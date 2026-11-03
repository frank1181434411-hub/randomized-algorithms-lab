# 随机化算法课程仓库

记录随机化算法课程的编程作业、实验代码、测试数据和实验报告。

## 已有内容

| 目录 | 主题 | 内容 |
|---|---|---|
| [assignment-1](assignment-1/README.md) | Freivalds 矩阵乘法随机验证 | 精确验证与随机验证实现、正确性检查、性能与漏检实验、图表和报告初稿 |
| [assignment-2](assignment-2/README.md) | 抽样区间宽度与随机化中位数 | 两次排序的抽样算法、失败重试、默认正式实验、新种子确认、图表和中文报告 |

## 作业一：Freivalds 矩阵乘法随机验证

给定整数方阵 A、B、C，判断 AB=C。比较 O(n³) 的精确验证与 O(kn²) 的 Freivalds 随机验证，分析运行时间和漏检概率随规模、验证轮数的变化。

已完成两种算法实现、测试数据与独立真值检查、正式性能和漏检实验，并生成 8 张图表及实验报告初稿。

- [运行说明与实验结果](assignment-1/README.md)
- [算法源码](assignment-1/src/solver.cpp)
- [实验报告](assignment-1/docs/实验报告.md)
- [规模与运行时间](assignment-1/results/figures/n_time.png)
- [加速比](assignment-1/results/figures/speedup.png)
- [实测漏检率与理论概率](assignment-1/results/figures/probability.png)

代码使用 C++17，数据检查与实验调度使用 Python，绘图使用 matplotlib。编译、复现实验和依赖说明见作业目录内的 README。

## 作业二：抽样区间宽度与随机化中位数

固定样本量和候选集合上限，比较五种抽样排名区间参数的成功率、候选大小、单次尝试和含失败重试的完整求解耗时。默认性能实验运行到一百万元素，并用新数据与新采样种子确认接近参数的表现。

- [运行说明与字段定义](assignment-2/README.md)
- [算法实现](assignment-2/src/median.hpp)
- [中文实验报告](assignment-2/docs/实验报告.md)
- [区间参数与完整求解均值](assignment-2/results/figures/alpha_solve_mean.png)
- [单次失败率](assignment-2/results/figures/alpha_failure_rate.png)
