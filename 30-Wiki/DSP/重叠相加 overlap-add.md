---
title: 重叠相加 overlap-add
type: wiki
domain: dsp
status: solid
confidence: high
sources: ["[[Downey - Think DSP]]"]
tags: [math, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 重叠相加 overlap-add

> [!important] 一句话
> **把长信号切成重叠的块，逐块 FFT 处理，再把结果叠加回去。**
> 它是 FFT 卷积、STFT 处理、频谱编辑、卷积混响的**共同骨架**。

## 为什么需要 OLA

FFT 处理需要**整块**数据，但音频是**流式**的。两者矛盾，OLA 是标准解法。

| 直接 FFT 的问题 | OLA 的解法 |
|---|---|
| 需要等整段音频 | 分块处理，有延迟但可控 |
| 分块边界会出现突变 | **重叠** + 窗函数平滑过渡 |
| 每块处理完后怎么拼回去 | **相加**（因此叫 overlap-**add**） |

> [!note] 两个名字
> - **OLA**（overlap-add）：块之间**重叠**，结果**相加**
> - **WOLA**（weighted OLA）：先加窗再 OLA —— 实际用的都是这个
>
> 本页说的 OLA 都指 WOLA。

---

## 一、核心条件：COLA

> [!important] COLA = Constant Overlap-Add
> **所有重叠窗在任意时刻的和必须是常数。**

用公式表示：对所有权重，$\sum_k w[n - kH] = C$（常数），$H$ 是 hop size。

**实测验证**（N = 1024，hop = 512，50% 重叠）：

| 窗 | **COLA 误差** | 总覆盖增益 | 满足？ |
|---|---|---|---|
| 矩形 | 0.00e+00 | 2.0000 | ✅ |
| **Hann（周期性）** | **4.44e-16** | 1.0000 | ✅ |
| **Hann（对称，`np.hanning`）** | **9.74e-04** | 0.9990 | ❌ |
| Hamming | 8.96e-04 | 1.0791 | ❌（需特殊 hop） |

> [!danger] 对称 Hann 不满足 COLA —— 这是本库踩过的坑
> `np.hanning(N)` 的分母是 $N-1$（对称），而 OLA 需要分母是 $N$（周期性）。
>
> **两者只差 1**，波形看起来几乎一样，但：
> - 周期性 Hann：误差 **4.44e-16**（数值零）✅
> - 对称 Hann：误差 **9.74e-04** ❌
>
> **后果**：重建信号有周期性起伏（约 -60 dB 的调制）。
> 你可能会以为是"算法误差"，其实是窗选错了。
>
> ```python
> def hann_periodic(n):                     # ✅ OLA 用这个
>     return 0.5 - 0.5*np.cos(2*np.pi*np.arange(n)/n)
> # np.hanning(n)                           # ❌ 对称，不是给 OLA 的
> ```

> [!tip] 常见窗的 COLA 参数
> | 窗 | 满足 COLA 的 hop |
> |---|---|
> | 矩形 | 任意（常取 N） |
> | **Hann（周期）** | **N/2、N/4**（50%、75% 重叠） |
> | Hamming | 需要特殊设计（也叫 "Hann-ish"） |
> | Blackman | N/3 或更小 |
>
> **最常用：周期性 Hann + 50% 重叠（hop = N/2）。**

---

## 二、算法流程

```
1. 分析：把输入切成 N 长的块，块间距 H（hop）
2. 加窗：每块乘以分析窗 w[n]
3. FFT：转到频域
4. 处理：在频域修改（这是我们唯一"想做的事"）
5. IFFT：转回时域
6. 加窗：乘以合成窗 w[n]（如果 w 是"平方根窗"则跳过）
7. 叠加：把块加进输出缓冲的对应位置
8. 归一化：除以窗的重叠和（或用 COLA 常数）
```

> [!note] 分析窗 × 合成窗
> 如果分析和合成都用同一个窗，总效果是 $w^2$。
> 如果 $w$ 本身满足 $\sum w^2[n-kH] = C$，那也能重建（叫 **Princen-Bradley 条件**，
> MDCT 用的就是这个）。
>
> **最简单的做法**：分析窗 = 合成窗 = Hann，然后**除以归一化因子**。

---

## 三、实现

```python
import numpy as np

def hann_periodic (n):
    return 0.5 - 0.5 * np.cos (2*np.pi*np.arange(n) / n)

def ola_process (x, N, hop, process_spectrum, sr=48000.0):
    """
    用 OLA 对 x 做频域处理。

    process_spectrum: 接收 (频谱, 频率数组)，返回修改后的频谱
    """
    w = hann_periodic (N)                # ⚠️ 周期性！
    out = np.zeros (len(x) + N)
    norm = np.zeros (len(x) + N)
    freqs = np.fft.rfftfreq (N, 1/sr)

    for start in range (0, len(x) - N + 1, hop):
        seg = x[start:start+N] * w       # ① 分析窗

        spec = np.fft.rfft (seg)         # ② FFT
        spec = process_spectrum (spec, freqs)   # ③ 处理（唯一"想做的事"）
        seg_out = np.fft.irfft (spec, N) # ④ IFFT

        out[start:start+N]  += seg_out * w      # ⑤ 合成窗 + 叠加
        norm[start:start+N] += w * w            # ⑥ 归一化累积

    nz = norm > 1e-12
    out[nz] /= norm[nz]                  # ⑦ 归一化
    return out[:len(x)]
```

> [!warning] 归一化不能省
> 不做归一化的话，输出幅度是输入的 $\sum w^2$ 倍。
> 用 Hann + 50% 重叠时这个因子是 **0.75**（不是 1）。
>
> 逐样本归一化（上面的 `norm`）比用固定常数更安全——
> 它自动处理开头/结尾的不完整重叠。

**浮点误差检查**（实测）：

| 窗 | 重建最大误差 | 折合 dB |
|---|---|---|
| Hann（周期） | 1.110e-16 | **-312 dB** |
| Hann（对称） | 5.551e-17 | -318 dB |

> [!note] 为什么两者误差都这么小？
> 上面测的是**恒等处理**（`process_spectrum` 原样返回），
> 且用了逐样本归一化——归一化会抵消窗形状的差异。
>
> **COLA 的重要性在"重叠相加但不归一化"时显现**：
> 那时窗形状的起伏会直接变成输出上的周期性调制。
>
> 而**频域修改**（滤波、频谱编辑）会让 COLA 变得更关键——
> 因为所有块必须"无缝"拼接，否则修改会在边界产生咔哒声。

---

## 四、延迟：OLA 的代价

| 项 | 延迟 |
|---|---|
| 需要攒满一个块 | **N** 采样 |
| 前向 FFT 的固有延迟 | 0（块内） |
| **总延迟（典型）** | **N**（或 N + 块内处理延迟） |

> [!danger] 必须报告延迟
> OLA 引入 **N 个采样**（甚至更多）的延迟。
> 不报告的话，多轨会错位。见 [[延迟报告 latency reporting]]。
>
> **N = 2048 @ 48kHz = 42.7 ms** —— 这个延迟在录音时**明显可感**。
>
> 降低延迟的办法：减小 N（但频率分辨率下降）。

---

## 五、FFT 卷积（OLA 的经典应用）

**目标**：用 FFT 做长 FIR 卷积，比直接卷积快。

**原理**：时域卷积 = 频域相乘。

$$y = x * h \quad \Longleftrightarrow \quad Y = X \cdot H$$

**关键细节**：**必须零填充**，否则会发生**循环卷积**（时域混叠）。

$$N_{\text{FFT}} \ge N_x + N_h - 1$$

```python
def fft_convolve (x, h, nfft=None):
    """用 FFT 做卷积（等价于 np.convolve）"""
    if nfft is None:
        nfft = 1 << int (np.ceil (np.log2 (len(x) + len(h) - 1)))

    # ⚠️ 必须零填充到 nfft >= len(x)+len(h)-1
    X = np.fft.rfft (x, nfft)
    H = np.fft.rfft (h, nfft)
    y = np.fft.irfft (X * H, nfft)

    return y[:len(x) + len(h) - 1]        # 只取有效长度

# 验证：必须和直接卷积一致
x = np.random.randn (1000)
h = np.random.randn (64)
y_fft = fft_convolve (x, h)
y_dir = np.convolve (x, h)
err = np.max (np.abs (y_fft - y_dir))
print (f"FFT 卷积 vs 直接卷积: 最大误差 {err:.3e}")
assert err < 1e-10
```

> [!danger] 忘了零填充会怎样
> 不做零填充（`nfft = len(x)`）时，FFT 算的是**循环卷积**——
> 卷积结果的尾部会**绕回来**污染开头。
>
> **症状**：输出开头有一段"不属于那里的"信号。
> 听起来像咔哒声或前几毫秒的失真。

**分段卷积的两种方式**：

| 方式 | 原理 | 适用 |
|---|---|---|
| **Overlap-Add** | 每块卷积后**相加**（尾部重叠） | 通用 |
| **Overlap-Save** | 每块**丢弃**被污染的部分 | 更省一次 FFT |

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **OLA 用 `np.hanning`（对称）** | 不满足 COLA（误差 9.7e-4） | 用周期性 Hann |
| 2 | **不做归一化** | 输出幅度是输入的 0.75 倍 | 检查 `norm` 累积 |
| 3 | **FFT 卷积不零填充** | 循环卷积污染开头 | `nfft >= Nx+Nh-1` |
| 4 | **忘了报告延迟** | 多轨错位 | `setLatencySamples(N)` |
| 5 | **每块重新分配缓冲区** | 违反实时契约 | prepare 里分配 |
| 6 | **hop 与窗不匹配** | COLA 不成立 | 检查 `hop = N/2` |
| 7 | **边界块处理不当** | 开头/结尾有咔哒 | 用逐样本归一化 |
| 8 | **在音频线程建 FFT 对象** | 分配 + 耗时 | prepare 里建 |
| 9 | **修改频谱后不做共轭对称** | `irfft` 输出实数但有警告 | 只改 rfft 的前半 |
| 10 | **以为 OLA 零延迟** | 概念错误 | 至少 N 采样延迟 |

> [!danger] 第 3 条最隐蔽
> 代码能跑、输出"听起来差不多"，但开头有轻微异常。
> 而且如果 `h` 比 `x` 短很多，污染范围小，**更难发现**。
>
> **判据**：和 `np.convolve` 对比，误差应 < 1e-10。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 输出音量不对 | 没归一化 | 累积 `norm` 并相除 |
| 有周期性起伏（~-60dB） | 用了对称 Hann | 用周期性 Hann |
| 卷积开头有异常 | 没零填充（循环卷积） | `nfft >= Nx+Nh-1` |
| 多轨错位 | 没报告延迟 | `setLatencySamples` |
| 块边界有咔哒 | COLA 不成立 / hop 不对 | 检查 `hop = N/2` |
| 开头结尾有咔哒 | 边界块未正确处理 | 逐样本归一化 |
| CPU 占用高 | 每块重新分配/建 FFT | prepare 里准备好 |
| 频谱修改后有噪声 | 破坏了共轭对称 | 只改 rfft 前半 |

---

## 八、怎么验证

**三个必做测试**：

| # | 测试 | 判据 |
|---|---|---|
| 1 | **COLA**：重叠窗之和是否为常数 | 误差 < 1e-12 |
| 2 | **恒等重建**：`process` 原样返回，输出 == 输入 | 误差 < -100 dB |
| 3 | **FFT 卷积 == 直接卷积** | 误差 < 1e-10 |

```python
import numpy as np

def hann_periodic (n):
    return 0.5 - 0.5*np.cos (2*np.pi*np.arange(n)/n)

def check_cola (w, hop, n_periods=4):
    """检验 COLA 条件"""
    N = len(w)
    total = np.zeros (N * n_periods)
    for start in range (0, N*n_periods - N + 1, hop):
        total[start:start+N] += w
    mid = total[N : (n_periods-1)*N]          # 跳过边界
    err = np.max (np.abs (mid - mid.mean()))
    return err, mid.mean()

N, hop = 1024, 512
for name, w in [('矩形', np.ones(N)),
                ('Hann(对称)', np.hanning(N)),
                ('Hann(周期)', hann_periodic(N)),
                ('Hamming', np.hamming(N))]:
    err, gain = check_cola (w, hop)
    ok = "✅" if err < 1e-12 else "❌"
    print (f"  {name:<12} COLA 误差 {err:.2e}  增益 {gain:.4f}  {ok}")

# 期望：矩形 0（增益2）、Hann(周期) 4.4e-16（增益1）、
#       Hann(对称) 9.7e-04 ❌、Hamming 9.0e-04 ❌
```

```python
# 恒等重建测试（最重要）
x = np.random.randn (48000) * 0.1
y = ola_process (x, 1024, 512, lambda spec, f: spec)   # 原样返回
core = slice (1024, -1024)                              # 跳过边界
err = np.max (np.abs (y[core] - x[core]))
print (f"恒等重建误差: {err:.3e} ({20*np.log10(err/np.max(np.abs(x))):.1f} dB)")
assert err < 1e-6, "OLA 重建有问题！"
```

---

## 相关

- [[MOC - DSP]]
- [[窗函数]] — COLA 与周期性窗
- [[FFT 与 STFT]] — OLA 是 STFT 的骨架
- [[卷积混响]] — OLA 的大型应用
- [[FIR 滤波器]] — FFT 卷积加速
- [[延迟报告 latency reporting]] — OLA 的延迟必须报告
- [[实时音频线程契约]] — 不能在音频线程分配
- [[10-Sources/books/Downey - Think DSP]] — 第 10 章（卷积）

> [!note] 待补充
> - Overlap-Save 的实现与对比（省一次 FFT）
> - 分区卷积（partitioned convolution）—— 长脉冲响应的实时处理
> - MDCT 与 Princen-Bradley 条件
> - 频谱修改的相位处理（相位声码器）
> - 实测：不同 hop size 对重建质量的影响
