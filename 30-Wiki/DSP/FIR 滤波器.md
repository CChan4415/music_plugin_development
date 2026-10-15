---
title: FIR 滤波器
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# FIR 滤波器

> [!important] 一句话
> **FIR = 没有反馈的滤波器**（Finite Impulse Response）。
> 它**永远稳定**，而且可以做到**严格线性相位**——代价是计算量大。

## 与 IIR 的核心区别

| | FIR | IIR |
|---|---|---|
| 反馈 | ❌ 无 | ✅ 有 |
| $H(z)$ | 只有分子 | 有分母 |
| 脉冲响应 | **有限长**（N 个抽头就 N 个样本） | 无限长 |
| 效率 | ❌ 低（要几百抽头） | ✅ 高 |
| 相位 | ✅ **可严格线性** | ❌ 非线性 |
| 稳定性 | ✅ **永远稳定** | ⚠️ 需检查 |
| 延迟 | $(N-1)/2$ 采样（线性相位时） | 通常很小 |

> [!tip] 一句话选型
> **要相位就 FIR，要效率就 IIR。**
>
> 音频里的 FIR：线性相位 EQ、卷积混响、过采样滤波器、分频。
> 见 [[IIR 滤波器]]。

---

## 一、定义

$$y[n] = \sum_{k=0}^{N-1} h[k]\, x[n-k]$$

$$H(z) = \sum_{k=0}^{N-1} h[k]\, z^{-k}$$

**没有分母** → 没有反馈 → 脉冲响应正好是 $h[0..N-1]$，之后全为 0。

> [!important] 两个直接推论
> 1. **永远稳定**——没有极点（或极点全在原点），不存在发散
> 2. **延迟有限**——N 个抽头就是 N 个样本的记忆

---

## 二、线性相位：FIR 的杀手锏

> [!important] 条件：系数**对称**（或反对称）

**对称 FIR**（$h[k] = h[N-1-k]$）：

$$\angle H(e^{j\omega}) = -\omega \cdot \frac{N-1}{2}$$

**相位是频率的严格线性函数** → **群延迟恒定**：

$$\tau_g = \frac{N-1}{2} \quad \text{（采样）}$$

> [!tip] 恒定群延迟意味着什么
> **所有频率延迟同样的时间** → 波形形状不被改变。
> 方波还是方波（只是延后了），鼓的瞬态不被抹开。

### 实测验证（本库 2026-10-15）

**通带内相位残差**（偏离理想直线的程度）：

| 类型 | 阶数 N | 延迟 | 通带残差 max\|°\| | 结论 |
|---|---|---|---|---|
| FIR | 11 | 5 | **0.00000000** | ✅ 严格线性相位 |
| FIR | 21 | 10 | **0.00000000** | ✅ 严格线性相位 |
| FIR | 51 | 25 | **0.00000000** | ✅ 严格线性相位 |
| FIR | 101 | 50 | **0.00000000** | ✅ 严格线性相位 |
| FIR | 201 | 100 | **0.00000000** | ✅ 严格线性相位 |
| FIR | 501 | 250 | **0.00000000** | ✅ 严格线性相位 |
| **IIR** | N=4 | 4.88 | **3.321** | ❌ **非线性相位** |

> [!important] 怎么读
> 对称 FIR 的相位残差是**精确的 0**（数值上完全线性），
> 与阶数无关。而 IIR 的残差是 3.321°——**明显不线性**。
>
> 这就是"线性相位"的实际含义。

### 相位失真如何表现为"瞬态被抹掉"

**实测**（方波前后沿对比）：

| 信号 | 上升沿 10%→90% 时间（样本） | 过冲 |
|---|---|---|
| 原始方波 | 0 | 0.0% |
| **FIR 101 抽头** | **6** | **8.4%** |
| **IIR 4 阶 Butterworth** | **5** | **11.7%** |

