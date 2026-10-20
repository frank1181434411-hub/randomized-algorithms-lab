# Freivalds 矩阵乘法随机验证实验

验证整数方阵 AB=C，比较 O(n³) 精确算法与 O(kn²) Freivalds 算法。正式实现、验证、性能与漏检实验、8 张图和报告初稿已完成，尚未导出 PDF。

入口：[实验报告](docs/实验报告.md)、[规模耗时](results/figures/n_time.png)、[加速比](results/figures/speedup.png)、[漏检率](results/figures/probability.png)。

## 目录与环境

~~~text
src/solver.cpp  正式算法、输入检查、核心计时与 JSON 输出
tools/          生成、独立检查、调度、自测、绘图与打包
build/          reference.exe、solver.exe、solver_build.json
data/           输入、元数据、manifest.json 与漏检配置
results/        正式 CSV、环境记录、检查摘要、figures/ 图片
docs/           实验报告.md
~~~

Windows 11、MSYS2 GCC 16.1.0、C++17、-O2。数据与性能工具使用 Python 3.14.6，正式漏检与绘图使用 Windows Python 3.12。除绘图外不需要第三方 Python 包；绘图库 matplotlib 3.11.2 已安装在本机 .plot-venv。脚本不会自动安装依赖。

## 当前结果

- 35 例数据完整性与 C++ 真值检查、27 例 Python 任意精度交叉检查、5 组工具自测通过。
- 正式正确性 286 次全部 OK：exact 26 次、Freivalds 260 次；额外 157 项检查通过。
- 性能 440 条记录、22 组汇总。n=512、k=10：exact 中位数 335.315450 ms，Freivalds 为 7.219450 ms，加速约 46.45 倍。
- 正式漏检共 50000 次，各 k=1、2、4、8、10 均运行 10000 次，漏检数分别为 5028、2487、625、47、10。

一般错误矩阵的 2⁻ᵏ 为理论上界，本次单点构造在独立均匀随机模型下恰为该值。实测样本频率允许高于理论概率。实现使用可复现伪随机数，模型与实测的边界见报告。

## 编译与构建记录

PowerShell 中执行，编译成功后记录真实环境：

~~~powershell
Set-Location 'D:/CPP/random/assignment-1'
$env:PYTHONIOENCODING = 'utf-8'
python tools/project.py build
$solverArgs = @('-std=c++17', '-O2', '-Wall', '-Wextra', 'src/solver.cpp', '-o', 'build/solver.exe')
& g++ @solverArgs
if ($LASTEXITCODE -ne 0) { throw 'solver build failed' }
$solverRecord = @{
    command = @('g++') + $solverArgs
    compiler = ((& g++ --version) -join [Environment]::NewLine)
    optimization = '-O2'
    os = [System.Environment]::OSVersion.VersionString
    machine = $env:PROCESSOR_ARCHITECTURE
    processor = $env:PROCESSOR_IDENTIFIER
}
$solverJson = $solverRecord | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText("$PWD/build/solver_build.json", $solverJson, [System.Text.UTF8Encoding]::new($false))
~~~

project.py build 只编译 reference.exe，后续步骤构建正式 solver.exe。性能调度保存构建记录及程序哈希至 [solver_environment.json](results/solver_environment.json)，不能借用参考程序的构建信息。源码或数据改变后应重新测量、更新报告。

## 检查与正式实验

数据已附，无需重新生成。以下命令会更新对应结果：

~~~powershell
python tools/project.py check
python tools/selftest.py
python tools/experiments.py correctness --exe build/solver.exe
python tools/experiments.py performance --exe build/solver.exe --provenance build/solver_build.json
python tools/experiments.py probability --exe build/solver.exe
python tools/experiments.py analyze --raw results/timing_raw.csv
~~~

正确性默认每例 exact 一次、Freivalds 十次，k=10。随机漏检记为 MISS，不自动判为 BUG；正确输入被拒绝或 exact 与真值不同才是 BUG。

性能按组合预热 2 次、测量 10 次，两个同规模数据种子合并为每组 20 条，取核心耗时中位数。参数为 --warmups、--repeats、--fixed-n。性能命令串行执行，应减少后台负载。

漏检默认各 k 试验 10000 次，可用 --trials 调整。标准 CLI 串行启动独立进程，可能较慢。本次正式结果按相同调用与种子规则，以 8 个线程并发调用独立进程，最终按原顺序汇总；见 [probability_execution.json](results/probability_execution.json)。漏检在性能测量完成后运行，其进程耗时不用于性能比较。串行命令可复现接受记录与统计，墙钟耗时不同。

未传 --exe 时三类实验输出 SKIP，不生成 CSV；显式传不存在的程序则报错。自测中的临时替身只检查基础设施，不作为正式结果。

## 绘图与结果文件

本机已有可用 .plot-venv：

~~~powershell
$env:MPLBACKEND = 'Agg'
$env:MPLCONFIGDIR = "$PWD/.plot-venv/mplconfig"
.\.plot-venv\Scripts\python.exe tools/plot.py
~~~

新环境可先使用原生 Windows Python：

