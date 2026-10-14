---
title: RBJ Audio EQ Cookbook
type: source
domain: dsp
status: solid
confidence: high
tags: [math, recipe]
source_type: standard
url: https://www.w3.org/TR/audio-eq-cookbook/
author: Robert Bristow-Johnson
year: 2005
created: 2026-10-14
updated: 2026-10-14
---

# RBJ Audio EQ Cookbook

> [!important] 这是双二阶滤波器系数的**权威版本**
> 你以后写的每一个 EQ、每一个滤波器，系数都从这里来。
> 更重要的是：**它是你核对 AI 输出的标准答案。**

## 元信息

| 项 | 值 |
|---|---|
| 类型 | 公式集（cookbook） |
| 作者 | Robert Bristow-Johnson（"RBJ"） |
| 原始发布 | musicdsp.org，2005 |
| **权威托管** | **W3C**（为 Web Audio API 适配）→ <https://www.w3.org/TR/audio-eq-cookbook/> |
| 另一版本 | <https://www.musicdsp.org/en/latest/Filters/198-rbj-audio-eq-cookbook.html> |

> [!tip] 为什么推荐 W3C 那一版
> 因为 W3C 明确写了 **"Adapted from Audio-EQ-Cookbook.txt, by Robert Bristow-Johnson, with permission"**，
> 并且它是为 Web Audio 规范适配的——**公式完整、格式规范、有官方背书**。
> musicdsp 那版是原始出处，但格式较旧（且评论区暴露了一个历史版本的公式差异，见下）。

## 覆盖的滤波器类型

| 类型 | 用途 |
|---|---|
| LPF / HPF | 低通 / 高通 |
| BPF（两种：constant skirt gain / constant 0dB peak gain） | 带通 |
| notch | 陷波 |
| APF | 全通（混响扩散器用，见 [[全通滤波器 allpass]]） |
| **peakingEQ** | **峰值 EQ —— 你最常用的那个** |
| lowShelf / highShelf | 低架 / 高架 |

## 关键公式（我核对过的部分）

**中间变量**：

$$\omega_0 = 2\pi \frac{f_0}{F_s} \qquad A = 10^{\mathrm{dBgain}/40}$$

$$\alpha = \frac{\sin\omega_0}{2Q} \quad(\text{Q 定义}) \qquad \alpha = \sin\omega_0 \sinh\!\left(\frac{\log 2}{2}\,\mathrm{BW}\,\frac{\omega_0}{\sin\omega_0}\right) \quad(\text{BW 定义})$$

**三种 α 定义** —— 这是关键：**Q / BW / S 是三种不同的参数化**，
同一个"滤波器类型"用不同定义会得到**不同的曲线形状**。
这就是"为什么两个 EQ 听起来不一样"的原因之一。

**peakingEQ 系数**：

```
b0 = 1 + α·A        b1 = -2·cos(ω0)     b2 = 1 - α·A
a0 = 1 + α/A        a1 = -2·cos(ω0)     a2 = 1 - α/A
```

> [!warning] `A = 10^(dBgain/40)` —— 不是 `/20`
> 这是 AI 最常写错的地方。写成 `/20` 会让实际增益**翻倍**（dB）。
> 验证方法：设 dBgain=6，在中心频率测增益，应正好 +6 dB。
> 我在 [[Biquad 滤波器]] 里实测过这个公式。

**Q ↔ BW 换算**（W3C 原文给出）：

$$\frac{1}{Q} = 2\sinh\!\left(\frac{\log 2}{2}\cdot \mathrm{BW}\cdot \frac{\omega_0}{\sin\omega_0}\right)$$

## ⚠️ 一个已知的历史版本差异

> [!warning] 搁架滤波器（shelf）的公式有过改动
> musicdsp 的评论区里有人报告：**`S`（shelf slope）定义的 α 在高采样率下会产生异常共振**，
> 而旧版用 `beta` 的公式工作正常。
>
> RBJ 本人的回复是：他把 `beta` 换成了 `alpha` 以去掉一个中间变量，
> **系数方程也相应改了**——他认为两者在相同参数下应给出相同系数。
>
> **对你的意义**：
> - 用**搁架滤波器**时，如果 AI 给的系数在 96kHz/192kHz 下出现异常共振，**可能是抄了混合版本**
> - 用 W3C 的完整版本（alpha 与系数方程配套）
> - **自己用 FFT 实测验证**，不要盲信任何一版

## 怎么用它验证 AI 输出

> [!tip] 这是最高频的核对场景
> 让 AI 写 EQ 时，按这个清单查：
>
> | # | 查什么 | 常见错误 |
> |---|---|---|
> | 1 | `A = 10^(dB/40)` | 写成 `/20` |
> | 2 | 系数是否**除以 a0 归一化** | 忘了归一化 → 增益不对 |
> | 3 | 差分方程的符号约定 | `+a1·y[n-1]` vs `-a1·y[n-1]` 混用 |
> | 4 | `α` 用的是哪种定义 | Q / BW / S 混用 |
> | 5 | 搁架滤波器是否抄了混合版本 | 高采样率下异常共振 |
>
> 验证手段：`audio_io.check_response()` —— 和解析解逐点对比。

## 相关

- [[Biquad 滤波器]] — 本库的实现 + 实测验证
- [[exp-002 Biquad 滤波器]] — 可运行实验
- [[滤波器设计]]
- [[全通滤波器 allpass]]
- [[过采样 oversampling]]
- [[MOC - DSP]]

> [!note] 待补充
> - 搁架滤波器完整系数（本页只列了 peakingEQ）
> - 三种 α 定义在同一 f0/Q 下的实际曲线差异（值得画图对比）
