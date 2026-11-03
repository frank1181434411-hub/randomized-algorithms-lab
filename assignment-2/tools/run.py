"""Build, test, schedule and audit the real C++ experiments (standard library only)."""
import argparse
import csv
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from analyze import analyze, audit

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
EXE = BUILD / "median.exe"

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def command(args, timeout=1800):
    args = [str(x) for x in args]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    if result.returncode:
        raise RuntimeError(f"exit {result.returncode}: {args}")
    return dict(command=args, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)

def build():
    BUILD.mkdir(exist_ok=True)
    commands = []
    for source, output in [("src/driver.cpp", "median.exe"), ("tests/test_median.cpp", "test_median.exe")]:
        args = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", source, "-o", str(BUILD / output)]
        command(args)
        commands.append(args)
    record = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), commands=commands, compiler=subprocess.check_output(["g++", "--version"], text=True), optimization="-O2", os=platform.platform(), machine=platform.machine(), processor=platform.processor(), python=sys.version, generator="C++ mt19937_64, rejection-mapped Fisher-Yates permutation of 1..n", executable_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(), source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/"src/median.hpp", ROOT/"src/driver.cpp"]})
    save(ROOT / "results/environment.json", record)
    print("PASS build (C++17, -O2)", flush=True)

def test():
    checks = [command([BUILD/"test_median.exe"])]
    # Real CLI rejection checks, including a path containing spaces.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="median check with spaces ", dir=BUILD) as folder:
        output = Path(folder)/"result with spaces.csv"
        valid = [EXE, "--mode", "attempt", "--n", "3", "--dataset-seed", "101", "--trials", "4",
                 "--warmups", "0", "--max-attempts", "20", "--master-seed", "1", "--schedule-seed", "2",
                 "--alphas", ".125,.25,.5,1,1.5", "--output", output]
        checks.append(command(valid))
        with output.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 20
        for key, value in [("--n", "0"), ("--n", "10000001"), ("--n", "-1"),
                           ("--alphas", "0"), ("--alphas", "nan"), ("--alphas", "inf"),
                           ("--alphas", "1,1"), ("--trials", "0"), ("--max-attempts", "0")]:
            bad = list(map(str, valid))
            bad[bad.index(key)+1] = value
            result = subprocess.run(bad, cwd=ROOT, capture_output=True, text=True)
            assert result.returncode != 0 and "ERROR:" in result.stderr, (key, value)
        # Same seed reproduces all non-time fields; sampling and sorting still execute.
        first = rows
        checks.append(command(valid))
        with output.open(encoding="utf-8") as f:
            second = list(csv.DictReader(f))
        for a,b in zip(first,second):
            assert {k:v for k,v in a.items() if not k.endswith("_ns")} == {
                k:v for k,v in b.items() if not k.endswith("_ns")}
    save(ROOT/"results/tests.json", dict(status="PASS", real_cli_invalid_cases=9, path_with_spaces=True, fixed_seed_reproducibility=True, checks=checks))
    print("PASS real CLI checks, paths with spaces and fixed-seed reproducibility", flush=True)

def config(profile):
    cfg = json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    if profile == "quick":
        cfg.update(attempt_sizes=[100,1000], attempt_trials=20, solve_sizes=[100,1000], dataset_seeds=[101], solve_trials=3, warmups=1, diagnostic_n=1000, diagnostic_trials=3)
    elif profile == "confirmation":
        cfg.update(alphas=[0.125,0.25,0.5],attempt_sizes=[],dataset_seeds=[404,505,606], diagnostic_trials=0,sampling_master_seed=2026110303,schedule_seed=2026110304)
    return cfg

