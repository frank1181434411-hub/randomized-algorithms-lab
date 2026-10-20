"""Future solver orchestration. No solver, synthetic timing, or Freivalds implementation."""
import argparse
import csv
import json
import math
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path
from project import ROOT, cases, save

def invoke(exe,path,algorithm,k,seed):
    command=[str(exe),'--input',str(path),'--algorithm',algorithm,'--rounds',str(k),'--seed',str(seed)]
    start=time.perf_counter_ns()
    p=subprocess.run(command,capture_output=True,text=True,timeout=120)
    process_ns=time.perf_counter_ns()-start
    if p.returncode: raise RuntimeError(f'exit {p.returncode}: {p.stderr[:500]}')
    if len(p.stdout.splitlines())!=1: raise ValueError('stdout must be one JSON line')
    result=json.loads(p.stdout)
    if type(result.get('accepted')) is not bool: raise ValueError('accepted must be boolean')
    if type(result.get('elapsed_ns')) is not int or result['elapsed_ns']<0: raise ValueError('invalid elapsed_ns')
    if result.get('algorithm')!=algorithm or result.get('rounds')!=k or result.get('seed')!=seed:
        raise ValueError('algorithm/rounds/seed echo mismatch')
    return result,process_ns

def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def classification(truth,algorithm,accepted):
    if truth and not accepted: return 'BUG_FALSE_REJECT'
    if algorithm=='exact' and truth!=accepted: return 'BUG_EXACT'
    if not truth and accepted: return 'MISS'
    return 'OK'

def probability_row(k,trials,misses):
    p=2.0**(-k)
    return dict(k=k,trials=trials,misses=misses,observed_rate=misses/trials,
                theoretical_probability=p,expected_misses=trials*p)

def correctness(args):
    rows=[];bugs=0
    for m,path in cases():
        if m['group']!='correctness':continue
        for alg in ['exact','freivalds']:
            for repeat in range(1 if alg=='exact' else args.repeats):
                seed=100000+repeat
                r,_=invoke(args.exe,path,alg,10,seed)
                status=classification(m['truth'],alg,r['accepted']);bugs+=status.startswith('BUG')
                rows.append(dict(case_id=m['case_id'],algorithm=alg,k=10,seed=seed,truth=m['truth'],accepted=r['accepted'],status=status))
    write_csv(args.out/'correctness.csv',rows,['case_id','algorithm','k','seed','truth','accepted','status'])
    print(f'correctness: {bugs} bugs; {sum(r["status"]=="MISS" for r in rows)} misses (not automatically bugs)')
    if bugs:raise RuntimeError('correctness failure')

def performance(args):
    if not args.provenance: raise ValueError('--provenance solver build JSON is required')
    provenance=json.loads(args.provenance.read_text(encoding='utf-8'))
    for field in ['compiler','optimization','os','machine','command']:
        if not provenance.get(field):raise ValueError(f'provenance missing {field}')
    if provenance['optimization']!='-O2':raise ValueError('use -O2 for comparable experiments')
    import hashlib
    save(args.out/'solver_environment.json',dict(provenance=provenance,
         executable=str(args.exe),sha256=hashlib.sha256(args.exe.read_bytes()).hexdigest()))
    rows=[]
    for m,path in cases():
        if m['group']!='performance':continue
        jobs=[('n',alg,k) for alg in ['exact','freivalds'] for k in ([1] if alg=='exact' else [5,10,20])]
        if m['n']==args.fixed_n: jobs += [('k','freivalds',k) for k in [1,2,5,10,20,40]]
        for sweep,alg,k in jobs:
            for rep in range(-args.warmups,args.repeats):
                seed=2026102000+rep+args.warmups
                r,process_ns=invoke(args.exe,path,alg,k,seed)
                if not r['accepted']:raise RuntimeError('correct performance product rejected')
                if rep>=0:rows.append(dict(sweep=sweep,case_id=m['case_id'],n=m['n'],algorithm=alg,k=k,
                     repeat=rep,seed=seed,accepted=r['accepted'],elapsed_ns=r['elapsed_ns'],process_ns=process_ns))
    if not any(r['sweep']=='k' for r in rows):raise ValueError('fixed n absent from performance datasets')
    write_csv(args.out/'timing_raw.csv',rows,['sweep','case_id','n','algorithm','k','repeat','seed','accepted','elapsed_ns','process_ns'])
    summarize(args.out/'timing_raw.csv',args.out)

