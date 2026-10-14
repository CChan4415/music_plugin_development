---
title: Playground 说明
type: meta
status: solid
updated: 2026-10-14
---

# 50-Playground

可运行的代码实验。**这里的代码不是产品**，是为了搞懂一个概念而写的最小程序。

## 约定

- 一个实验一个目录：`exp-<主题>/`
- 每个实验必须有 `README.md` 说明：**我想验证什么**、**怎么运行**、**结论是什么**
- 结论要回写到 `30-Wiki/` 或 `20-Notes/`，否则实验等于没做
- 构建产物已在 `.gitignore` 中排除

## 建议的前几个实验

| 实验 | 验证什么 | 对应 Wiki |
|---|---|---|
| `exp-biquad-sweep/` | 手算的滤波器系数和代码输出是否一致 | [[Biquad 滤波器]] |
| `exp-zipper-noise/` | 不平滑参数会产生什么声音（能听出来的 bug） | [[参数平滑 parameter smoothing]] |
| `exp-aliasing/` | 不过采样做失真，混叠有多明显 | [[混叠 aliasing]] |
| `exp-denormal/` | denormal 到底让 CPU 慢多少 | [[denormal 数处理]] |
| `exp-latency-budget/` | 你的机器在 64 samples block 下有多少时间预算 | [[实时音频线程契约]] |

> [!tip] 实验的副产品比实验本身值钱
> 你为 `exp-aliasing` 写的扫频 + FFT 绘图脚本，后面每个插件都能复用。
> 把这些脚本放在 `50-Playground/tools/` 下。
