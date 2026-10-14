---
title: Think DSP (Allen B. Downey)
type: source
domain: dsp
status: solid
confidence: high
tags: [python, math]
source_type: book
url: https://greenteapress.com/wp/think-dsp/
author: Allen B. Downey
year: 2016
created: 2026-10-14
updated: 2026-10-14
---

# Think DSP — Digital Signal Processing in Python

> [!important] 为什么这份资料对你是第一优先
> **它是"用 Python 学 DSP"，正好是你现在的路径**（C++ 为 0，会 Python）。
> 作者的核心理念写在简介里：**"如果你会编程，你就能用这个技能学别的东西。"**
>
> 他还明确批评了传统 DSP 教材的顺序：
> > "大多数书（和用它们的课）是自下而上的，从相量（phasor）这样的数学抽象开始。"
>
> 他的做法是**自上而下**：第一章结束你就能把声音分解成谐波、修改谐波、生成新声音。
> **这和我们知识库的"先听到声音"原则完全一致。**

## 元信息

| 项 | 值 |
|---|---|
| 类型 | 免费在线书 + PDF + Jupyter notebooks |
| 作者 | Allen B. Downey（也是 *Think Python* / *Think Stats* 的作者） |
| 链接 | <https://greenteapress.com/wp/think-dsp/> |
| 代码 | <https://github.com/allendowney/thinkdsp> |
| 语言 | Python（用 numpy / scipy / matplotlib） |
| **许可证** | **CC BY-NC 3.0 — 禁止商业使用** ⚠️ |

> [!warning] 许可证提醒
> 这是 **NonCommercial**。学习完全没问题，但**不要把它的大段内容搬进商业产品**。
> 按本知识库的规矩：这里只留链接 + 我自己的理解，不复制原文。

## 覆盖内容

按书的章节顺序（自上而下，从"能听到"开始）：

| 章 | 主题 | 对插件开发的意义 |
|---|---|---|
| 1 | 声音与信号 | 生成正弦、读写 WAV —— **和 `exp-001` 完全对应** |
| 2 | 谐波 | 加法合成的数学基础 |
| 3 | 非周期信号 | 噪声、自相关 |
| 4 | 噪声 | 白噪声、粉噪声、功率谱 |
| 5 | 自相关 | 音高检测（**我们踩过"过零计数"的坑，见 [[2026-10-14 第一次验证：过零计数为什么错了]]**） |
| 6 | 离散余弦变换 | 频域分析入门 |
| 7 | 离散傅里叶变换 | DFT → [[FFT 与 STFT]] |
| 8 | 滤波与卷积 | 滤波器、卷积、[[延迟线 delay line]] |
| 9 | 微分与积分 | 信号的变化率 |
| 10 | LTI 系统 | 线性时不变系统 —— **DSP 的理论核心** |
| 11 | 调制与采样 | 采样、混叠、[[过采样 oversampling]] |

## 关键内容摘要（我的理解）

> [!note] 以下是我的理解，不是原文摘录

1. **代码优先于公式**。Downey 用可运行的 Python 讲概念，而不是先推公式。
   这对"数学忘了但会编程"的人是唯一可行的入口。

2. **频谱是理解一切的工具**。书里反复用 `Spectrum` 类画图。
   这印证了我们的经验：**验证 DSP 用 FFT，不要靠耳朵**（耳朵会骗你，见踩坑记录）。

3. **从"能听到"倒推到理论**。第一章就能出声，最后才讲 LTI 系统。
   这个顺序避免了"学三个月基础然后放弃"。

4. **自相关用于音高检测**（第 5 章）。
   我在 `exp-002` 里实测过：FFT 测低频音高不准（分辨率 = sr/N），
   自相关精度高得多（实测偏差 0.000%）。书里讲的就是这个。

## 可直接应用的点

- [ ] 把第 8 章（滤波与卷积）和第 11 章（采样与混叠）**对照我们的 `exp-002`/`exp-003` 读**
- [ ] 用它的 `thinkdsp.py` 作为参考，但**自己写**我们的 `audio_io.py`（已写）
- [ ] 第 5 章的自相关 → 补进 `audio_io.py`（已实现 `dominant_freq_autocorr`）
- [ ] 第 11 章 → 支撑 [[混叠 aliasing]] 和 [[过采样 oversampling]] 两页

## 怎么用它验证 AI 输出

> [!tip] 这份资料最适合当"AI 代码的对照答案"
> 因为它的代码**可运行、可对比**。
> 当你让 AI 写一个 FFT 或滤波器时：
> 1. 用 Think DSP 的写法跑一遍
> 2. 和 AI 的写法对比输出
> 3. 用 `audio_io.null_test()` 看差异

## 相关

- [[Python 优先的 DSP 学习路径]] — 这份资料是那条路径的配套读物
- [[FFT 与 STFT]]
- [[混叠 aliasing]]
- [[采样与量化]]
- [[延迟线 delay line]]
- [[2026-10-14 第一次验证：过零计数为什么错了]] — 书里第 5 章正好讲这个

> [!note] 待补充
> - 第 2 版（work in progress）是否值得跟
> - 哪些章节可以跳过（第 6 章 DCT 对插件开发用得少）
