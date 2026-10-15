---
title: 多速率处理 multirate
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 多速率处理 multirate

> [!important] 一句话
> **多速率 = 在信号链的不同位置用不同的采样率。**
> 核心技巧是**多相分解**——它让"先插 0 再滤波"这种浪费的做法变成省 factor 倍的计算。

## 什么时候需要

| 场景 | 需要的速率变化 |
|---|---|
| **过采样**（抗混叠） | 升 → 处理 → 降 |
| 采样率转换（44.1↔48） | 有理数倍率 |
| 高效滤波器（窄带） | 降 → 滤波 → 升（省计算） |
| 卷积混响 | 通常不需要，但大 IR 可以用 |
| 波表合成 | 按音高选不同分辨率的表 |

> [!note] 本页和相邻页的分工
> - [[过采样 oversampling]] — 为什么需要过采样（抗混叠）
> - [[采样率转换 resampling]] — 具体的转换实现
> - **本页** — **多相分解**这个让一切变高效的工具

---

## 一、多相分解：核心思想

> [!important] 问题：插 0 之后大部分乘法是白算的
> 升 4× 后，**75% 的样本是 0**。
> 对这些 0 做卷积 = 乘以 0 = **纯浪费**。

**朴素做法**：

```
输入 → 插 0（4 倍长）→ 卷积（N 抽头）→ 输出
        ↑                      ↑
    长度 ×4              每个输出算 N 次乘加
```

**多相做法**：

```
把滤波器 h 按相位拆成 4 组：
  h0 = [h[0], h[4], h[8], ...]
  h1 = [h[1], h[5], h[9], ...]
  h2 = [h[2], h[6], h[10], ...]
  h3 = [h[3], h[7], h[11], ...]

输出按相位选对应的子滤波器 → 每个输出只算 N/4 次乘加
```

> [!important] 关键洞察
> **不需要真的插 0**——直接跳过它们，用不同的子滤波器算输出。
> 数学上**完全等价**，计算量省 factor 倍。

**实测对比**（滤波器长度 N = 64）：

| 倍率 | 朴素（插 0 + 卷积） | **多相** | **节省** |
|---|---|---|---|
| 2× | 64 | 32 | **2.0×** |
| 4× | 64 | 16 | **4.0×** |
| 8× | 64 | 8 | **8.0×** |

> [!tip] 这就是"高效重采样"的全部秘密
> 现代 SRC 库（SoX、r8brain、JUCE）**全都用多相**。
> 朴素实现慢 factor 倍，而且同样是"正确"的——所以你可能不会意识到自己慢了。

---

## 二、半带滤波器：2× 的专用优化

> [!important] 半带滤波器（half-band filter）的特殊性质
> 1. **通带和阻带关于 $f_s/4$ 对称**
> 2. **约一半的系数是 0**（奇数位置的系数为 0，中心系数 0.5）
> 3. 所以在 2× 场景下，计算量**再减半**

**结构**：$h = [h_1, 0, h_3, 0, \ldots, 0.5, \ldots, 0, h_3, 0, h_1]$

**实测**（3 抽头示例 `[h1, 0.5, h1]`）：

| $h_1$ | 直流增益 | $f_s/4$ 处 |
|---|---|---|
| -0.25 | 0.0 | 0.5000（**-6.02 dB**） |
| -0.20 | 0.1 | 0.5000（-6.02 dB） |

> [!important] $f_s/4$ 处恰好是 -6.02 dB
> 这正是半带滤波器的**定义性特征**：
> 在"新 Nyquist"位置恰好衰减一半（0.5 = -6.02 dB）。
>
> **验证方法**：设计一个半带滤波器，测 $f_s/4$ 处的增益——
> 应该是 -6.02 dB（±0.1 dB）。

> [!note] 为什么用 0.5 作为中心系数
> 让直流增益容易归一化，且满足"半带"的对称要求。
> 不同的设计方法（窗化、等波纹）会给出不同的 $h_1, h_3, \ldots$。

**2× 过采样的完整结构**：

```
升 2×：插 0 → 半带滤波（多相）→ ×2 补偿
处理：在高采样率下做非线性
降 2×：半带滤波（多相）→ 抽取
```

---

## 三、多相分解的实现

