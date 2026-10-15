---
title: 状态变量滤波器 SVF
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 状态变量滤波器 SVF

> [!important] 一句话
> **一次运算同时给出低通、带通、高通三个输出**，而且系数与参数近似线性——
> 这让它成为**被 LFO 调制**时的首选滤波器（Biquad 不适合调制）。
>
> 代价是：截止频率高时必须钳制，否则**发散**。

## 为什么这一页重要

| 场景 | 该用谁 | 为什么 |
|---|---|---|
| **EQ（参数固定或缓慢变化）** | Biquad | 系数公式精确，Q 定义标准 |
| **合成器滤波器（LFO 快速扫频）** | **SVF** | 系数与参数近似线性，无"阶梯感" |
| **需要同时拿 LP/BP/HP** | **SVF** | 一次运算三个输出，Biquad 要算三遍 |
| **需要陡峭滚降（>12 dB/oct）** | Biquad 级联 | SVF 单级也是二阶 |

> [!note] 你的经验对应
> 合成器上 cutoff + resonance 扫起来"很顺"的，大概率是 SVF 或 ladder（见 [[虚拟模拟滤波器]]）。

---

## 一、Chamberlin SVF 的差分方程

```
low  = low  + f * band          // 三个输出：low / band / high
high = x - low - q * band
band = band + f * high
```

$$f = 2\sin\!\left(\frac{\pi f_c}{f_s}\right), \qquad q = \frac{1}{Q}$$

### 精确传递函数（本页推导并实测验证）

把上面三行写成状态方程，消去中间变量：

$$H_{lp}(z) = \frac{f^2 z^{-1}}{D(z)},\quad
H_{bp}(z) = \frac{f(1-z^{-1})}{D(z)},\quad
H_{hp}(z) = \frac{(1-z^{-1})^2}{D(z)}$$

$$D(z) = 1 + a_1 z^{-1} + a_2 z^{-2},\qquad
a_1 = f^2 + fq - 2,\qquad a_2 = 1 - fq$$

**实测验证**（fc=1000 Hz，Q=1，脉冲响应 + 2^17 点 FFT，解析 vs 实测）：

| 频率 | LP | BP | HP |
|---|---|---|---|
| 1000 Hz | 1.00000 / 0.99989 | 1.00000 / 1.00002 | 1.00000 / 1.00014 |
| 20000 Hz | 0.00493 / 0.00493 | 0.07279 / 0.07279 | **1.07506 / 1.07506** |

**最大绝对偏差 1.51e−4** ✅ 解析式正确。

> [!warning] 注意 HP 在高频的增益**不是 1**
> HP 在 20 kHz 是 **1.07506**（+0.63 dB）。这是 Chamberlin 的固有误差
> （TPT 版本此处精确为 1.0000）。**"高通"要平坦到 Nyquist 就不能用 Chamberlin。**

---

## 二、稳定性条件（本页自己推导）

### 推导

取自由响应（x = 0），状态向量 $\mathbf{s}_n = [\text{low}_n,\ \text{band}_n]^T$：

$$\mathbf{s}_{n+1} = A\,\mathbf{s}_n,\quad
A = \begin{bmatrix} 1 & f \\ -f & 1 - f^2 - fq \end{bmatrix},\quad
\det(A) = 1 - fq,\quad \operatorname{tr}(A) = 2 - f^2 - fq$$

二阶实系统稳定 ⟺ $|\det| < 1$ 且 $|\operatorname{tr}| < 1 + \det$：

$$|\det| < 1 \iff 0 < fq < 2, \qquad
|\operatorname{tr}| < 1 + \det \iff f^2 + 2fq - 4 < 0
\iff \boxed{\,f < \sqrt{q^2 + 4} - q\,}$$

**这就是 Chamberlin 的稳定性边界**（$q = 1/Q$）。

### 实测验证（数值仿真 vs 闭式解）

