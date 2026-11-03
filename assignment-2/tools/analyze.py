"""Aggregate all trials (including failures/limits); audit raw counts and statistics."""
import csv
import hashlib
import json
import math
import statistics as stats
from collections import defaultdict, Counter
from pathlib import Path

def load(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def write(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def percentile95(values):
    return sorted(values)[math.ceil(.95*len(values))-1]

def summarize(rows):
    attempt,solve,diagnostic=[],[],[]
    groups=defaultdict(list)
    for r in rows:
        groups[(r["experiment"],int(r["n"]),float(r["alpha"]),r["method"])].append(r)
    sort_means={n:stats.mean(int(x["elapsed_ns"]) for x in g)
                for (mode,n,a,method),g in groups.items() if mode=="solve" and method=="sort"}
    for (mode,n,alpha,method),g in sorted(groups.items()):
        elapsed=[int(x["elapsed_ns"]) for x in g]
        candidates=[int(x["candidate_size"]) for x in g]
        statuses=Counter(x["status"] for x in g)
        common=dict(n=n,alpha=alpha,method=method,trials=len(g),successes=statuses["OK"], fail_bracket=statuses["FAIL_BRACKET"],fail_size=statuses["FAIL_SIZE"], retry_limit=statuses["RETRY_LIMIT"],mean_ns=stats.mean(elapsed), median_ns=stats.median(elapsed),p95_ns=percentile95(elapsed))
        if mode=="solve":
            common.update(mean_attempts=stats.mean(int(x["attempt_count"]) for x in g), total_attempts=sum(int(x["attempt_count"]) for x in g), bracket_failures=sum(int(x["bracket_failures"]) for x in g), size_failures=sum(int(x["size_failures"]) for x in g), speedup=sort_means[n]/stats.mean(elapsed), eligible_for_best=statuses["RETRY_LIMIT"]==0)
            solve.append(common)
        else:
            p=statuses["OK"]/len(g)
            # Wilson interval for the observed success probability.
            z=1.959963984540054
            center=(p+z*z/(2*len(g)))/(1+z*z/len(g))
            half=z*math.sqrt(p*(1-p)/len(g)+z*z/(4*len(g)**2))/(1+z*z/len(g))
            common.update(success_rate=p,failure_rate=1-p,success_ci_low=center-half, success_ci_high=center+half,mean_candidate=stats.mean(candidates), median_candidate=stats.median(candidates), mean_candidate_normalized=stats.mean(candidates)/(n**.75), median_candidate_normalized=stats.median(candidates)/(n**.75), rank_misses=sum(x["rank_in_bracket"]=="0" for x in g), size_exceeded_events=sum(x["size_exceeded"]=="1" for x in g), simultaneous_events=sum(x["rank_in_bracket"]=="0" and x["size_exceeded"]=="1" for x in g), low_clamped=sum(x["low_clamped"]=="1" for x in g), high_clamped=sum(x["high_clamped"]=="1" for x in g))
            if mode=="diagnostic":
                for field in ["sampling_ns","sample_sort_ns","scan_ns","candidate_sort_ns"]:
                    common["mean_"+field]=stats.mean(int(x[field]) for x in g)
                common["mean_residual_ns"]=common["mean_ns"]-sum(common["mean_"+f] for f in ["sampling_ns","sample_sort_ns","scan_ns","candidate_sort_ns"])
                diagnostic.append(common)
            else:
                attempt.append(common)
    return {"attempt_summary.csv":attempt,"solve_summary.csv":solve,"diagnostic_summary.csv":diagnostic}

def all_rows(out):
    return [row for path in sorted((out/"raw").glob("*.csv")) for row in load(path)]

def analyze(out):
    rows=all_rows(out)
    for filename,table in summarize(rows).items():
        write(out/filename,table)
    print(f"PASS summarize {len(rows)} actual C++ records",flush=True)

def audit(out,require_complete=True):
    rows=all_rows(out)
    manifest=json.loads((out/"run_manifest.json").read_text(encoding="utf-8"))
    cfg=manifest["config"]
    jobs={(j["mode"],j["n"],j["dataset_seed"]):j for j in manifest["jobs"]}
    seen=set()
    paired=defaultdict(set)
    for r in rows:
        n=int(r["n"])
        job=jobs[(r["experiment"],n,int(r["dataset_seed"]))]
        assert 0<=int(r["trial_id"])<job["trials"]
        assert float(r["alpha"]) in (cfg["alphas"] if r["method"]=="randomized" else [0.0])
        identity=tuple(r[k] for k in ["experiment","n","dataset_seed","alpha","method","trial_id"])
        assert identity not in seen
        seen.add(identity)
        assert int(r["elapsed_ns"])>=0 and r["correctness"] in ("true","NA")
        if r["status"]=="OK":
            assert r["correctness"]=="true" and int(r["answer"])==n//2+1==int(r["reference"])
        else:
            assert r["correctness"]=="NA" and not r["answer"]
        if r["method"]=="sort":
            assert r["status"]=="OK"
            continue
        s=int(r["sample_size"])
        assert (s-1)**4<n**3<=s**4
        lo=max(1,min(s,math.floor(s/2-float(r["alpha"])*math.sqrt(n))))
        hi=max(1,min(s,math.ceil(s/2+float(r["alpha"])*math.sqrt(n))))
        assert (int(r["j_low"]),int(r["j_high"]))==(lo,hi)
        assert 0<=int(r["candidate_size"])<=n
        assert (r["size_exceeded"]=="1")==(int(r["candidate_size"])>4*s)
        if r["experiment"]!="solve":
            expected="FAIL_BRACKET" if r["rank_in_bracket"]=="0" else ( "FAIL_SIZE" if r["size_exceeded"]=="1" else "OK")
            assert r["status"]==expected and int(r["attempt_count"])==1
        else:
            assert 1<=int(r["attempt_count"])<=cfg["max_attempts"]
            failures=int(r["bracket_failures"])+int(r["size_failures"])
            assert failures+(r["status"]=="OK")==int(r["attempt_count"])
            if r["status"]=="RETRY_LIMIT":
                assert int(r["attempt_count"])==cfg["max_attempts"]
        paired[(r["experiment"],n,r["dataset_seed"],r["trial_id"])].add(r["sampling_seed"])
    assert all(len(v)==1 for v in paired.values()),"paired seeds differ"
    seeds_by_job=defaultdict(set)
    trials_by_job=Counter()
    for (mode,n,dataset_seed,trial),values in paired.items():
        seeds_by_job[(mode,n,dataset_seed)].update(values)
        trials_by_job[(mode,n,dataset_seed)]+=1
    assert all(len(seeds_by_job[job])==count for job,count in trials_by_job.items()),"sampling seed repeated across trials"
    for filename,expected in summarize(rows).items():
        actual=load(out/filename) if expected else []
        assert actual==[{k:str(v) for k,v in row.items()} for row in expected],filename
    expected_attempt=len(cfg["attempt_sizes"])*len(cfg["alphas"])*cfg["attempt_trials"]
    expected_solve=len(cfg["solve_sizes"])*len(cfg["dataset_seeds"])*(len(cfg["alphas"])+1)*cfg["solve_trials"]
    expected_diagnostic=len(cfg["alphas"])*cfg["diagnostic_trials"]
    counts=Counter(r["experiment"] for r in rows)
    if require_complete:
        expected_counts={k:v for k,v in dict(attempt=expected_attempt,solve=expected_solve, diagnostic=expected_diagnostic).items() if v}
        assert dict(counts)==expected_counts,counts
        expected_jobs={("attempt",n,cfg["attempt_dataset_seed"]) for n in cfg["attempt_sizes"]}
        expected_jobs|={("solve",n,s) for n in cfg["solve_sizes"] for s in cfg["dataset_seeds"]}
        if cfg["diagnostic_trials"]:
            expected_jobs.add(("diagnostic",cfg["diagnostic_n"],cfg["attempt_dataset_seed"]))
        assert {(j["mode"],j["n"],j["dataset_seed"]) for j in manifest["jobs"]}==expected_jobs
        for job in manifest["jobs"]:
            name=f"{job['mode']}_n{job['n']}_d{job['dataset_seed']}.csv"
            data=load(out/"raw"/name)
            assert len(data)==job["rows"]
            assert all(int(r["dataset_seed"])==job["dataset_seed"] and int(r["n"])==job["n"] for r in data)
    record=dict(status="PASS",profile=manifest["profile"],counts=dict(counts), require_complete=require_complete,successful_answers_checked=True, paired_seeds_verified=True,summary_recomputed=True, raw_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((out/"raw").glob("*.csv"))})
    (out/"audit.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print("PASS raw/summary audit "+str(dict(counts)),flush=True)