~~~powershell
py -3.12 -m venv .plot-venv
.\.plot-venv\Scripts\python.exe -m pip install matplotlib==3.11.2
~~~

若 py 启动器找不到安装，用 Python 3.12 的实际完整路径替代 py -3.12。MSYS2 Python 可能缺少兼容 wheel。绘图读取正式 CSV，没有数据则跳过。

| 文件 | 内容 |
|---|---|
| [correctness.csv](results/correctness.csv) | 286 次正确性结果 |
| [timing_raw.csv](results/timing_raw.csv) | 440 条性能记录，含核心和进程时间 |
| [timing_summary.csv](results/timing_summary.csv) | 22 组中位数、归一化指标、倍率和加速比 |
| [probability_raw.csv](results/probability_raw.csv) | 50000 次的种子与接受结果 |
| [probability.csv](results/probability.csv) | 漏检率、理论概率和期望次数 |
| [solver_validation.json](results/solver_validation.json) | 157 项额外检查摘要 |
| [experiment_validation.json](results/experiment_validation.json) | 正式输出一致性检查摘要 |

| 图表 | 内容 |
|---|---|
| [n_time.png](results/figures/n_time.png) | 规模与耗时 |
| [k_time.png](results/figures/k_time.png) | n=256 的轮数与耗时 |
| [speedup.png](results/figures/speedup.png) | 相对 exact 加速比 |
| [adjacent_ratio.png](results/figures/adjacent_ratio.png) | 相邻规模耗时倍率 |
| [normalized_n2.png](results/figures/normalized_n2.png) | T/n² |
| [normalized_n3.png](results/figures/normalized_n3.png) | T/n³ |
| [normalized_kn2.png](results/figures/normalized_kn2.png) | T/(kn²) |
| [probability.png](results/figures/probability.png) | 实测漏检率与理论值 |

## 数据安排与重建

- 正确性：26 例，n=1、2、3、4、5、7、8，覆盖结构矩阵、随机/负数和多种错误。
- 性能：n=64、128、256、512，各种子 101、202，共 8 例正确乘积；1024 尚未正式测量。
- 规模扫描：k=5、10、20；exact 每个 n 测 k=1。
- 轮数扫描：n=256，k=1、2、5、10、20、40。
- 漏检：n=16，数据种子 314159，单点加 1，主种子 271828。

默认拒绝覆盖，确需重建或扩展时执行：

~~~powershell
python tools/project.py generate --force
# 可选扩展；改变清单后重跑检查和实验
python tools/project.py generate --sizes 64 128 256 512 1024 --seeds 101 202 --force
~~~

新 manifest 以本次集合为准，旧的非清单文件不删除、不参与实验。

## 打包与提交

~~~powershell
python tools/package.py
~~~

生成 freivalds.zip、PACKAGE_MANIFEST.json、PACKAGE_VERIFY.json，收集源码、文档、工具、build、data、results 和 README，校验包内文件哈希；不打包虚拟环境。提交前检查 PACKAGE_VERIFY.json。

旧阶段压缩包、旧验收脚本、初期抽查、无效虚拟环境和缓存已清理。本次文档更新没有生成新的提交包。保留正式原始数据、8 张图、当前构建和检查记录，以及后续绘图需要的 .plot-venv。build 与 figures 默认被 Git 忽略，应按课程要求另附或明确加入提交。

## 数据与接口约定（schema_version=1）

### 输入与数值

ASCII 文本：第一行仅一个十进制整数 n，1≤n≤1024；随后恰好 3n 行，依次为 A、B、C，每行恰好 n 个以空格分隔的十进制整数。无注释、空行或尾随额外内容，文件以 LF 换行。行列索引均从 0 开始。A/B 为整数，默认 0～9，少量小例 -9～9；C 为实际乘积加明确记录的整数修改。不是模运算，也不使用浮点数。

C++ 矩阵与累加器使用 ll（long long，本环境为 64 位）。设元素绝对值≤9，则单项乘积≤81，AB 元素绝对值≤81n；本项目修改最多 +2，候选 C 元素绝对值≤81n+2。n≤1024 时分别≤82944、82946。二元 r 下 Br≤9n、A(Br)≤81n²、Cr≤81n²+2；后者上界 84934658，差的保守界≤162n²+2=169869314，远小于 int64_t 上限。C 的总修改绝对值最多 3，因此上述 +2 的 Cr 界对当前多点布局也成立（每行最多 2）；这些边界不能外推到任意扩展输入。检查工具拒绝超出范围的输入。

### 元数据与清单

每个 txt 对应同目录同名 json，UTF-8。`data/manifest.json` 包含 schema_version 和 cases（相对 data 的元数据路径），只检查/调度清单内的用例；旧的非清单文件不参与。生成器拒绝同名覆盖，`--force` 才允许重建生成文件。