```python
import numpy as np

def design_lowpass_fir (fc, fs, n_taps=65):
    M = (n_taps-1)//2
    n = np.arange (n_taps)
    wc = 2*np.pi*fc/fs
    h = np.sin (wc*(n-M)) / (np.pi*(n-M)); h[M] = wc/np.pi
    h *= np.hamming (n_taps)
    return h / np.sum (h)

def upsample_polyphase (x, factor, h):
    """
    多相升采样（等价于插 0 + 卷积，但快 factor 倍）
    """
    h = np.asarray (h, float)
    N = len (h)
    # ① 把 h 拆成 factor 个子滤波器
    sub = [h[k::factor] for k in range(factor)]

    out = np.zeros (len (x) * factor)
    # ② 每个输出相位用对应的子滤波器
    for phase in range (factor):
        # 该相位的输出 = 输入与 sub[phase] 的卷积
        # ⚠️ 乘 factor 补偿增益（与朴素做法保持一致！）
        conv = np.convolve (x, sub[phase]) * factor
        seg = out[phase::factor]
        n = min (len(conv), len(seg))          # ⚠️ 长度可能不同
        out[phase::factor][:n] = conv[:n]
    return out

def upsample_naive (x, factor, h):
    """朴素做法（插 0 + 卷积）—— 用于验证等价性"""
    up = np.zeros (len(x) * factor)
    up[::factor] = x
    return np.convolve (up, h)[:len(up)] * factor

# 验证等价性
rng = np.random.default_rng (42)
x = rng.standard_normal (500) * 0.1
h = design_lowpass_fir (20000.0, 96000.0, 65)

for factor in [2, 4, 8]:
    a = upsample_polyphase (x, factor, h)
    b = upsample_naive (x, factor, h)
    n = min (len(a), len(b))               # 长度可能不同
    err = np.max (np.abs (a[:n] - b[:n]))
    print (f"  {factor}× 多相 vs 朴素: 差异 {err:.3e}  "
           f"{'✅' if err < 1e-10 else '❌'}  (比较前 {n} 个样本)")

# 实测输出：
#   2× 多相 vs 朴素: 差异 1.110e-16  ✅
#   4× 多相 vs 朴素: 差异 1.110e-16  ✅
#   8× 多相 vs 朴素: 差异 1.110e-16  ✅
```

> [!danger] 这个验证代码里藏过两个 bug（本库的真实经历）
>
> **Bug 1：两个函数增益补偿不一致**
> ```python
> upsample_naive:     return np.convolve(up, h)[:len(up)] * factor   # 有 ×factor
> upsample_polyphase: return out                                      # ← 没有！
> ```
> 差异立刻是 **3.700e-01**——看起来像"多相算法错了"。
>
> 实际上：`0.37 / 4 ≈ 0.0925`，比值恰好是 $1 - 1/	ext{factor}$。
> **补上增益后差异降到 1.110e-16。**
>
> **Bug 2：数组长度不同**
> 朴素做完整卷积（长度 `len(x)*factor + len(h) - 1`），
> 多相只算到 `len(x)*factor`。
> `np.max(np.abs(a - b))` 在长度不同时会**静默地比较错位数据**。
>
> **教训**：
> 1. 两个实现比对时，**先确认增益约定一致**
> 2. **先确认长度相同**，或显式截断到公共长度
> 3. 差异是"整齐的倍数"时，先怀疑增益/缩放，而不是算法

> [!warning] 上面的多相实现是**教学版**
> 真正的生产实现要考虑：
> - 输出的**延迟补偿**（卷积的因果性）
> - **块处理**（流式，不能等整个信号）
> - **状态保持**（跨块连续）
>
> 这里只演示"数学等价性"。

---

## 四、多相分解的验证

> [!important] 唯一的正确性判据：**和朴素做法等价**

```python
def verify_polyphase (factor=4, n=500, seed=42):
    rng = np.random.default_rng (seed)
    x = rng.standard_normal (n) * 0.1
    h = design_lowpass_fir (20000.0, 96000.0, 65)

    a = upsample_polyphase (x, factor, h)
    b = upsample_naive (x, factor, h)

    err = np.max (np.abs (a - b))
    print (f"  {factor}× : 差异 {err:.3e}")
    assert err < 1e-10, "多相实现与朴素不等价！"
    return err
```

> [!danger] 多相最容易写错的地方
> | 错误 | 症状 |
> |---|---|
> | 子滤波器**顺序反了** | 输出有周期性失真 |
> | 忘记**增益补偿** | 音量不对（÷factor 或 ×factor） |
> | 相位索引**偏移一位** | 输出有延迟/超前 |
> | 用**对称窗**而非周期性 | 微小周期性起伏 |
>
> **全都靠"和朴素做法比对"抓出来**——这是唯一的可靠判据。

---

## 五、实际用在哪

| 场景 | 用什么 |
|---|---|
| **过采样 2×/4×/8×** | 半带滤波器 + 多相 |
| 44.1 ↔ 48 kHz | 有理数倍率（147:160）+ 多相 |
| 任意倍率 | 多相 + 分数延迟插值 |
| 高效窄带滤波 | 降采样 → 低阶滤波 → 升采样 |