| q = 1/Q | 闭式边界 | 仿真边界 | 偏差 |
|---|---|---|---|
| 0.250 | 1.76556 | 1.76555 | −1.8e−5 |
| 0.500 | 1.56155 | 1.56152 | −2.9e−5 |
| 1.000 | 1.23607 | 1.23603 | −4.1e−5 |
| 1.414 | 1.03528 | 1.03523 | −4.4e−5 |
| 2.000 | 0.82843 | 0.82839 | −4.2e−5 |

**完美吻合。** ✅

### 换算成实际截止频率

$$f_{\max} = \frac{\sqrt{1 + 4Q^2} - 1}{Q},
\qquad f_{c,\max} = \frac{f_s}{\pi}\arcsin\!\left(\frac{f_{\max}}{2}\right)$$

| Q | f_max | fc_max @48kHz | fc_max / fs |
|---|---|---|---|
| 0.5（临界阻尼） | 0.8284 | **6525 Hz** | 0.136 |
| 0.707（Butterworth） | 1.0352 | **8312 Hz** | 0.173 |
| 1.0 | 1.2361 | **10179 Hz** | 0.212 |
| 2.0 | 1.5616 | **13688 Hz** | 0.285 |
| 5.0 | 1.8100 | **17286 Hz** | 0.360 |
| 10.0 | 1.9025 | **19210 Hz** | 0.400 |

> [!danger] 最容易踩的边界：**Q 越低，最高可用频率越低**
> 常见说法是"f > 1（约 fs/6）开始出问题"，但那只是 Q≈0.7 的情形。
> **Q=0.5 时 fc 上限只有 6525 Hz**——你在 48 kHz 下把 cutoff 拧到 8 kHz，
> 滤波器就已经发散了。
>
> 而且这个方向的直觉是反的：**加大 Q 反而更安全**（因为 $\sqrt{q^2+4}-q$ 随 q 减小而增大）。

```cpp
// 关键：把 f 钳制在稳定边界内
q = std::max (q, 0.05f);
const float fMax = std::sqrt (q*q + 4.0f) - q;
const float fcMax = (float) (sr / M_PI) * std::asin (std::min (fMax * 0.5f, 1.0f));
cutoffHz = std::clamp (cutoffHz, 5.0f, fcMax * 0.98f);   // 留 2% 余量
f = 2.0f * std::sin ((float) M_PI * cutoffHz / (float) sr);
```

> [!warning] 别忘了 `std::min(fMax * 0.5f, 1.0f)` 保护 `asin`
> Q 很大时 $f_{\max} \to 2$，`asin` 的参数趋近 1；浮点误差让它超过 1 就返回 NaN
> → **整个滤波器变 NaN**。

---

## 三、为什么 SVF 比 Biquad 更适合调制

### 1. 系数与参数的线性度

| 滤波器 | 系数 | 调制时的行为 |
|---|---|---|
| **Chamberlin SVF** | $f = 2\sin(\pi f_c/f_s)$ | 低频段 $f \propto f_c$，近似线性 |
| **TPT SVF** | $g = \tan(\pi f_c/f_s)$ | 同上，且**全频段精确** |
| **Biquad（RBJ）** | $a_1 = -2\cos\omega/a_0$，$a_2 = (1-\alpha)/a_0$ | **两个系数都要变，且非线性** |

**实测**（LFO 逐样本扫频，测每样本的系数变化量）：

| fc 范围 | Chamberlin Δf | TPT Δg | Biquad Δa1 |
|---|---|---|---|
| 200–2000 Hz | 1.245e−5 | 6.388e−6 | 9.045e−6 |
| 500–5000 Hz | 2.973e−5 | 1.751e−5 | 3.978e−5 |
| 1000–8000 Hz | 3.929e−5 | 3.024e−5 | **7.320e−5** |

Biquad 的 $a_1$ 变化量最大——$\cos\omega$ 在高频段变化极快。
**系数跳变越大 → 瞬态不连续 → 可闻的"沙沙"声或爆音。**

### 2. 谐振频率的跟踪精度（Q=1，BP 输出峰值位置）