| 字段 | 类型与含义 |
|---|---|
| schema_version | 整数 1 |
| case_id | 唯一字符串，与输入文件 stem 一致 |
| seed | 非负整数，mt19937_64 种子 |
| n | 方阵规模 |
| group | correctness / performance / probability |
| data_type | random / zero（A 为零）/ identity（A 为单位阵）/ diagonal（A、B 为对角阵） |
| element_range | A/B 允许的闭区间 [low,9]，不要求端点一定出现 |
| candidate_abs_bound | 81n+2，C 的保守绝对值界 |
| truth | JSON 布尔值，AB=C 的真值 |
| modifications | 相对真实乘积的修改列表，每项 row、col、delta；位置不重复，delta 非零，正确乘积为 [] |
| input_file | 同目录输入文件名 |
| sha256 | 输入原始字节的 SHA-256，64 位小写十六进制 |

生成器固定使用 mt19937_64，加显式拒绝采样映射到闭区间，按行先 A 后 B 抽样；结构矩阵先抽样再置零、写对角元素。相同生成工具、参数和种子得到相同文件。参考工具 CLI：`reference.exe generate <output> <n> <seed> <kind> <mutation> <low>`，mutation 为 none/single/multi/cancel；日常优先通过 project.py 管理元数据。`reference.exe check <input>` 仅输出 `{"accepted":true}` 或 false，不提供正式算法或核心计时。

`probability_config.json`：case_id 指向唯一漏检用例，rounds=[1,2,4,8,10]、trials=10000、master_seed=271828、vector_distribution 为独立均匀二元向量、exact_probability="2**(-k)"。调度器 `--trials` 可覆盖次数，输出 CSV 记录实际次数。

### 正式程序接口

```text
solver.exe --input <路径> --algorithm exact|freivalds --rounds <正整数k> --seed <uint64十进制>
```

所有参数必选，路径以单独参数传递，支持空格。成功退出码 0，标准输出恰好一行 JSON，标准错误承载诊断；失败退出非零，不得用 accepted=false 伪装运行错误。正式 JSON 至少包含：

```json
{"accepted":true,"elapsed_ns":12345,"algorithm":"freivalds","rounds":10,"seed":271828}
```

accepted 必须是真布尔，elapsed_ns 必须为非负整数，algorithm/rounds/seed 必须原样回显。可以增加字段，但不要增加 stdout 日志。exact 忽略 rounds 的算法意义，仍回显传入值。seed 保持整数，不能经双精度中转丢失 64 位精度。

Freivalds 的每轮 r 各坐标独立均匀取 0/1，轮间更新随机状态，比较完整整数 A(Br) 和 Cr；一旦不等可拒绝，正确输入必须走完 k 轮。每次调用仅用给定 seed 初始化一次，禁止每轮重置。实现使用 mt19937_64，每个输出最多提供 64 个二元分量。

elapsed_ns 为 steady_clock 统计的完整验证核心时间，含生成随机向量与验证所需临时内存，排除输入解析、进程启动、输出和数据生成。必须使用结果（至少写 accepted），避免优化删除计算。单次调用超时 120 秒，非零退出、超时、JSON 错误、类型错误和回显不符都是调度失败。

性能调度所需 `solver_build.json` 必填 compiler（完整版本）、optimization（固定 "-O2"）、os、machine（可靠可得的机器描述）、command（实际编译参数数组）。可增加 cpu、内存等已知信息，不可捏造。脚本存档此内容并加入可执行文件哈希；它不能替代编译过程的真实性。

### CSV 字段

UTF-8，第一行字段名，逗号分隔，空值表示指标不适用；时间均为纳秒。布尔值在 CSV 中为 True/False。

| 文件 | 字段（按输出顺序） |
|---|---|
| correctness.csv | case_id, algorithm, k, seed, truth, accepted, status |
| timing_raw.csv | sweep, case_id, n, algorithm, k, repeat, seed, accepted, elapsed_ns, process_ns |
| timing_summary.csv | sweep, n, algorithm, k, samples, median_ns, T_per_n2, T_per_n3, T_per_kn2, speedup, previous_n, adjacent_ratio, local_exponent |
| probability_raw.csv | k, trial, seed, accepted |
| probability.csv | k, trials, misses, observed_rate, theoretical_probability, expected_misses |

sweep=n 为规模扫描，sweep=k 为固定规模轮数扫描。repeat/trial 从 0 开始，不含预热。elapsed_ns 是程序回报的核心时间；process_ns 是 Python 围住整个子进程的 perf_counter_ns 墙钟时间。samples 为合并相同 sweep/n/algorithm/k 后的样本量；中位数可以是 .5 纳秒。

status=OK / BUG_FALSE_REJECT / BUG_EXACT / MISS；MISS 只是随机算法漏检记录。speedup 是同一规模 exact(k=1) 中位数除以 freivalds 中位数，默认仅 n 扫描可得；previous_n 为同组前一规模；adjacent_ratio=T(n)/T(previous_n)；local_exponent=log(倍率)/log(n/previous_n)。三个归一化指标分别为 T/n²、T/n³、T/(kn²)，解释时只采用对应算法的适当指标。

misses 为错误 C 被接受次数；observed_rate=misses/trials；theoretical_probability=2^(-k)，expected_misses=trials×2^(-k)。这是指定单点构造的精确理论值；一般错误矩阵仅有概率上界。抽样波动可以超过该值，零观测不等于零真实概率。