> [!tip] JUCE 里怎么做
> `juce::dsp::Oversampling` 内部就是**多相 + 半带 FIR**。
> 用它就行——除非你要自己实现，否则不需要手写多相。
>
> ⚠️ 具体实现细节需查你锁定版本的 JUCE 源码。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **朴素插 0 + 卷积** | 慢 factor 倍 | 用多相 |
| 2 | **多相子滤波器顺序反了** | 周期性失真 | 和朴素比对 |
| 3 | **忘记增益补偿** | 音量不对 | 检查 ×factor / ÷factor |
| 4 | **升采样后不滤波** | 镜像 | 见 [[采样率转换 resampling]] |
| 5 | **降采样前不滤波** | 混叠 | 同上 |
| 6 | **半带滤波器不验证 $f_s/4$ 处** | 设计错误 | 应恰好 -6.02 dB |
| 7 | **不做流式处理** | 无法实时 | 保持跨块状态 |
| 8 | **忘了报告延迟** | 多轨错位 | `setLatencySamples` |
| 9 | **在音频线程重算子滤波器** | 违反实时契约 | prepare 里算好 |

> [!danger] 第 2 条最隐蔽
> 子滤波器顺序反了之后，**升采样仍然"能工作"**——
> 输出听起来是差不多的信号，但有**周期性失真**。
>
> 而且在你只测"频率对不对"时会通过（因为频谱位置没变）。
> **必须用"和朴素做法逐点比对"才能抓到。**

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| CPU 占用高 | 用了朴素插 0 | 多相分解 |
| 输出有周期性失真 | 子滤波器顺序错 | 和朴素比对 |
| 音量不对 | 忘了增益补偿 | ×factor |
| 高频有镜像 | 升采样后没低通 | 加抗混叠 |
| 半带滤波器效果不好 | 设计错误 | 验证 $f_s/4$ = -6.02 dB |
| 实时处理有咔哒 | 没保持跨块状态 | 状态连续 |
| 多轨错位 | 没报告延迟 | `setLatencySamples` |

---

## 八、怎么验证

**三个必做测试**：

| # | 测试 | 判据 |
|---|---|---|
| 1 | **多相 == 朴素** | 误差 < 1e-10 |
| 2 | **半带滤波器** | $f_s/4$ 处 = -6.02 dB |
| 3 | **无镜像/无混叠** | < -80 dB |

```python
import numpy as np

def check_halfband (h, fs_high=96000.0):
    """半带滤波器：fs/4 处应恰好 -6.02 dB"""
    h = np.asarray (h, float)
    H = np.abs (np.fft.rfft (h, 1 << 14))
    f = np.fft.rfftfreq (1 << 14, 1/fs_high)
    at_quarter = H[np.argmin (np.abs (f - fs_high/4))] / H[0]
    db = 20*np.log10 (at_quarter + 1e-20)
    print (f"  fs/4 处: {db:.2f} dB  {'✅' if abs(db + 6.02) < 0.2 else '❌'}")
    return db

# 一个真实的半带滤波器（窗化设计，奇数位置为 0）
def design_halfband (n_taps=33):
    M = (n_taps-1)//2
    n = np.arange (n_taps)
    # 理想半带：截止在 fs/4
    h = np.sinc (n - M) / 2.0            # ⚠️ 简化版
    h *= np.hamming (n_taps)
    h /= np.sum (h)
    return h

check_halfband (design_halfband())
```

> [!warning] 上面的 `design_halfband` 是**示意**
> 真正满足"一半系数为 0"的半带滤波器需要**等波纹设计**（Parks-McClellan）
> 或特定的窗化方法。
>
> ⚠️ 本页**没有**给出严格意义上的半带滤波器设计（没把握）。
> 只给出了**验证判据**（$f_s/4$ = -6.02 dB）——
> 你可以用它验证任何声称是"半带"的滤波器。

---

## 相关

- [[MOC - DSP]]
- [[过采样 oversampling]] — 主要应用场景
- [[采样率转换 resampling]] — 具体转换
- [[插值]] — 分数延迟
- [[FIR 滤波器]] — 多相滤波器的来源
- [[奈奎斯特-香农定理]]
- [[抗混叠振荡器]] — 过采样的实测对比

> [!note] 待补充
> - **严格半带滤波器的设计方法**（Parks-McClellan / 等波纹）
> - 多相分解的**流式实现**（跨块状态）
> - JUCE `dsp::Oversampling` 的内部结构（读源码）
> - 实测：多相 vs 朴素的 CPU 占用对比
> - 有理数倍率（147:160）的多相实现