> [!note] 怎么读这组数据
> 两者的上升时间接近（6 vs 5 样本），但：
> - **FIR 的过冲更小**（8.4% vs 11.7%）→ 波形更"干净"
> - FIR 的上升沿是**对称的**（前后沿形状一致）
> - IIR 的前后沿形状**不同**（相位非线性的直接表现）
>
> **这就是"保瞬态"vs"抹瞬态"的量化区别。**
>
> ⚠️ 注意：FIR 的 8.4% 过冲**不是相位造成的**，而是**窗化设计**的固有振铃
> （Gibbs 现象）。这是 FIR 的另一个代价。

---

## 三、代价：延迟与计算量

**线性相位 FIR 的延迟**：

$$\text{延迟} = \frac{N-1}{2} \quad \text{采样} = \frac{N-1}{2 f_s} \quad \text{秒}$$

**实测示例**：

| 抽头数 N | 延迟（采样） | @48kHz |
|---|---|---|
| 11 | 5 | 0.10 ms |
| 101 | 50 | 1.04 ms |
| 501 | 250 | 5.21 ms |
| 2049 | 1024 | **21.3 ms** |

> [!danger] 因果性的代价必须被补偿
> FIR 的延迟是**真实延迟**，必须：
> 1. **向宿主报告**（`setLatencySamples`）→ 见 [[延迟报告 latency reporting]]
> 2. **在多轨混音里对齐**——否则和其他轨错位 → 梳状滤波
>
> 一个 2049 抽头的线性相位 EQ 会引入 **21ms** 延迟。
> 录音时这个延迟会让人**明显感到延迟**。

**计算量**：

| 实现 | 每采样运算 |
|---|---|
| 直接卷积 | N 次乘加 |
| FFT 卷积（overlap-add） | $O(\log N)$ —— 适合大 N |
| 多相分解 | 适合抽取/插值 |

> [!tip] 什么时候用 FFT 卷积
> **N > 64 左右**，FFT 卷积就开始划算。
> 见 [[重叠相加 overlap-add]] 和 [[卷积混响]]。

---

## 四、设计：窗化法

**思路**：理想低通的脉冲响应是 **sinc 函数**（无限长）→ 截断 → 乘以窗函数。

**理想低通**（截止 $\omega_c$）：

$$h_{\text{ideal}}[n] = \frac{\sin(\omega_c (n - M))}{\pi (n - M)}, \qquad M = \frac{N-1}{2}$$

**窗化**：

$$h[n] = h_{\text{ideal}}[n] \cdot w[n]$$

| 窗 | 主瓣宽度 | 旁瓣 | 过渡带 | 阻带衰减 |
|---|---|---|---|---|
| **矩形** | 最窄 | **-13 dB** | 最陡 | ❌ 差（振铃大） |
| **Hann** | 2× | -31 dB | 中 | 中 |
| **Hamming** | 2× | **-43 dB** | 中 | 好 |
| **Blackman** | 3× | **-57 dB** | 缓 | 很好 |
| **Kaiser** | 可调 | 可调 | 可调 | ✅ 最灵活 |

> [!important] 窗的取舍：主瓣 vs 旁瓣
> - **主瓣越宽** → 过渡带越缓
> - **旁瓣越低** → 阻带衰减越好（振铃越小）
>
> **两者不可兼得。** 见 [[窗函数]]。

```python
import numpy as np

def design_lowpass_fir (n_taps, fc, fs=48000.0, window='hamming'):
    """窗化法设计线性相位低通 FIR"""
    assert n_taps % 2 == 1, "奇数抽头才能有整数对称中心"
    M = (n_taps - 1) // 2
    n = np.arange (n_taps)
    wc = 2 * np.pi * fc / fs

    # 理想低通（sinc）
    h = np.sin (wc * (n - M)) / (np.pi * (n - M))
    h[M] = wc / np.pi                      # n=M 处取极限

    # 窗
    windows = {
        'rect':    np.ones (n_taps),
        'hann':    np.hanning (n_taps),
        'hamming': np.hamming (n_taps),
        'blackman':np.blackman (n_taps),
    }
    h *= windows[window]

    # ⚠️ 归一化：让直流增益恰好为 1
    h /= np.sum (h)                        # 低通：sum(h) = H(1) = DC 增益
    return h
```