def probability(args):
    config=json.loads((ROOT/'data/probability_config.json').read_text())
    m,path=next((m,p) for m,p in cases() if m['case_id']==config['case_id'])
    rng=random.Random(config['master_seed']);used=set();rows=[];raw=[]
    for k in config['rounds']:
        misses=0
        for trial in range(args.trials):
            seed=rng.getrandbits(64)
            while seed in used:seed=rng.getrandbits(64)
            used.add(seed)
            r,_=invoke(args.exe,path,'freivalds',k,seed)
            misses+=r['accepted']
            raw.append(dict(k=k,trial=trial,seed=seed,accepted=r['accepted']))
        rows.append(probability_row(k,args.trials,misses))
    write_csv(args.out/'probability_raw.csv',raw,['k','trial','seed','accepted'])
    write_csv(args.out/'probability.csv',rows,list(rows[0]))
    print('probability complete; inspect binomial sampling variation, not a hard rate threshold')

def summarize(path,out):
    with path.open(encoding='utf-8',newline='') as f:raw=list(csv.DictReader(f))
    groups={}
    for r in raw:
        key=(r['sweep'],int(r['n']),r['algorithm'],int(r['k']))
        groups.setdefault(key,[]).append(int(r['elapsed_ns']))
    med={k:statistics.median(v) for k,v in groups.items()}; rows=[]
    for (s,n,a,k),t in sorted(med.items()):
        smaller=[nn for ss,nn,aa,kk in med if (ss,aa,kk)==(s,a,k) and nn<n]
        previous=max(smaller) if smaller else None
        prev_t=med.get((s,previous,a,k),0);exact=med.get((s,n,'exact',1),0)
        rows.append(dict(sweep=s,n=n,algorithm=a,k=k,samples=len(groups[s,n,a,k]),median_ns=t,
             T_per_n2=t/n**2,T_per_n3=t/n**3,T_per_kn2=t/(k*n*n),
             speedup=exact/t if a=='freivalds' and t else '',previous_n=previous or '',
             adjacent_ratio=t/prev_t if prev_t else '',
             local_exponent=math.log(t/prev_t)/math.log(n/previous) if prev_t and t else ''))
    fields=['sweep','n','algorithm','k','samples','median_ns','T_per_n2','T_per_n3','T_per_kn2','speedup','previous_n','adjacent_ratio','local_exponent']
    write_csv(out/'timing_summary.csv',rows,fields)
    print(f'PASS summarized {len(raw)} measurements into {len(rows)} groups')

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['correctness','performance','probability','analyze'])
    p.add_argument('--exe',type=Path);p.add_argument('--out',type=Path,default=ROOT/'results')
    p.add_argument('--provenance',type=Path);p.add_argument('--raw',type=Path)
    p.add_argument('--repeats',type=int,default=10);p.add_argument('--warmups',type=int,default=2)
    p.add_argument('--fixed-n',type=int,default=256);p.add_argument('--trials',type=int,default=10000)
    args=p.parse_args()
    if args.repeats<1 or args.warmups<0 or args.trials<1:p.error('invalid repeat/trial count')
    if args.mode=='analyze':
        if not args.raw:p.error('--raw required')
        summarize(args.raw,args.out);return
    if not args.exe:
        print('SKIP / 待接入：尚未指定正式算法 --exe；不生成实验 CSV。');return
    args.exe=args.exe.resolve()
    if not args.exe.is_file():raise FileNotFoundError(args.exe)
    {'correctness':correctness,'performance':performance,'probability':probability}[args.mode](args)

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError,KeyError,StopIteration) as e:
        print(f'FAIL {e}',file=sys.stderr);sys.exit(1)
