"""Generate the Chinese report tables directly from audited, formal CSVs."""
import csv
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/"results"/name).open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))
def table(headers,rows):
    return "| "+" | ".join(headers)+" |\n|"+"|".join("---" for _ in headers)+"|\n"+ "\n".join("| "+" | ".join(map(str,row))+" |" for row in rows)
def ms(value):
    return f"{float(value)/1e6:.6f}"

def main():
    env=json.loads((ROOT/"results/environment.json").read_text(encoding="utf-8"))
    audit=json.loads((ROOT/"results/audit.json").read_text(encoding="utf-8"))
    assert audit["status"]=="PASS" and audit["require_complete"]
    cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    attempts=read("attempt_summary.csv")
    solves=read("solve_summary.csv")
    diagnostics=read("diagnostic_summary.csv")
    confirms=read("confirmation/solve_summary.csv")
    sizes=cfg["solve_sizes"]
    best=[]
    for n in sizes:
        g=sorted([r for r in solves if int(r["n"])==n and r["method"]=="randomized"], key=lambda r:float(r["mean_ns"]))
        eligible=[r for r in g if r["eligible_for_best"]=="True"]
        if len(eligible)!=len(g):
            raise RuntimeError("retry limits observed: adapt the report to censored solves before ranking")
        best.append(eligible[0])
    best_table=table(["$n$","均值最小的 $\\alpha$","平均总时间 (ms)","中位数 (ms)","P95 (ms)", "平均尝试次数","相对排序加速比","次优均值差距"], [(r["n"],r["alpha"],ms(r["mean_ns"]),ms(r["median_ns"]),ms(r["p95_ns"]), f'{float(r["mean_attempts"]):.3f}',f'{float(r["speedup"]):.2f}', f'{(sorted(float(x["mean_ns"]) for x in solves if x["n"]==r["n"] and x["method"]=="randomized")[1]/float(r["mean_ns"])-1)*100:.2f}%') for r in best])
    attempt_table=table(["$n$","$\\alpha$","成功/1000","FAIL_BRACKET","FAIL_SIZE","平均 $\\lvert C\\rvert$", "中位数 $\\lvert C\\rvert$","平均 $\\lvert C\\rvert/n^{3/4}$","平均尝试时间 (ms)"], [(r["n"],r["alpha"],r["successes"],r["fail_bracket"],r["fail_size"], f'{float(r["mean_candidate"]):.2f}',f'{float(r["median_candidate"]):.2f}', f'{float(r["mean_candidate_normalized"]):.4f}',ms(r["mean_ns"])) for r in attempts])
    solve_table=table(["$n$","方法","平均总时间 (ms)","中位数 (ms)","P95 (ms)","平均尝试次数", "RETRY_LIMIT","加速比"], [(r["n"],"完整排序" if r["method"]=="sort" else "$\\alpha="+r["alpha"]+"$", ms(r["mean_ns"]),ms(r["median_ns"]),ms(r["p95_ns"]), f'{float(r["mean_attempts"]):.3f}',r["retry_limit"],f'{float(r["speedup"]):.2f}') for r in solves])
    confirm_table=table(["$n$","新种子均值最低的 $\\alpha$","平均总时间 (ms)", "原候选 0.125 (ms)","原候选 0.25 (ms)","原候选 0.5 (ms)"], [(n,min((r for r in confirms if int(r["n"])==n and r["method"]=="randomized"), key=lambda r:float(r["mean_ns"]))["alpha"], ms(min(float(r["mean_ns"]) for r in confirms if int(r["n"])==n and r["method"]=="randomized")), *(ms(next(r["mean_ns"] for r in confirms if int(r["n"])==n and float(r["alpha"])==a)) for a in [.125,.25,.5])) for n in sizes])
    phase_table=table(["$\\alpha$","抽样 (ms)","样本排序 (ms)","扫描与构造 (ms)","候选排序 (ms)", "其他开销 (ms)","总时间均值 (ms)","总时间中位数 (ms)"], [(r["alpha"],*(ms(r[k]) for k in ["mean_sampling_ns","mean_sample_sort_ns","mean_scan_ns", "mean_candidate_sort_ns","mean_residual_ns","mean_ns","median_ns"])) for r in diagnostics])
    bound_table=table(["$n$","$s$","下述保守失败概率上界","$\\alpha=1$ 实测失败率"], [(n,math.ceil(n**.75),f'{min(1,math.ceil(n**.75)/(2*n)+math.ceil(n**.75)/(2*(math.sqrt(n)-1)**2)):.6f}', next(r["failure_rate"] for r in attempts if int(r["n"])==n and float(r["alpha"])==1)) for n in cfg["attempt_sizes"]])
    confirmation_same=all( float(min((r for r in confirms if int(r["n"])==int(b["n"]) and r["method"]=="randomized"), key=lambda r:float(r["mean_ns"]))["alpha"])==float(b["alpha"]) for b in best)
    confirm_note=("新种子确认中，各规模的均值最低参数与主实验相同。" if confirmation_same else "新种子确认中，部分规模的均值最低参数发生变化，说明接近的候选参数排名会受抽样与计时噪声影响。")
    tokens={
        "ENV":table(["项目","实际记录"],[ ("操作系统",env["os"]),("编译器",env["compiler"].splitlines()[0]), ("编译选项","-std=c++17 -O2 -Wall -Wextra"),("架构",env["machine"]), ("处理器标识",env["processor"]),("调度 Python",env["python"].splitlines()[0]), ("核心计时","std::chrono::steady_clock，纳秒"),("构建程序 SHA-256",env["executable_sha256"])]),
        "BEST":best_table,"ATTEMPT":attempt_table,"SOLVE":solve_table,"CONFIRM":confirm_table,
        "PHASE":phase_table,"BOUND":bound_table,"CONFIRM_NOTE":confirm_note,
        "BEST_ALPHAS":"、".join(f'$n={r["n"]}$：$\\alpha={r["alpha"]}$' for r in best),
    }
    text=r"""# 抽样区间宽度对随机化中位数算法性能的影响

实验日期：2026 年 11 月 3 日。本文基于默认正式配置的真实运行记录；快速模式结果没有混入正式统计。

## 一、实验目的与要求

实现课堂抽样式随机化中位数算法，固定样本量 $s=\lceil n^{3/4}\rceil$，仅改变区间参数 $\alpha\in\{0.125,0.25,0.5,1,1.5\}$。比较单次正确性、失败原因、实际候选集合、单次尝试时间及含失败重试的完整求解时间。$\alpha=1$ 为题目指定的参照设置。

区间宽度指样本排序后的排名间隔，不是数值差 $u-d$。实验分别记录样本量 $s$、样本边界排名 $j_{\rm low},j_{\rm high}$ 和原数组实际候选个数 $|C|$，不将三者混为一谈。

## 二、中位数定义与输入前提

输入为非空、元素互异的 int64_t 数组。目标为第 $r=\lfloor n/2\rfloor+1$ 小的元素，偶数长度取上中位数。参考答案由完整排序后的 sorted[n/2] 得到。

正式数据采用 $1,\ldots,n$ 的随机排列。生成器在 C++ 中使用 mt19937_64、拒绝采样映射与 Fisher–Yates 洗牌，数据种子和算法抽样种子分开记录；大数组不落盘、不按试验重复保存。算法采样有放回，保留样本中重复抽中的元素。

预检查把输入副本排序，检查相邻元素是否相等；发现重复值就明确拒绝，不让重复值导致无限重试。检查和参考答案计算均在核心计时外。正式算法函数要求调用前完成输入/参数检查。没有小规模直接排序分支，边界规模也执行同一算法。最大输入规模为一千万，本次默认只运行到一百万。

本次加速比只反映验证前提成立时的核心求解开销。对未知输入采用完整排序做重复值预检查，本身还需额外 $O(n\log n)$ 时间，实际应用不能忽略这部分成本。

## 三、算法及参数化方式

一次尝试按以下步骤执行：

1. 从原数组独立、均匀、有放回抽取 $s$ 个元素，构成样本 $R$，用 std::sort 排序。
2. 使用 1-based 排名：

$$
j_{\rm low}=\operatorname{clamp}\!\left(\left\lfloor s/2-\alpha\sqrt n\right\rfloor,1,s\right),
\qquad
j_{\rm high}=\operatorname{clamp}\!\left(\left\lceil s/2+\alpha\sqrt n\right\rceil,1,s\right).
$$

3. 取 $d=R[j_{\rm low}-1]$、$u=R[j_{\rm high}-1]$，扫描原数组，构造 $C=\{x:d\le x\le u\}$，统计 $l_d=\#\{x<d\}$、$l_u=\#\{x>u\}$。
4. 若 $l_d<r\le n-l_u$ 不成立，返回 FAIL_BRACKET；否则若 $|C|>4s$，返回 FAIL_SIZE。
5. 仅在两项检查均通过后，用 std::sort 排序 $C$，返回 $C[r-l_d-1]$。

原始记录无论优先返回哪种失败状态，都保留“目标排名在区间内”和“候选集合超限”两个独立布尔量，并记录两端排名是否夹取。实现没有使用 Quickselect 或 std::nth_element。

完整求解从一次 seed 初始化一个随机状态，失败后推进相同状态重新抽样，不重复设为同一 seed。最多尝试 100 次；达到上限返回 RETRY_LIMIT，保留耗时和尝试次数，不静默改用完整排序。

## 四、正确性与复杂度

### 4.1 成功结果的正确性

扫描后，原数组被严格划分为小于 $d$、位于 $[d,u]$ 和大于 $u$ 的三个部分，个数分别为 $l_d,|C|,l_u$。因而 $|C|=n-l_d-l_u$。当 $l_d<r\le n-l_u$ 时，原目标是 $C$ 中第 $r-l_d$ 小的元素，其零下标为 $r-l_d-1$。排序后返回该位置必定等于参考中位数。失败只是一次尝试未给出答案，不是错误答案。

### 4.2 单次尝试与完整求解

$$
T_{\rm attempt}=O(s\log s+n+|C|\log |C|).
$$

候选排序仅在 $|C|\le4s$ 时执行；$s=\lceil n^{3/4}\rceil$ 且 $n^{3/4}\log n=O(n)$，故单次最坏时间为 $O(n)$。构造失败候选时仍可能存储至多 $n$ 个元素，额外空间最坏为 $O(n)$；成功尝试的样本和候选存储为 $O(s)$。

这些固定 $\alpha$ 的单次渐近复杂度相同，实测差异体现有限规模常数与重试成本，不代表不同理论复杂度。

若理想独立尝试的成功概率为 $p>0$，无限重试的期望尝试次数为 $1/p$，期望工作量为 $O(n/p)$；只有 $p$ 有正的常数下界时才能进一步称为期望 $O(n)$。限制为 $L$ 次时，模型中的超限概率为 $(1-p)^L$，实际程序明确报告超限，不将其当作成功。耗时统计包含已发生的所有失败。

### 4.3 参照参数的概率上界与实测区别

下面给出仅针对 $\alpha=1$、本实验不发生排名夹取且中间排名存在的规模的保守推导，不把原参照设置的常数直接套到其他 $\alpha$。

样本中小于或不大于目标的个数均服从相应二项分布，方差至多 $s/4$。两端括住目标失败分别要求偏离样本中心至少约 $\sqrt n$，按上述整数排名可得：

$$
\Pr(\text{FAIL\_BRACKET})\le \frac{s}{2n}.
$$

若两端在原数组中的排名都位于 $[r-2s,r+2s-1]$，则候选集合至多 $4s$ 个。超限必有一端超出该排名段。对应样本计数与边界排名的期望间隔至少为 $\sqrt n-1$：使用 $s^2/n\ge\sqrt n$，并保留整数取整误差。由 Chebyshev 不等式及并集上界：

$$
\Pr(\text{一次失败})\le
\frac{s}{2n}+\frac{s}{2(\sqrt n-1)^2}
=O(n^{-1/4}).
$$

这不是精确失败概率，常数也不等同于课件所有版本的表述。本实验参照参数观测如下：

__BOUND__

其他 $\alpha$ 的成功率由独立计数统计报告。本次未观察到失败，不表示概率为零；例如 1000 次全成功的 Wilson 95% 区间仍允许约 0.38% 的失败率。

## 五、环境、种子与计时口径

__ENV__

未推断 CPU 商品型号、内存大小或温度。绘图使用已有 Python 3.12 虚拟环境中的 matplotlib 3.11.2，中文字体为 Windows 微软雅黑，缓存放在 assignment-2 内。

- 单次尝试：$n=1000,10000,100000$，每个规模每个 $\alpha$ 1000 次，数据种子 101，共 15000 条。
- 完整求解：$n=1000,10000,100000,1000000$，数据种子 101、202、303，每份每种方法预热 2 次、记录 30 次。每个规模/设置共 90 条，包含排序基线，共 2160 条。
- 分阶段诊断：$n=100000$，每个 $\alpha$ 20 次，独立于主性能实验，共 100 条。
- 抽样主种子 2026110301；调度主种子 2026110302。各任务派生种子及完整 C++ 命令保存在 run_manifest.json。
- 新种子确认：数据种子 404、505、606，抽样/调度主种子为 2026110303/2026110304，比较 $\alpha=0.125,0.25,0.5$；每份数据每种设置预热 2 次、测量 30 次，含排序共 1440 条，单独保存。

同一试验轮的不同 $\alpha$ 使用相同初始抽样 seed，是配对比较；各方法仍自行在计时内采样和排序，不复用其他方法已算好的样本。不同参数之间不当作独立样本。每轮打乱参数顺序，完整求解的数据任务顺序也用固定种子打乱。

输入副本在各方法计时前准备。计时包含随机引擎初始化、抽样、两次排序、扫描与候选构造、失败重试及内部管理；不包含数据生成、文件 I/O、输入预检查、参考排序、最终比对和进程启动。排序基线也在计时前准备副本，只计完整排序及读取中位数。

先运行快速流程。首轮正式性能可能与快速绘图有短暂重叠，随后在没有绘图任务时完整重测了正式性能部分，最终 CSV 采用该轮；默认单次试验没有缩小。分阶段诊断不混入主耗时统计。

平均值、中位数和 P95 都包含失败重试与超限运行；P95 采用最近秩定义 $x_{\lceil0.95m\rceil}$，加速比为同规模完整排序平均时间除以随机算法平均总时间。若出现超限，该参数不得作为“成功求解平均时间最优”直接排名。

## 六、正确性和功能检查

C++ 测试共 9915 项断言通过，覆盖 3300 次单次检查，其中 2775 次成功、525 次允许失败，成功结果及之后的完整求解均与参考排序一致。覆盖：

- $n=1,2,3$ 等边界、奇偶长度、正负数、排序/逆序/随机排列、五种 $\alpha$ 和多个固定种子。
- 成功的候选排名换算、排名夹取、FAIL_BRACKET、FAIL_SIZE、两种事件同时发生、两次不同样本重试成功及 RETRY_LIMIT。
- 重复输入拒绝、空输入、非正/非有限参数和零重试上限。

指定失败分支使用可注入采样序列，只用于单元测试。正式数据只使用真实伪随机采样。另有 9 类真实 CLI 非法参数检查、含空格路径和固定 seed 非时间字段复现检查。记录在 tests.json。

正式 17260 条记录及确认试验 1440 条均已核对；所有成功答案正确。完整求解主实验和确认实验均未发生 RETRY_LIMIT。本次主实验未观察到 FAIL_SIZE、候选超限事件或排名夹取，不能据此删除相关分支或宣称其概率为零。

## 七、单次成功率与候选集合

__ATTEMPT__

![区间宽度与失败率](../results/figures/alpha_failure_rate.png)

![区间宽度与候选集合](../results/figures/alpha_candidate_size.png)

![单次尝试时间](../results/figures/alpha_attempt_time.png)

区间越窄，候选集合越小，但括住目标失败的次数明显增加。例如 $\alpha=0.125$ 在三种规模的成功率分别为 47.7%、60.9%、73.0%；$\alpha=0.25$ 为 78.7%、89.2%、97.1%。$\alpha=0.5$ 在最小规模仍有 16 次 FAIL_BRACKET，在其余两种规模本次未观察到失败。

平均 $|C|/n^{3/4}$ 接近 $2\alpha$，这里只是本次均匀排列、有放回抽样下的观测趋势，不替代实际扫描统计。候选中位数、成功率 Wilson 区间、超限与同时发生事件、两端夹取次数均在 attempt_summary.csv 保留。平均候选集合和尝试时间使用全部尝试，不只选择成功样本。

## 八、完整求解与最佳参数

__SOLVE__

![区间宽度与完整求解均值](../results/figures/alpha_solve_mean.png)

![规模与完整求解时间](../results/figures/n_solve_time.png)

![区间宽度与尝试次数](../results/figures/alpha_retry_count.png)

以获得正确中位数的平均总时间为目标，本次默认候选中的均值最低项为：

__BEST__

最窄区间虽然单次扫描后的排序量小，却需要更多失败重试。较宽区间常一次成功，但候选排序开销变大。综合两者，主实验均值最低项为 __BEST_ALPHAS__。这仅是本机、这些排列及默认候选中的观测排名，不能声称所有输入都由该参数严格获胜。

### 新数据和新抽样种子确认

部分均值差距只有约几个到十几个百分点，因此保留全部默认数据，并对较接近的三个候选追加新数据种子确认：

__CONFIRM__

__CONFIRM_NOTE__ 确认与主实验分别统计，没有把不同批次任意合并。未进行参数间显著性检验；接近的候选应视为表现相近，不能仅凭一次均值小差距宣称普遍最优。没有为预设某个参数获胜而删去失败或选择性去掉慢运行。

## 九、分阶段诊断

__PHASE__

![分阶段诊断](../results/figures/phase_diagnostic.png)

抽样、样本排序、扫描与候选构造、候选排序分别计时；其他开销为总时间减去四阶段。它包含 RNG 初始化、分配/释放、排名计算及计时管理等，阶段均值按全部尝试计算，失败未执行的候选排序计零。

这是独立的少量诊断，不能拿它的均值替换主实验时间。该批次部分设置的均值高于中位数，存在明显慢运行；尤其 $\alpha=1$ 的诊断总时间均值与中位数相差较大。保留全部记录，并避免据此断言精确阶段占比或因果关系。主实验没有这些额外阶段时钟调用。

## 十、局限与可选优化

1. 正式数据都是 $1,\ldots,n$ 的排列；正确性测试包含负数、排序和逆序，但未正式测量所有分布。
2. 单次成功率每个规模只有一个数据种子，且同轮参数配对；二项区间仅描述对应模型下的抽样误差，不是不同参数独立性的证明。
3. 未控制后台任务、CPU 温度和频率；计时有尾部慢运行，提供均值、中位数和 P95，未作显著性检验。随机打乱顺序可减轻顺序偏差，不能消除系统噪声。
4. 额外新种子确认不取代完整默认实验。可选的一千万规模和一百万单次成功率扩展未运行；它们不是本次默认配置的一部分。
5. 重复值采用拒绝策略，若要支持重复值，应扩展为“数值、原始下标”的全序版本。本实现未声称已支持任意重复输入。
6. 可比较复用缓冲、候选构造存储上限、其他固定种子与更多样本；主算法必须保留两次排序，不能用 nth_element 的结果冒充本算法。

## 十一、复现与文件

源码：src/median.hpp、src/driver.cpp；数据生成在 C++ 的 permutation 中；功能测试：tests/test_median.cpp。默认配置：config.json。调度、统计与绘图：tools/run.py、tools/analyze.py、tools/plot.py。报告表格由 tools/report.py 从已审计 CSV 生成。

主要命令见 README。正式每行 CSV 均能追溯 experiment、n、alpha、dataset_seed、sampling_seed、trial_id、status、sample_size、candidate_size、attempt_count、elapsed_ns、correctness。完整字段及单位在 README 列出。

results/raw 保存单次、完整求解和诊断的逐行数据，results/confirmation 单独保存新种子确认，results/quick 只用于快速检查且被 Git 忽略。audit.json 重算所有汇总，校验数量、成功答案、样本量、排名、配对 seed、失败优先级与尝试次数。所有返回结果均实际检查，未生成 PDF、未自动提交或推送。
"""
    for key,value in tokens.items():
        text=text.replace("__"+key+"__",value)
    assert "__" not in text
    path=ROOT/"docs/实验报告.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text.lstrip(),encoding="utf-8")
    print("PASS report generated from audited formal and confirmation CSVs")

if __name__=="__main__":
    main()