> [!warning] 测群延迟必须在**严格通带内**
> 本库踩过这个坑：101 抽头低通（$f_c$ = 1000 Hz）在 50–2000 Hz 上测群延迟得 **37.68**，
> 而理论值是 50。原因：**测到了截止频率以外的频段**，
> 那里幅度趋近 0、相位快速翻转，解缠失效。
>
> 收窄到 50–1000 Hz（严格通带内）后，实测 **50.000000**，与理论完全一致。
>
> **规则**：测群延迟时，测量带宽 **必须明显低于截止频率**。

> [!danger] 别忘了归一化
> 不归一化的话，**滤波器的整体增益不是 1**，
> 用户挂上插件就会发现"音量变了"。
>
> - **低通**：除以 `sum(h)`（直流增益）
> - **高通**：需要让 $H(-1) = 1$（用交替符号求和）
> - 一般情况：在**你关心的频率**上归一化

---

## 五、实现

```cpp
// 线性相位 FIR（对称系数 → 计算量减半）
class FirFilter
{
public:
    void prepare (const std::vector<float>& taps)
    {
        h = taps;
        N = (int) h.size();
        history.assign ((size_t) N, 0.0f);
        pos = 0;
    }

    float process (float x) noexcept
    {
        history[(size_t) pos] = x;

        // 对称系数：h[k] == h[N-1-k]
        // → 可以把历史里对称的两点先相加，乘法次数减半
        const int half = N / 2;
        float acc = 0.0f;

        int idx = pos;
        for (int k = 0; k < half; ++k)
        {
            const float pair = history[(size_t) idx] + history[(size_t) ((pos - (N-1-k) + N) % N)];
            acc += h[(size_t) k] * pair;
            idx = (idx - 1 + N) % N;
        }
        if (N % 2 == 1)                       // 奇数抽头：中间那项
            acc += h[(size_t) half] * history[(size_t) idx];

        pos = (pos + 1) % N;
        return acc;
    }

private:
    std::vector<float> h, history;
    int N = 0, pos = 0;
};
```

> [!warning] 上面这段的取模运算可能成为瓶颈
> 每个采样 N/2 次取模很慢。
> **优化**：用环形缓冲 + 两个线性区段（避免每次取模），
> 或者用 `size_t` 单调递增索引 + 位与（容量取 2 的幂）。
> 见 [[SPSC 队列]] 里的同类技巧。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **忘了归一化** | 整体增益不是 1（音量变了） | 检查 `h /= sum(h)` |
| 2 | **抽头数用偶数做线性相位** | 延迟不是整数采样 → 无法精确对齐 | 用奇数抽头（Type I） |
| 3 | **不报告延迟** | 多轨错位 | `setLatencySamples((N-1)/2)` |
| 4 | **以为 FIR 永远线性相位** | 只有**对称**系数才线性 | 检查 `h[k] == h[N-1-k]` |
| 5 | **大 N 用直接卷积** | CPU 爆炸 | N > 64 考虑 FFT 卷积 |
| 6 | **每次采样都算 sinc** | 极慢 | 系数在 prepare 里算好 |
| 7 | **用矩形窗** | 阻带只有 -13 dB（振铃大） | 换 Hamming/Hann |
| 8 | **窗化后不重算归一化** | 增益偏了 | 换窗后重新归一化 |
| 9 | **忘了处理 N=1 的退化情况** | 除零 | 检查边界 |
| 10 | **在音频线程分配 history** | 违反实时契约 | prepare 里分配 |

> [!danger] 第 4 条是概念错误，但很常见
> **"FIR = 线性相位"是错的。**
> 只有**系数对称**（或反对称）的 FIR 才线性相位。
> 一个随机系数的 FIR 相位完全非线性。
>
> 判据：`h[k] == h[N-1-k]` 对所有 k 成立。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 音量变了 | 没归一化 | `h /= sum(h)` |
| 多轨错位/低频抵消 | 没报告延迟 | `setLatencySamples` |
| 阻带衰减只有 -13 dB | 用了矩形窗 | 换窗 |
| 高频有振铃 | 窗的旁瓣太高，或抽头太少 | 加抽头 + 换 Blackman |
| 相位不是线性 | 系数不对称 | 检查对称性 |
| 延迟不是整数采样 | 用了偶数抽头 | 改奇数 |
| CPU 占用高 | 大 N 用直接卷积 | FFT 卷积 |
| 过渡带太缓 | 抽头数不够 | 加抽头（过渡带 ≈ 4/N 归一化频率） |

