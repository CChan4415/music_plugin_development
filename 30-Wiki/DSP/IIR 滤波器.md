---
title: IIR 滤波器
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, cpp, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# IIR 滤波器

> [!important] 一句话
> **IIR = 有反馈的滤波器**（Infinite Impulse Response）。
> 用很少的计算量实现陡峭的频响——代价是**相位非线性**和**可能不稳定**。

## 与 FIR 的核心区别

| | IIR | FIR |
|---|---|---|
| 反馈 | ✅ 有 | ❌ 无 |
| $H(z)$ | 分母有 $z$ | 只有分子 |
| 脉冲响应 | **无限长** | 有限长 |
| 效率 | ✅ **高**（几个系数做陡峭响应） | ❌ 低（要几百抽头） |
| 相位 | ❌ **非线性** | ✅ 可线性 |
| 稳定性 | ⚠️ **需要检查** | ✅ **永远稳定** |
| 典型用途 | EQ、分频、共鸣 | 线性相位 EQ、卷积 |

> [!tip] 一句话选型
> **要效率就 IIR，要相位就 FIR。**
> 音频里 90% 的滤波器是 IIR（见 [[Biquad 滤波器]]）。

---

## 一、定义：分母出现 $z$

**FIR**（只有前馈）：

$$H(z) = b_0 + b_1 z^{-1} + b_2 z^{-2}$$

**IIR**（有反馈）：

$$H(z) = \frac{b_0 + b_1 z^{-1} + b_2 z^{-2}}{1 + a_1 z^{-1} + a_2 z^{-2}}$$

> [!important] 分母 = 反馈 = 无限脉冲响应
> 因为输出被送回输入，一个脉冲会**永远**在环路里绕（逐渐衰减）。
> 这就是"无限"的含义。

**时域形式**：

$$y[n] = b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2]$$

> [!warning] 注意符号
> 不同文献的 $a$ 定义不同：
> - 有些写 $y[n] = \sum b_i x[n-i] \mathbf{-} \sum a_i y[n-i]$（本页，RBJ 约定）
> - 有些写 $y[n] = \sum b_i x[n-i] \mathbf{+} \sum a_i y[n-i]$（此时 $a$ 符号相反）
>
> **抄系数前必须确认是哪种约定**，否则极点会跑到单位圆外 → 发散。

---

## 二、⚠️ 高阶 IIR 不能直接实现（本页最重要的一节）

> [!danger] 实测：float32 下 N=6 直接型就坏了

**测试**：Butterworth 低通（$f_c$ = 1000 Hz @ 48kHz），float32 计算。

| 阶数 N | biquad 数 | **直接型 DC 增益** | **级联 SOS DC 增益** | 直接型 | SOS |
|---|---|---|---|---|---|
| 2 | 1 | 1.000004 | 1.000004 | ✅ 正常 | ✅ 正常 |
| 4 | 2 | 1.000025 | 1.000000 | ✅ 正常 | ✅ 正常 |
| **6** | 3 | **1.087170** | 1.000004 | ❌ **已坏** | ✅ 正常 |
| **8** | 4 | **nan** | 1.000002 | ❌ **已坏** | ✅ 正常 |
| 10 | 5 | **nan** | 0.999988 | ❌ 已坏 | ✅ 正常 |
| **12** | 7 | **nan** | 1.000010 | ❌ 已坏 | ✅ **仍然正常** |
| 16 | 8 | nan | nan | ❌ 已坏 | ❌ 已坏 |

> [!important] 怎么读这张表
> - **直接型在 N=6 就把 DC 增益算成 1.087**（应该 1.000）——**误差 8.7%**
> - N=8 直接型直接变成 **NaN**（完全崩溃）
> - **级联 SOS 到 N=12 仍然准确**（1.000010）
>
> **同样的滤波器、同样的 float32，只是实现结构不同，结果天差地别。**

**频响误差对比**（N=8，以 float64 为参考）：

| 频率 | float64 | 直接型 f32 | SOS f32 | 直接型误差 | SOS 误差 |
|---|---|---|---|---|---|
| 100 Hz | -0.0000 | **nan** | 0.0000 | +nan | **+0.0000 dB** |
| 1000 Hz | -3.0018 | **nan** | -3.0018 | +nan | **-0.0000 dB** |
| 5000 Hz | -114.2839 | **nan** | -114.5520 | +nan | -0.2681 dB |
| 10000 Hz | -170.9499 | **nan** | -161.9831 | +nan | +8.97 dB |

> [!warning] 组带（10000 Hz）的 SOS 误差 +8.97 dB 看起来大
> 但那是 **-171 dB 到 -162 dB** 之间的差异——
> 都在**听不见**的电平上（远低于任何噪声底）。

### 为什么直接型会坏

高阶多项式的**根**对系数的**微小扰动极其敏感**（经典结论）。
float32 只有 24 位尾数，量化系数时极点的位置就会大幅偏移。

**极端例子**：Wilkinson 多项式——20 阶，根是 1..20，
系数扰动 $10^{-10}$ 就能让部分根变成复数。