| fc 设定 | Chamberlin 实测峰 | 误差 | TPT 实测峰 | 误差 |
|---|---|---|---|---|
| 500 Hz | 508.5 | +1.70% | 500.1 | +0.01% |
| 1000 Hz | 1035.6 | +3.56% | 999.9 | −0.01% |
| 2000 Hz | 2158.1 | +7.90% | 2000.1 | +0.00% |
| 5000 Hz | 6552.1 | **+31.04%** | 5000.1 | +0.00% |
| 8000 Hz | 24000.0 | **+200%** | 8000.1 | +0.00% |

> [!important] Chamberlin 的调谐误差随频率急剧恶化，TPT 几乎完美
> Chamberlin 用 $f = 2\sin(\pi f_c/f_s)$ 是**前向欧拉积分**的近似，
> 只在低频准确。TPT 用 $g = \tan(\pi f_c/f_s)$ + 双线性变换，**全频段精确**。
>
> **选型建议**：cutoff 不超过约 fs/10 时 Chamberlin 够用；
> 要做"扫到 15 kHz"的滤波器，用 TPT。

---

## 四、TPT / ZDF 版本（更好）

**零延迟反馈（ZDF）**：不要"先算 low 再算 high"（那引入 1 个采样的延迟，正是误差来源），
而是**直接解出这一时刻的反馈方程**。

```cpp
class TptSVF
{
public:
    void prepare (double sampleRate) { sr = sampleRate; ic1eq = ic2eq = 0.0f; }

    void setParams (float cutoffHz, float q)
    {
        cutoffHz = std::clamp (cutoffHz, 5.0f, (float) sr * 0.49f);
        q = std::max (q, 0.05f);
        const float g = std::tan ((float) M_PI * cutoffHz / (float) sr);
        const float k = 1.0f / q;                    // k = 1/Q
        a1 = 1.0f / (1.0f + g * (g + k));            // 三个系数预先算好
        a2 = g * a1;  a3 = g * a2;  k_ = k;
    }

    float processLow  (float x) { tick (x); return v2; }
    float processBand (float x) { tick (x); return v1; }
    float processHigh (float x) { tick (x); return v0 - k_ * v1 - v2; }

private:
    void tick (float x)
    {
        v0 = x;  v3 = v0 - ic2eq;
        v1 = a1 * ic1eq + a2 * v3;
        v2 = ic2eq + a2 * ic1eq + a3 * v3;
        ic1eq = 2.0f * v1 - ic1eq;
        ic2eq = 2.0f * v2 - ic2eq;
    }
    double sr = 48000.0;
    float a1 = 0.0f, a2 = 0.0f, a3 = 0.0f, k_ = 1.0f;
    float ic1eq = 0.0f, ic2eq = 0.0f;
    float v0 = 0.0f, v1 = 0.0f, v2 = 0.0f, v3 = 0.0f;
};
```

> [!note] 关键增益精度对比（fc=1000 Hz，Q=1）
>
> | 指标 | Chamberlin | TPT | 理论 |
> |---|---|---|---|
> | LP @Nyquist | 0.00460 | 0.00000 | 0 |
> | **HP @Nyquist** | **1.0749** | **1.0000** | 1 |
> | BP 峰值频率 | 1035.6 Hz | 999.9 Hz | 1000 |
> | BP 带宽误差 | +7.3% | −0.41% | 0 |
>
> **TPT 每一条都更准**，代价是 `tan()` 比 `sin()` 贵一点。

---

## 五、与 Biquad 的取舍表

| 维度 | Biquad（RBJ） | Chamberlin SVF | TPT / ZDF SVF |
|---|---|---|---|
| **调谐精度** | 精确 | 低频准，高频差（+31% @5kHz） | **精确** |
| **调制表现** | 差（系数非线性，两个都变） | 好 | **最好** |
| **稳定性** | 稳（钳制参数即可） | **需钳制 f，Q 低时上限低** | 稳（无条件稳定） |
| **同时拿 LP/BP/HP** | ❌ 要算三遍 | ✅ 一次三个 | ✅ 一次三个 |
| **CPU** | 5 乘 4 加 | 4 乘 4 加 | 5 乘 6 加（略贵） |
| **系数公式** | 复杂（RBJ 一整套） | **极简（一行）** | 中等（`tan` + 三个乘） |
| **适合** | EQ、固定滤波 | 合成器、低保真 | **现代合成器滤波器** |