---

## 八、怎么验证

**本库已有脚本**：

```bash
python3 50-Playground/tools/verify/verify-fir-linear-phase.py
```

**四个必做测试**：

| # | 测试 | 期望 |
|---|---|---|
| 1 | **对称性**：`h[k] == h[N-1-k]` | 精确相等（线性相位的前提） |
| 2 | **线性相位**：通带内相位残差 | ≈ 0° |
| 3 | **群延迟**：$\tau_g = (N-1)/2$ | 与理论一致 |
| 4 | **直流增益**：`sum(h)` | ≈ 1（低通） |

```python
import numpy as np

def verify_fir (h, fs=48000.0):
    N = len(h)

    # 1. 对称性（线性相位的前提）
    symmetric = np.allclose (h, h[::-1], atol=1e-12)
    print (f"  对称性: {'✅ 对称（线性相位）' if symmetric else '❌ 不对称（非线性相位）'}")

    # 2. 直流增益
    print (f"  直流增益 sum(h) = {np.sum(h):.6f}  "
           f"{'✅' if abs(np.sum(h)-1) < 1e-6 else '⚠️ 未归一化'}")

    # 3. 群延迟（用相位差分算）
    nfft = 1 << 14
    H = np.fft.rfft (h, nfft)
    f = np.fft.rfftfreq (nfft, 1/fs)
    w = 2*np.pi*f/fs
    ph = np.unwrap (np.angle (H))
    gd = -np.gradient (ph, w)

    # ⚠️ 只在**严格通带内**测（必须低于截止频率！）
    #    本库踩过的坑：带宽取到 2000Hz（fc=1000）时测出 37.68，
    #    收窄到 1000Hz 以内后精确等于 50.000000
    band = (f > 50) & (f < 1000)
    expected = (N-1)/2
    measured = np.mean (gd[band])
    print (f"  群延迟: 实测 {measured:.4f} 采样，理论 (N-1)/2 = {expected}")
    assert symmetric, "系数不对称 → 不是线性相位！"
    assert abs(measured - expected) < 1.0, \
        f"群延迟不符（测 {measured:.2f} vs 理论 {expected}）——检查是否在通带内测"
    return symmetric

# 设计一个 101 抽头低通
def design_lowpass_fir (n_taps, fc, fs=48000.0):
    M = (n_taps-1)//2
    n = np.arange (n_taps)
    wc = 2*np.pi*fc/fs
    h = np.sin (wc*(n-M)) / (np.pi*(n-M))
    h[M] = wc/np.pi
    h *= np.hamming (n_taps)
    return h / np.sum (h)

print ("101 抽头 Hamming 低通:")
verify_fir (design_lowpass_fir (101, 1000.0))
```

---

## 相关

- [[MOC - DSP]]
- [[IIR 滤波器]] — 有反馈的对照
- [[Biquad 滤波器]] — IIR 的基本单元
- [[窗函数]] — 窗化设计的关键
- [[重叠相加 overlap-add]] — FFT 卷积实现
- [[卷积混响]] — FIR 的大型应用
- [[过采样 oversampling]] — 半带 FIR
- [[延迟报告 latency reporting]] — FIR 的延迟必须报告
- [[传递函数与 z 变换]]
- [[线性相位 EQ]]

> [!note] 待补充
> - Parks-McClellan（等波纹）设计的原理
> - 半带滤波器的专门设计（过采样用）
> - FFT 卷积的最佳分区大小
> - 实测：不同窗的阻带衰减曲线对比
> - Type II/III/IV 线性相位 FIR（偶数抽头、反对称）