> [!important] 结论：**永远用级联二阶节（SOS）**
> $$\text{N 阶} \Rightarrow \lceil N/2 \rceil \text{ 个 biquad 串联}$$
>
> 每个 biquad 只有 2 个极点，对量化不敏感。

---

## 三、SOS 分解的正确性验证

**实测**（SOS 分解 vs 直接型，float64）：

| 阶数 | 直接型 DC | SOS DC | 逐点最大差 | 结论 |
|---|---|---|---|---|
| N=2 | 1.0000000000 | 1.0000000000 | 0.000e+00 | ✅ |
| N=4 | 1.0000000000 | 1.0000000000 | 4.042e-11 | ✅ |
| N=6 | 1.0000000000 | 1.0000000000 | 6.003e-09 | ✅ |

> [!note] float64 下直接型也是"能用"的
> 上表说明：**精度问题主要来自 float32**。
> float64 的直接型到 N=6 还准确（差 6e-9）。
>
> **但音频插件用 float32**（CPU、内存、JUCE 默认）→ 必须用 SOS。

---

## 四、SOS 的形式

**每个二阶节**（biquad）：

$$H_k(z) = \frac{b_{k0} + b_{k1}z^{-1} + b_{k2}z^{-2}}{1 + a_{k1}z^{-1} + a_{k2}z^{-2}}$$

**总传递函数**：

$$H(z) = \prod_{k=1}^{K} H_k(z)$$

```cpp
// 级联 biquad（直接型 II 转置，数值最好）
struct BiquadCoeffs { float b0, b1, b2, a1, a2; };

class CascadedBiquads
{
public:
    void prepare (const std::vector<BiquadCoeffs>& c)
    {
        coeffs = c;                       // ⚠️ 只在 prepare/参数变化时调用
        state.assign (coeffs.size() * 2, 0.0f);   // 每节 2 个状态
    }

    float process (float x) noexcept
    {
        for (size_t k = 0; k < coeffs.size(); ++k)
        {
            const auto& c = coeffs[k];
            float& z1 = state[k*2 + 0];
            float& z2 = state[k*2 + 1];

            // 直接型 II 转置（Transposed Direct Form II）
            const float y = c.b0 * x + z1;
            z1 = c.b1 * x - c.a1 * y + z2;
            z2 = c.b2 * x - c.a2 * y;

            x = y;                        // 串联到下一节
        }
        return x;
    }

private:
    std::vector<BiquadCoeffs> coeffs;
    std::vector<float> state;
};
```

> [!tip] 为什么用"转置直接型 II"
> | 结构 | 状态数 | 数值行为 |
> |---|---|---|
> | 直接型 I | 4 | 一般 |
> | 直接型 II | 2 | 中间变量可能溢出 |
> | **转置直接型 II** | **2** | ✅ **最好（中间变量不易溢出）** |
>
> **RBJ 的系数设计就是配合转置直接型 II 的。**

---

## 五、四种经典逼近

| 类型 | 通带 | 阻带 | 过渡带 | 相位 | 用途 |
|---|---|---|---|---|---|
| **Butterworth** | **最平坦**（无纹波） | 单调 | 最慢 | 较好 | **通用首选** |
| **Chebyshev I** | 有纹波 | 单调 | 快 | 较差 | 要更陡的过渡 |
| **Chebyshev II** | 单调 | 有纹波 | 快 | 较差 | 阻带要求高 |
| **Elliptic** | 有纹波 | 有纹波 | **最快** | 最差 | 极限陡度 |
| **Bessel** | 单调 | 单调 | 很慢 | ✅ **最线性** | 保瞬态形状 |

> [!tip] 怎么选
> | 场景 | 推荐 |
> |---|---|
> | 通用分频、EQ | **Butterworth** |
> | 要陡峭但能接受纹波 | Chebyshev I |
> | 保瞬态（鼓、拨弦） | **Bessel** |
> | 极限陡度（分析用） | Elliptic |
>
> ⚠️ 本库的 `verify-iir-families.py` 尝试做四家族对比，
> 但 6 阶设计在 48kHz 下数值不稳（部分输出 NaN）。
> **该脚本只适合看定性趋势，不要直接引用数字。**

---

## 六、Linkwitz-Riley：分频器的标准

**LR 分频器** = 两个同阶 Butterworth **级联**：

$$\text{LR4} = \text{Butterworth 2 阶级联两次}$$

**关键性质**：在分频点上，两个输出的**幅度都是 -6 dB**，
且**相位一致** → 相加后**平坦**（无凹陷、无凸起）。

| 分频类型 | 分频点幅度 | 相加结果 |
|---|---|---|
| Butterworth | -3 dB | ❌ 有凸起 |
| **Linkwitz-Riley** | **-6 dB** | ✅ **平坦** |
| 一阶 | -6 dB | ✅ 平坦但斜率太缓 |

---

