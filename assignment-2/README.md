# 抽样区间宽度对随机化中位数算法性能的影响

固定样本量 $s=\lceil n^{3/4}\rceil$ 和候选上限 $4s$，比较 $\alpha=0.125,0.25,0.5,1,1.5$ 对单次成功率、候选集合、单次尝试和含失败重试的完整求解时间的影响。偶数长度返回上中位数；输入必须非空且元素互异，重复值在计时外明确拒绝。

[实验报告](docs/实验报告.md) · [完整求解均值](results/figures/alpha_solve_mean.png) · [失败率](results/figures/alpha_failure_rate.png) · [候选集合](results/figures/alpha_candidate_size.png) · [规模耗时](results/figures/n_solve_time.png)

## 目录

~~~text
src/median.hpp        算法、均匀采样和数据生成
src/driver.cpp        C++ 批量实验驱动、核心计时、正确性核对和 CSV
tests/test_median.cpp 分支与功能测试（注入采样只用于测试）
tools/run.py          编译、测试、快速/正式/新种子确认调度及审计
tools/analyze.py      汇总和原始数据一致性审计（标准库）
tools/plot.py         matplotlib 绘图，读取真实 CSV
tools/report.py       由正式数据生成中文报告
config.json           默认正式实验参数
docs/实验报告.md       实测报告
results/raw/          正式原始记录，按任务分片
results/figures/      七类图与可视检查拼图
results/confirmation/ 新数据和采样种子确认结果
build/                编译产物，被 Git 忽略
~~~

## 编译、测试与运行

需要 Windows 上的 GCC、C++17 与 Python 3。算法、数据生成和核心计时均在 C++ 中，Python 只调度、统计和绘图。GCC 的 128 位整数扩展用于精确计算样本量的整数上取整，当前 MSYS2 GCC 16.1.0 支持；迁移 MSVC 时须替换该辅助计算。没有使用 Quickselect 或 nth_element。

在 PowerShell 中：

~~~powershell
Set-Location 'D:/CPP/random/assignment-2'
$env:PYTHONIOENCODING = 'utf-8'
python tools/run.py build
python tools/run.py test
python tools/run.py run --profile quick
~~~

快速模式只检查流程：单次 $n=100,1000$ 各参数 20 次；完整求解每设置 3 次、1 个数据种子；诊断每参数 3 次。保存在 results/quick，不能作为正式结果。

本机复用了 assignment-1 已有的绘图环境，不修改该环境内容或安装大型依赖：

~~~powershell
$plotPython = '..\assignment-1\.plot-venv\Scripts\python.exe'
& $plotPython tools/plot.py --results results/quick
~~~

若该环境不存在，使用已经装有 matplotlib 的 Python 运行。绘图脚本使用微软雅黑，字体缺失会明确报错，需要配置已有 CJK 字体；脚本不自动安装依赖，也不改系统全局配置。

正式实验、确认与报告：

~~~powershell
python tools/run.py run --profile formal
python tools/run.py audit --profile formal
python tools/run.py run --profile confirmation
python tools/run.py audit --profile confirmation
& $plotPython tools/plot.py
python tools/report.py
~~~

可用 python tools/run.py all --profile quick 一次编译、测试并运行快速数据；绘图仍单独执行。所有脚本以参数数组调用子进程，C++ 输出和输入路径支持空格。

## 正式配置与复现

config.json 是默认正式配置，不为更快完成而缩小：

| 实验 | 规模 | 数据种子 | 重复次数 |
|---|---|---|---|
| 单次尝试 | 1000、10000、100000 | 101 | 每个 $\alpha$ 1000 次 |
| 完整求解及排序 | 1000、10000、100000、1000000 | 101、202、303 | 每数据/设置预热 2 次、记录 30 次 |
| 分阶段诊断 | 100000 | 101 | 每个 $\alpha$ 20 次 |

完整求解最大尝试次数 100；含排序共 2160 条记录，每个规模/设置 90 条。单次 15000 条、诊断 100 条。数据为 C++ 生成的 $1,\ldots,n$ 随机排列，只保存配置和种子，不保存大数组。数据种子与抽样种子分开。

抽样主种子为 2026110301，调度主种子为 2026110302。各任务派生种子、编译环境、源码和可执行文件哈希均保存。每轮不同参数配对使用相同初始 seed，并打乱设置顺序；每种方法自行在计时内执行采样、排序等全部运算。

confirmation 是独立补充，不替代默认正式实验：候选参数 0.125、0.25、0.5；数据种子 404、505、606；抽样/调度主种子 2026110303/2026110304；每数据/设置预热 2 次、测量 30 次，含排序共 1440 条。用新种子检查接近的参数排名。

可选的一千万完整求解规模和一百万单次实验没有默认启用。样本两端排名夹取会明确记录，没有小规模静默排序回退；重复输入拒绝，不声称支持任意重复值。

续跑：

