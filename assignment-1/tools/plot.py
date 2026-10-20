"""Only plot actual CSVs; matplotlib is optional and never installed automatically."""
import argparse
import csv
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=Path(__file__).resolve().parents[1]/'results')
    args=p.parse_args();timing=args.results/'timing_summary.csv';prob=args.results/'probability.csv'
    if not timing.exists() and not prob.exists():
        print('SKIP / 待接入：没有实测 CSV，不生成图。');return
    import matplotlib.pyplot as plt
    out=args.results/'figures';out.mkdir(exist_ok=True)
    if timing.exists():
        with timing.open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        for name,sweep,x,y in [('n_time','n','n','median_ns'),('k_time','k','k','median_ns'),
                            ('speedup','n','n','speedup'),('adjacent_ratio','n','n','adjacent_ratio'),
                            ('normalized_n2','n','n','T_per_n2'),('normalized_n3','n','n','T_per_n3'),
                            ('normalized_kn2','n','n','T_per_kn2')]:
            groups={}
            for r in rows:
                if r['sweep']!=sweep or not r[y]:continue
                key=(r['algorithm'],r['k'] if sweep=='n' else r['n'])
                groups.setdefault(key,[]).append((float(r[x]),float(r[y])))
            if not groups:continue
            fig,ax=plt.subplots()
            for label,values in sorted(groups.items()):
                values.sort();ax.plot(*zip(*values),marker='o',label=str(label))
            ax.set(xlabel=x,ylabel=y);ax.legend();fig.tight_layout();fig.savefig(out/(name+'.png'));plt.close(fig)
    if prob.exists():
        with prob.open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        fig,ax=plt.subplots();ax.plot([int(r['k']) for r in rows],[float(r['observed_rate']) for r in rows],'o-',label='observed')
        ax.plot([int(r['k']) for r in rows],[float(r['theoretical_probability']) for r in rows],'--',label='2^(-k)')
        ax.set(xlabel='k',ylabel='miss rate');ax.legend();fig.tight_layout();fig.savefig(out/'probability.png');plt.close(fig)

if __name__=='__main__':main()