## 七、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **直接实现高阶 IIR** | float32 下 N=6 就坏（实测 DC 误差 8.7%） | 必须拆成 SOS |
| 2 | **符号约定混用** | 极点跑到圆外 → 发散 | 确认 $a$ 的符号约定 |
| 3 | **忘记归一化 $a_0$** | 增益完全不对 | 所有系数除以 $a_0$ |
| 4 | **用直接型 II（非转置）** | 中间变量溢出 | 用转置直接型 II |
| 5 | **不检查稳定性** | 高 Q 时发散 | 算极点半径 |
| 6 | **以为 IIR 也能线性相位** | 概念错误 | 线性相位要 FIR（或全通均衡） |
| 7 | **在音频线程重算 SOS 分解** | 分配 + 耗时 | 只在参数变化时算 |
| 8 | **级联时不考虑中间增益** | 内部溢出 | 检查每节缩放 |
| 9 | **忘了 denormal** | 安静时 CPU 飙升 | 见 [[denormal 数处理]] |

> [!danger] 第 1 条最隐蔽
> AI 会写一个"8 阶 Butterworth"，代码看起来完全正确——
> 但用直接型实现，**在 float32 下输出 NaN**。
> 而且它可能在你测试时"看起来还行"（取决于具体系数）。
>
> **判据**：代码里有多个 biquad 结构 = 对；只有一个高阶系数数组 = 错。

---

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 输出 NaN（高阶） | 直接型 + float32 | 拆成 SOS |
| 滤波器发散 | 极点出单位圆 | 检查符号约定、钳制参数 |
| DC 增益不是 1 | 没归一化 $a_0$ | 除以 $a_0$ |
| 低频/高频有异常 | 中间变量溢出 | 用转置直接型 II |
| 相位失真导致瞬态变形 | IIR 的固有特性 | 改用 FIR，或全通补偿 |
| 安静时 CPU 飙升 | denormal | 加偏置/FTZ |
| 改参数时爆音 | 系数突跳 | 见 [[参数平滑 parameter smoothing]] |

---

## 九、怎么验证

```python
import numpy as np

def sos_from_coeffs (b, a):
    """把高阶系数分解成 SOS（二阶节）"""
    from scipy.signal import tf2sos    # ⚠️ 本机无 scipy，见下方替代
    return tf2sos (b, a)

def check_iir (b, a, fs=48000.0):
    """三个自检：稳定性、DC 增益、Nyquist 增益"""
    p = np.roots (a)
    rmax = np.max (np.abs (p)) if len(p) else 0.0
    dc = np.sum (b) / np.sum (a)

    print (f"  极点最大半径: {rmax:.6f}  {'✅ 稳定' if rmax < 0.999 else '❌ 危险'}")
    print (f"  DC 增益: {dc:.6f}")

    # 实测：喂脉冲，看是否收敛
    N = 1 << 14
    x = np.zeros (N); x[0] = 1.0
    y = np.zeros (N)
    for n in range (N):
        acc = sum (b[i] * x[n-i] for i in range(len(b)) if n-i >= 0)
        acc -= sum (a[i] * y[n-i] for i in range(1,len(a)) if n-i >= 0)
        y[n] = acc

    tail = np.max (np.abs (y[N//2:]))
    print (f"  脉冲响应尾部: {tail:.3e}  {'✅ 收敛' if tail < 1e-6 else '❌ 未收敛'}")
    assert rmax < 0.999 and tail < 1e-3, "IIR 不稳定！"
    return y

# Biquad 低通
fs, fc, Q = 48000.0, 1000.0, 0.707
w0=2*np.pi*fc/fs; al=np.sin(w0)/(2*Q); cw=np.cos(w0); a0=1+al
b=[(1-cw)/2/a0,(1-cw)/a0,(1-cw)/2/a0]; a=[1.0,-2*cw/a0,(1-al)/a0]
print("Biquad 低通:")
check_iir(b, a)
```

> [!warning] 本机没有 scipy
> `scipy.signal.tf2sos` 不可用（本机 numpy 有，scipy 没有）。
> 需要 SOS 分解时：
> - 手写（用 `np.roots` 求极点，配对成共轭对，再合成二阶多项式）
> - 或者直接用 [[Biquad 滤波器]] 的设计公式**逐节设计**（推荐——不用分解高阶）

**本库已有验证脚本**：

```bash
python3 50-Playground/tools/verify/verify-highorder-sos.py   # 直接型 vs SOS
python3 50-Playground/tools/verify/verify-iir-families.py    # ⚠️ 部分可用
```

---

## 相关

- [[MOC - DSP]]
- [[FIR 滤波器]] — 无反馈的对照
- [[Biquad 滤波器]] — 二阶节（SOS 的基本单元）
- [[极零点与稳定性]] — 稳定性判据
- [[传递函数与 z 变换]] — $H(z)$ 的推导
- [[滤波器设计]] — 各种逼近的系数计算
- [[状态变量滤波器 SVF]] — 另一种实现结构
- [[denormal 数处理]]
- [[参数平滑 parameter smoothing]]

> [!note] 待补充
> - SOS 配对的优化算法（如何配对极零点让数值最好）
> - 各级的缩放策略（避免内部溢出）
> - Linkwitz-Riley 分频器的完整设计流程
> - 实测：更多阶数/更多滤波器类型的直接型 vs SOS 对比