~~~powershell
python tools/run.py run --profile formal --resume
python tools/run.py run --profile formal --stage solve
python tools/run.py audit --profile formal
~~~

resume 校验配置和程序哈希，跳过行数完整的任务分片；最终审计重新校验内容。stage 可取 attempt、solve、diagnostic、all。子任务成功后以临时文件替换结果分片，中断文件不参与汇总。不要在重建不同程序后混用旧结果。最终必须运行完整 audit。

## C++ 单任务接口

~~~powershell
.\build\median.exe --mode attempt --n 1000 --dataset-seed 101 --trials 1000 --warmups 0 --max-attempts 100 --master-seed 123 --schedule-seed 456 --alphas 0.125,0.25,0.5,1,1.5 --output 'build\result with spaces.csv'
~~~

所有选项必填。mode 为 attempt、solve 或 diagnostic；n 为 1..10000000；trials、max-attempts 为正数；warmups 为非负数；三类 seed 为无符号 64 位整数；alphas 为不重复、有限正数的逗号分隔列表。solve 自动增加完整排序基线。错误参数或错误答案非零退出，不写假成功。

算法接口位于 median.hpp。调用核心前执行 checked_reference 和 validate_alpha，分别在计时外检查互异输入和参数。一次失败返回结构体而非错误答案；solve 只推进采样状态重试，超限返回 RETRY_LIMIT。测试的 Sequence 采样器不会进入正式驱动。

## 计时口径

输入副本在各方法计时前准备。随机算法计时包含随机状态初始化、样本抽取/排序、扫描、候选构造/排序、必要重试和管理；排除数据生成、文件 I/O、合法性预检查、参考排序、结果核对和进程启动。排序基线只计排序及读取中位数。所有成功答案在计时后核对。

分阶段诊断单独运行，不混入主要总耗时；阶段未执行时记零，残差包含初始化、分配释放、排名计算等。若要比较端到端应用，须另算排序式重复值预检查等开销。

## 原始 CSV 字段

attempt 与 diagnostic 每行代表一次尝试；solve 每行代表一个完整调用（可能含多次失败重试）或一次完整排序。所有时间单位为纳秒，布尔字段为 0/1。

| 字段 | 定义 |
|---|---|
| experiment | attempt / solve / diagnostic |
| n、alpha、method | 输入规模、区间参数、randomized / sort；sort 的 alpha=0 为不适用标记 |
| dataset_seed、sampling_seed | 数据生成种子、本次调用的初始采样种子；基线也记录配对轮次 seed |
| trial_id | 去掉预热后的零起始轮次 |
| status | OK / FAIL_BRACKET / FAIL_SIZE / RETRY_LIMIT |
| sample_size | $s=\lceil n^{3/4}\rceil$；基线为 0 |
| j_low、j_high | 夹取后的 1-based 样本边界排名 |
| low_clamped、high_clamped | 两端排名是否夹取 |
| candidate_size | 实际 $\lvert C\rvert$；solve 记录最后一次尝试，基线为 0 |
| rank_in_bracket、size_exceeded | 两个独立事件标志，失败优先级不掩盖同时发生 |
| attempt_count | 完整调用实际尝试次数；单次和基线为 1 |
| bracket_failures、size_failures | 完整调用各类优先失败状态的累计次数；同时事件另看单次布尔标志 |
| elapsed_ns | 核心总时间，solve 包含全部重试 |
| correctness | 成功答案核对为 true，失败未返回答案为 NA；错误答案直接报错 |
| answer、reference | 成功结果与排序参考，失败的 answer 为空 |
| sampling_ns、sample_sort_ns、scan_ns、candidate_sort_ns | 仅 diagnostic 分别记录阶段时间；其他模式为 0 |

## 汇总与结果

- attempt_summary.csv：成功及两类失败次数、成功率与 Wilson 95% 区间、全部尝试的候选均值/中位数及除以 $n^{3/4}$ 的指标、独立超限/同时事件、夹取次数、尝试耗时均值/中位数/P95。
- solve_summary.csv：包括超限运行的均值、中位数、P95、平均和总尝试次数、累计失败、相对排序均值加速比。P95 使用最近秩。出现超限的设置不直接参与最优成功求解参数排名。
- diagnostic_summary.csv：单次统计与阶段均值、总时间和管理残差，包含失败记录。
- environment.json：实际构建命令、编译器、操作系统、可靠处理器标识、Python、程序及源码哈希。
- tests.json、audit.json：真实功能检查及原始记录/汇总重算结果。
- run_manifest.json：实际配置、模式、种子派生、任务命令和行数。

报告与图表根据正式 CSV 生成，不使用模拟耗时或测试替身。零失败只表示本次未观察到失败。概率上界和实测频率、固定 $\alpha$ 的共同渐近复杂度和有限规模常数均分开讨论。

本阶段不生成 PDF，不自动提交或推送 Git。build、缓存、quick 结果被忽略；正式原始 CSV、配置、种子和图表保留用于复现。assignment-1 及用户已有改动不覆盖。