> [!note] 我的判断
> **写 EQ 用 Biquad，写合成器滤波器用 TPT SVF**，要"三输出"用 SVF。
> 判据不是"哪个更好"，而是**"你的参数会不会动"**。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **不钳制 f** | Q 低 + 高频 → **发散爆炸** | 检查是否有 `f < sqrt(q*q+4)-q` |
| 2 | **`asin` 参数没钳制到 ≤1** | Q 大时 NaN 污染整个信号链 | 检查 `std::min(..., 1.0f)` |
| 3 | **q 写成 Q** | 谐振完全不对（Q=5 时差 25 倍） | $q = 1/Q$，看 `f*q` 的量级 |
| 4 | **`f` 用 `2*sin(pi*fc/fs)` 却声称精确** | 高频调谐偏 +31% | 与 TPT 对照测 BP 峰值 |
| 5 | **在音频线程调 `tan()`/`sin()`** | 违反实时契约（慢 + 可能不一致） | 参数变化时才算，或每 block 算一次 |
| 6 | **三个输出用了不同的状态更新顺序** | 输出之间相位/幅度不匹配 | 三个 `processXxx` 必须共用同一次 `tick()` |
| 7 | **每 block 只更新一次参数** | LFO 扫频有"阶梯感" | 每 sample 或每 32 samples 更新 |
| 8 | **反馈路径没有 denormal 处理** | 安静时 CPU 飙升 | 见 [[denormal 数处理]] |
| 9 | **左右声道共用状态** | 串音、立体声异常 | 每声道独立实例 |
| 10 | **以为 SVF 的输出已经归一化** | HP 在高频是 1.075 而不是 1 | 见第二节的 HP 增益表 |

> [!danger] 第 1 条是最常见的"插件崩溃"
> AI 写的 SVF 几乎总是**没有稳定性钳制**——因为教科书里也很少写。
> 后果：用户在 48 kHz 下、Q=0.5 时把 cutoff 拧过 6.5 kHz，
> 输出立刻变成 NaN，然后**污染整个信号链**（NaN 会传播）。
>
> **验证方法**：把 cutoff 从 20 Hz 扫到 20 kHz，Q 从 0.5 扫到 20，
> 检查输出是否始终有限。这个测试应该自动化。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 输出爆炸/NaN | f 超稳定边界 | 钳制（见第二节公式） |
| 高 Q 时 NaN | `asin` 参数 > 1 | `std::min(fMax*0.5f, 1.0f)` |
| 谐振位置与设定不符 | Chamberlin 高频误差 | 换 TPT，或用精确反解 |
| LFO 扫频有"沙沙"声 | 系数每 block 才更新 | 提高更新率 |
| 扫频时爆音 | 参数跳变 | 见 [[参数平滑 parameter smoothing]] |
| 高通高频增益 > 1 | Chamberlin 固有误差 | 用 TPT |
| 低 Q 时更容易炸 | 稳定边界随 Q 降低而收紧 | 按 Q 动态算 fc 上限 |
| 安静时 CPU 飙升 / 立体声异常 | denormal / 共用状态 | 见 [[denormal 数处理]]；每声道独立实例 |

---

## 八、怎么验证

| 测试 | 方法 | 期望 |
|---|---|---|
| **稳定性边界** | 扫 f，看自由响应是否衰减 | 边界 = $\sqrt{q^2+4}-q$ |
| **三种输出的频响** | 脉冲响应 + FFT vs 解析式 | 偏差 < 1e−4（本页实测 1.51e−4） |
| **LP 直流增益 / HP 奈奎斯特增益** | 喂直流；看 f→fs/2 | LP=1.0；HP：TPT=1.0，Chamberlin≈1.075 |
| **调谐精度** | BP 峰值位置 vs 设定 fc | TPT 误差 < 0.01% |
| **极端参数扫描** | fc 20 Hz→20 kHz × Q 0.5→20 | 输出必须始终有限 |
| **无 denormal** | 看安静时 CPU | 不应升高 |

