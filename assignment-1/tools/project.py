"""Stage-one build, reproducible generation, integrity and independent references."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'build' / 'reference.exe'
DATA = ROOT / 'data'

def run(args):
    return subprocess.run([str(x) for x in args], check=True, capture_output=True, text=True).stdout

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def build():
    REF.parent.mkdir(exist_ok=True)
    command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', str(ROOT/'tools/reference.cpp'), '-o', str(REF)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stderr: print(result.stderr, file=sys.stderr)
    result.check_returncode()
    save(ROOT/'results/build_environment.json', dict(command=command, compiler=run(['g++','--version']),
         os=platform.platform(), machine=platform.machine(), processor=platform.processor(),
         python=sys.version, timing_source='future solver: std::chrono::steady_clock',
         scope='reference infrastructure only; solver build provenance must be supplied separately'))
    print('PASS build reference (-O2, C++17)')

def generate(args):
    if not REF.exists(): raise RuntimeError('run build first')
    if not all(1<=n<=1024 for n in args.sizes):raise ValueError('sizes must be in 1..1024')
    if not all(0<=s<2**64 for s in args.seeds):raise ValueError('seeds must be uint64')
    if len(set(args.sizes))!=len(args.sizes) or len(set(args.seeds))!=len(args.seeds):
        raise ValueError('duplicate sizes or seeds')
    specs=[]
    for n,kind,low in [(1,'random',0),(2,'random',0),(3,'zero',0),(4,'identity',0),
                       (5,'diagonal',0),(8,'random',0),(7,'random',-9)]:
        for mutation in ['none','single']+(['multi','cancel'] if n>=2 else []):
            specs.append(('correctness', n, 20261020+n, kind, mutation, low))
    for n in args.sizes:
        for seed in args.seeds: specs.append(('performance',n,seed,'random','none',0))
    specs.append(('probability',16,314159,'random','single',0))
    ids=[]
    for group,n,seed,kind,mutation,low in specs:
        cid=f'{group}_n{n}_s{seed}_{kind}_{mutation}'
        file=DATA/group/(cid+'.txt'); meta=file.with_suffix('.json')
        if (file.exists() or meta.exists()) and not args.force:
            raise RuntimeError(f'refusing overwrite: {file}; use --force for generated data')
        file.parent.mkdir(parents=True,exist_ok=True)
        run([REF,'generate',file,n,seed,kind,mutation,low])
        changes={'none':[], 'single':[[0,0,1]], 'multi':[[0,0,1],[n-1,n-1,2]], 'cancel':[[0,0,1],[0,1,-1]]}[mutation]
        save(meta,dict(schema_version=1,case_id=cid,seed=seed,n=n,group=group,data_type=kind,
                      element_range=[low,9],candidate_abs_bound=81*n+2,truth=mutation=='none',
                      modifications=[dict(row=i,col=j,delta=d) for i,j,d in changes],
                      input_file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        ids.append(str(meta.relative_to(DATA)).replace('\\','/'))
    save(DATA/'manifest.json',dict(schema_version=1,cases=ids))
    save(DATA/'probability_config.json',dict(case_id=specs and cid,rounds=[1,2,4,8,10],trials=10000,
        master_seed=271828,vector_distribution='independent uniform bits {0,1}',exact_probability='2**(-k)'))
    print(f'PASS generated {len(ids)} cases')

def cases():
    manifest=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['schema_version']==1 and len(set(manifest['cases']))==len(manifest['cases'])
    for name in manifest['cases']:
        p=DATA/name
        m=json.loads(p.read_text(encoding='utf-8'))
        yield m,p.parent/m['input_file']

def read_case(m,p):
    raw=p.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==m['sha256'], f'hash: {p}'
    lines=raw.decode('ascii').splitlines(); n=m['n']
    assert type(n) is int and 1<=n<=1024 and lines[0]==str(n)
    assert len(lines)==1+3*n
    rows=[]
    for line in lines[1:]:
        tokens=line.split(); assert len(tokens)==n
        assert all(t.lstrip('-').isdigit() for t in tokens)
        row=list(map(int,tokens)); assert all(-(2**63)<=x<2**63 for x in row); rows.append(row)
    a,b,c=rows[:n],rows[n:2*n],rows[2*n:]
    lo,hi=m['element_range']; assert -9<=lo<=hi<=9
    assert all(lo<=x<=hi for row in a+b for x in row)
    assert m['candidate_abs_bound']==81*n+2
    assert all(abs(x)<=m['candidate_abs_bound'] for row in c for x in row)
    assert type(m['truth']) is bool and type(m['seed']) is int
    assert p.stem==m['case_id'] and m['group']==p.parent.name and m['schema_version']==1
    seen=set()
    for d in m['modifications']:
        i,j,v=d['row'],d['col'],d['delta']
        assert 0<=i<n and 0<=j<n and v!=0 and (i,j) not in seen
        seen.add((i,j))
    assert m['truth']==(not seen)
    return a,b,c

def check():
    count=small=0
    for m,p in cases():
        a,b,c=read_case(m,p); n=m['n']
        actual=json.loads(run([REF,'check',p]))['accepted']
        assert actual==m['truth'],m['case_id']
        if n<=32:
            product=[[sum(a[i][t]*b[t][j] for t in range(n)) for j in range(n)] for i in range(n)]
            assert (product==c)==actual
            for d in m['modifications']: product[d['row']][d['col']]+=d['delta']
            assert product==c, 'modification metadata mismatch'
            small+=1
        else:
            assert m['group']=='performance' and not m['modifications']
        count+=1
    config=json.loads((DATA/'probability_config.json').read_text())
    assert config['rounds']==[1,2,4,8,10] and config['trials']==10000
    assert any(m['case_id']==config['case_id'] and m['group']=='probability' for m,p in cases())
    print(f'PASS integrity + C++ truth: {count}; independent Python bigint: {small}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('build'); sub.add_parser('check')
    gen=sub.add_parser('generate'); gen.add_argument('--sizes',type=int,nargs='+',default=[64,128,256,512])
    gen.add_argument('--seeds',type=int,nargs='+',default=[101,202]); gen.add_argument('--force',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='build': build()
        elif args.command=='generate': generate(args)
        else: check()
    except (AssertionError,ValueError,RuntimeError,OSError,subprocess.SubprocessError) as e:
        print(f'FAIL {e}',file=sys.stderr);sys.exit(1)
