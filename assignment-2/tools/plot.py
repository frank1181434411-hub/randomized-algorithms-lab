"""Plot real summaries only; use local font/cache settings, never install packages."""
import argparse
import csv
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR",str(ROOT/".mplconfig"))
os.environ.setdefault("MPLBACKEND","Agg")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

def read(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--results",type=Path,default=ROOT/"results")
    args=parser.parse_args()
    out=args.results/"figures"
    out.mkdir(parents=True,exist_ok=True)
    font=Path("C:/Windows/Fonts/msyh.ttc")
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams["font.family"]=font_manager.FontProperties(fname=str(font)).get_name()
    else:
        raise RuntimeError("Chinese font msyh.ttc missing; configure an available CJK font before plotting")
    plt.rcParams.update({"axes.unicode_minus":False,"figure.dpi":140,"font.size":10})
    solves=read(args.results/"solve_summary.csv")
    attempts=read(args.results/"attempt_summary.csv")
    diagnostics=read(args.results/"diagnostic_summary.csv")
    sizes=sorted({int(r["n"]) for r in solves})
    alphas=sorted({float(r["alpha"]) for r in solves if r["method"]=="randomized"})
    files=[]
    def finish(fig,name):
        fig.tight_layout()
        fig.savefig(out/name,bbox_inches="tight")
        plt.close(fig)
        files.append(name)
    fig,axes=plt.subplots(2,2,figsize=(11,7),squeeze=False)
    for ax,n in zip(axes.flat,sizes):
        g=sorted([r for r in solves if int(r["n"])==n and r["method"]=="randomized"],key=lambda r:float(r["alpha"]))
        ax.plot([float(r["alpha"]) for r in g],[float(r["mean_ns"])/1e6 for r in g],"o-",label="随机算法（含重试）")
        ax.set(title=f"n={n:,}",xlabel="区间参数 α",ylabel="平均完整求解时间 (ms)")
        ax.set_xticks(alphas)
        ax.grid(alpha=.25)
        ax.legend()
    for ax in list(axes.flat)[len(sizes):]:
        ax.set_visible(False)
    fig.suptitle("区间宽度与完整求解平均耗时")
    finish(fig,"alpha_solve_mean.png")

    attempt_sizes=sorted({int(r["n"]) for r in attempts})
    fig,axes=plt.subplots(1,len(attempt_sizes),figsize=(5*len(attempt_sizes),4),squeeze=False)
    for ax,n in zip(axes.flat,attempt_sizes):
        g=sorted([r for r in attempts if int(r["n"])==n],key=lambda r:float(r["alpha"]))
        x=list(range(len(g)))
        bracket=[int(r["fail_bracket"])/int(r["trials"]) for r in g]
        size=[int(r["fail_size"])/int(r["trials"]) for r in g]
        independent=[int(r["size_exceeded_events"])/int(r["trials"]) for r in g]
        ax.bar(x,bracket,label="FAIL_BRACKET")
        ax.bar(x,size,bottom=bracket,label="FAIL_SIZE")
        ax.plot(x,independent,"x--",color="black",label="候选超限事件（独立标志）")
        ax.set_xticks(x,[r["alpha"] for r in g])
        ax.set(title=f"n={n:,}",xlabel="区间参数 α",ylabel="单次尝试失败率")
        ax.set_ylim(0,min(1,max(.06,max(bracket)+max(size)+.08)))
        ax.legend(fontsize=8)
        ax.grid(axis="y",alpha=.2)
    finish(fig,"alpha_failure_rate.png")

    fig,ax=plt.subplots(figsize=(8,5))
    for n in attempt_sizes:
        g=sorted([r for r in attempts if int(r["n"])==n],key=lambda r:float(r["alpha"]))
        ax.plot([float(r["alpha"]) for r in g],[float(r["mean_candidate_normalized"]) for r in g],"o-",label=f"n={n:,}")
    ax.axhline(4,color="black",ls="--",label="4（实际上限为 4s/n^(3/4)）")
    ax.set(xlabel="区间参数 α",ylabel="平均候选集合大小 / n^(3/4)",title="样本排名间隔与实际候选集合大小")
    ax.set_xticks(alphas)
    ax.legend();ax.grid(alpha=.25)
    finish(fig,"alpha_candidate_size.png")

    fig,ax=plt.subplots(figsize=(8,5))
    for alpha in [0]+alphas:
        g=sorted([r for r in solves if float(r["alpha"])==alpha],key=lambda r:int(r["n"]))
        ax.plot([int(r["n"]) for r in g],[float(r["mean_ns"])/1e6 for r in g],"o-",label="完整排序" if alpha==0 else f"α={alpha:g}")
    ax.set(xscale="log",yscale="log",xlabel="数组长度 n（对数）",ylabel="平均完整求解时间 (ms，对数)",title="规模与完整求解时间")
    ax.legend();ax.grid(which="both",alpha=.2)
    finish(fig,"n_solve_time.png")

    fig,ax=plt.subplots(figsize=(8,5))
    for n in sizes:
        g=sorted([r for r in solves if int(r["n"])==n and r["method"]=="randomized"],key=lambda r:float(r["alpha"]))
        ax.plot([float(r["alpha"]) for r in g],[float(r["mean_attempts"]) for r in g],"o-",label=f"n={n:,}")
    ax.set(xlabel="区间参数 α",ylabel="平均尝试次数（含成功尝试）",title="区间宽度与重试成本")
    ax.set_xticks(alphas)
    ax.legend();ax.grid(alpha=.25)
    finish(fig,"alpha_retry_count.png")

    fig,ax=plt.subplots(figsize=(8,5))
    for n in attempt_sizes:
        g=sorted([r for r in attempts if int(r["n"])==n],key=lambda r:float(r["alpha"]))
        ax.plot([float(r["alpha"]) for r in g],[float(r["mean_ns"])/1e6 for r in g],"o-",label=f"n={n:,}")
    ax.set(xlabel="区间参数 α",ylabel="平均单次尝试时间 (ms)",title="单次尝试时间（包含失败尝试）")
    ax.set_xticks(alphas)
    ax.legend();ax.grid(alpha=.25)
    finish(fig,"alpha_attempt_time.png")

    fig,ax=plt.subplots(figsize=(9,5))
    g=sorted(diagnostics,key=lambda r:float(r["alpha"]))
    bottom=[0.0]*len(g);x=list(range(len(g)))
    for field,label in [("mean_sampling_ns","抽样"),("mean_sample_sort_ns","样本排序"),
                        ("mean_scan_ns","扫描与构造"),("mean_candidate_sort_ns","候选排序"),
                        ("mean_residual_ns","其余管理开销")]:
        values=[float(r[field])/1e6 for r in g]
        ax.bar(x,values,bottom=bottom,label=label)
        bottom=[a+b for a,b in zip(bottom,values)]
    ax.set_xticks(x,[r["alpha"] for r in g])
    ax.set(xlabel="区间参数 α",ylabel="平均单次诊断时间 (ms)",title=f"独立分阶段诊断 n={int(g[0]['n']):,}（包含失败尝试）")
    ax.legend(fontsize=9)
    finish(fig,"phase_diagnostic.png")

    # A visual inspection sheet, excluded from the seven scientific plot filenames.
    fig,axes=plt.subplots(4,2,figsize=(18,21))
    for ax,filename in zip(axes.flat,files):
        ax.imshow(plt.imread(out/filename))
        ax.axis("off")
    axes.flat[-1].axis("off")
    fig.tight_layout()
    fig.savefig(out/"inspection_sheet.png",dpi=90)
    plt.close(fig)
    (out/"plot_environment.txt").write_text( f"matplotlib={matplotlib.__version__}\nfont={font}\ninput={args.results.resolve()}\n",encoding="utf-8")
    print(f"PASS {len(files)} result plots + inspection sheet in {out}",flush=True)

if __name__=="__main__":
    main()