def run(profile, stage="all", resume=False):
    cfg = config(profile)
    out = ROOT/"results" if profile == "formal" else ROOT/"results"/profile
    raw = out/"raw"
    raw.mkdir(parents=True, exist_ok=True)
    jobs = []
    if stage in ("all", "attempt"):
        jobs += [("attempt", n, cfg["attempt_dataset_seed"], cfg["attempt_trials"], 0)
                 for n in cfg["attempt_sizes"]]
    if stage in ("all", "solve"):
        solve_jobs = [("solve", n, seed, cfg["solve_trials"], cfg["warmups"])
                      for n in cfg["solve_sizes"] for seed in cfg["dataset_seeds"]]
        random.Random(cfg["schedule_seed"]).shuffle(solve_jobs)
        jobs += solve_jobs
    if stage in ("all", "diagnostic") and cfg["diagnostic_trials"]:
        jobs.append(("diagnostic", cfg["diagnostic_n"], cfg["attempt_dataset_seed"], cfg["diagnostic_trials"], cfg["warmups"]))
    env = json.loads((ROOT/"results/environment.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(EXE.read_bytes()).hexdigest() == env["executable_sha256"], "rebuild provenance first"
    manifest = out/"run_manifest.json"
    if resume and manifest.exists():
        prior = json.loads(manifest.read_text(encoding="utf-8"))
        assert prior["config"] == cfg and prior["executable_sha256"] == env["executable_sha256"]
    invocation = dict(profile=profile, config=cfg, executable_sha256=env["executable_sha256"], timestamp_utc=datetime.now(timezone.utc).isoformat(), jobs=[])
    for mode,n,seed,trials,warmups in jobs:
        target = raw/f"{mode}_n{n}_d{seed}.csv"
        expected = trials*(len(cfg["alphas"])+(mode=="solve"))
        seed_offset = {"attempt":0, "solve":1<<60, "diagnostic":2<<60}[mode]
        master = (cfg["sampling_master_seed"]+n*1000003+seed*1000033+seed_offset) % (1<<64)
        order_seed = (cfg["schedule_seed"]+n*10007+seed*10009+seed_offset) % (1<<64)
        args = [EXE, "--mode",mode,"--n",n,"--dataset-seed",seed,"--trials",trials,
                "--warmups",warmups,"--max-attempts",cfg["max_attempts"],
                "--master-seed",master,"--schedule-seed",order_seed,
                "--alphas",",".join(map(str,cfg["alphas"])),"--output",target]
        temporary = target.with_suffix(".csv.partial")
        real_args = args[:-1]+[temporary]
        skipped = False
        if resume and target.exists():
            with target.open(encoding="utf-8") as f:
                skipped = len(list(csv.DictReader(f))) == expected
        if not skipped:
            command(real_args)
            with temporary.open(encoding="utf-8") as f:
                assert len(list(csv.DictReader(f))) == expected
            temporary.replace(target)
        print(f"{'RESUME' if skipped else 'SAVED'} {target.name}", flush=True)
        invocation["jobs"].append(dict(mode=mode,n=n,dataset_seed=seed,trials=trials,warmups=warmups, sampling_master_seed=master,schedule_seed=order_seed, command=list(map(str,real_args)),final_output=str(target), executed_this_invocation=not skipped,rows=expected))
    if manifest.exists() and stage != "all":
        previous = json.loads(manifest.read_text(encoding="utf-8"))
        current = {(j["mode"],j["n"],j["dataset_seed"]) for j in invocation["jobs"]}
        invocation["jobs"] = [j for j in previous["jobs"] if (j["mode"],j["n"],j["dataset_seed"]) not in current] + invocation["jobs"]
    save(manifest, invocation)
    analyze(out)
    audit(out, require_complete=stage=="all")
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["build","test","run","analyze","audit","all"])
    parser.add_argument("--profile",choices=["quick","formal","confirmation"],default="quick")
    parser.add_argument("--stage",choices=["all","attempt","solve","diagnostic"],default="all")
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    if args.action in ("build","all"):build()
    if args.action in ("test","all"):test()
    out=ROOT/"results" if args.profile=="formal" else ROOT/"results"/args.profile
    if args.action in ("run","all"):run(args.profile,args.stage,args.resume)
    if args.action=="analyze":analyze(out)
    if args.action=="audit":audit(out,require_complete=True)

if __name__=="__main__":
    main()