```python
import numpy as np
SR = 48000.0

def fc_max_for (Q, sr=SR):
    q = 1.0/Q
    return (sr/np.pi) * np.arcsin(min((np.sqrt(q*q+4.0) - q)*0.5, 1.0))

def chamberlin (x, fc, Q, sr=SR, clamp=True):
    if clamp: fc = min(max(fc, 5.0), fc_max_for(Q, sr) * 0.98)   # ✅ 钳制
    f = 2*np.sin(np.pi*fc/sr); q = 1.0/Q
    low = band = 0.0; lp = np.zeros(len(x))
    for n, inp in enumerate(x):
        low = low + f*band; high = inp - low - q*band
        band = band + f*high; lp[n] = low
    return lp

def free_response_stable (f, q, n=200000):
    low = 0.0; band = 1e-6
    for _ in range(n):
        low = low + f*band; band = band + f*(-low - q*band)
    return abs(low) + abs(band) < 1e-9

# 1) 稳定性边界必须等于 sqrt(q^2+4) - q
for Q in [0.5, 1.0, 2.0]:
    q = 1.0/Q; bound = np.sqrt(q*q + 4) - q
    assert free_response_stable (bound*0.9, q),     f"Q={Q}: 边界内应稳定"
    assert not free_response_stable (bound*1.1, q), f"Q={Q}: 边界外应发散"
    print(f"✅ Q={Q}: 边界 {bound:.5f} 实测吻合")

# 2) LP 直流增益必须为 1
imp = np.zeros(1 << 14); imp[0] = 1.0
assert abs(chamberlin(imp, 1000.0, 1.0).sum() - 1.0) < 1e-6
print("✅ LP 直流增益 = 1.0")

# 3) ⚠️ 极端参数扫描 —— 抓"没钳制"的 bug
for fc in [20, 1000, 6500, 8000, 20000]:
    for Q in [0.5, 1.0, 5.0]:
        assert np.all(np.isfinite(chamberlin(imp, fc, Q))), f"fc={fc} Q={Q}"
print("✅ 钳制后极端参数下无 NaN/Inf")
```

> [!danger] 这个测试会抓到"没钳制"的 bug（本库实测）
> 用 **`clamp=False`** 跑第 3 个测试，结果：
>
> | fc \ Q | 0.5 | 1.0 | 5.0 |
> |---|---|---|---|
> | 6500 Hz | ✅ | ✅ | ✅ |
> | **8000 Hz** | ❌ **NaN** | ✅ | ✅ |
> | **20000 Hz** | ❌ **NaN** | ❌ **NaN** | ❌ **NaN** |
>
> **注意 Q=0.5、fc=8000 那一格**：cutoff 只拧到 8 kHz 就炸了，
> 而 Q=1.0 和 Q=5.0 都没事——这正是"Q 越低越危险"的实证。
> 这个测试应该写进 `50-Playground/tools/` 的自动化检查里。

---

## 相关

- [[MOC - DSP]]
- [[Biquad 滤波器]] — 另一个二阶 IIR，EQ 的首选
- [[传递函数与 z 变换]] — 本页的 H(z) 推导基础
- [[极零点与稳定性]] — 稳定判据的来源
- [[参数平滑 parameter smoothing]] — 调制时的爆音
- [[虚拟模拟滤波器]] — Moog ladder 与 ZDF 的更深入内容
- [[denormal 数处理]] / [[IIR 滤波器]] / [[过采样 oversampling]]

> [!note] 待补充
> - Zavalishin《The Art of VA Filter Design》里 TPT 的完整推导
> - 非线性 SVF（反馈路径里加饱和）的实现与稳定性
> - 精确调谐：给定 fc 和 Q 反解 f 的闭式解
> - Chamberlin 原始文献（*Musical Applications of Microprocessors*, 1980）的具体页码
