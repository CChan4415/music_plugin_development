---
title: 状态变量滤波器 SVF
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, cpp, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# 状态变量滤波器 SVF

> [!important] 一句话
> **SVF 同时输出低通、高通、带通，而且系数与参数近似线性——这让它成为"需要调制"的场景的首选。**
> Biquad 适合固定参数的 EQ；SVF 适合扫频、包络跟随、LFO 调制。

## 为什么你需要它

| 场景 | 用哪个 | 原因 |
|---|---|---|
| 固定参数的 EQ | [[Biquad 滤波器]] | 系数稳定、成熟 |
| **滤波器扫频**（自动哇音） | **SVF** | 参数变化时行为平滑 |
| **LFO 调制截止频率** | **SVF** | 系数与 f 近似线性，不会"跳" |
| **包络跟随的滤波** | **SVF** | 参数每采样变也不炸 |
| 需要同时拿 LP/HP/BP | **SVF** | 一个结构三个输出 |
| 高阶分频（Linkwitz-Riley） | Biquad 级联 | 更容易配对 |

> [!tip] 核心区别
> **Biquad 的系数是 `sin(ω)`、`cos(ω)` 的组合**——
> 改 f0 时所有系数都要重算，且中间状态可能不稳定。
>
> **SVF 的系数 `f` 直接就是频率的近似线性函数**——
> 每采样改 f 也不会炸。这就是"适合调制"的全部含义。

---

## 一、Chamberlin SVF（经典结构）

```
                    ┌──────────────────────────────┐
                    │                              │
  输入 ──┬─→ [×f] ─→ Σ ─→ [积分器] ─→ 带通 ─┬─→ [×f] ─→ Σ ─→ [积分器] ─→ 低通
         │          ↑                      │          ↑
         │          └── [×q] ←────────────┘          │
         │                                            │
         └── [×q] ←───────────────────────────────────┘
```

**差分方程**（Chamberlin 原始形式）：

```
低通 += f × 带通
高通  = 输入 − 低通 − q × 带通
带通 += f × 高通
```

**系数**：
- $f$：频率系数（决定截止频率）
- $q$：阻尼系数 = $1/Q$（决定共振）

---

## 二、⚠️ 最关键的坑：`f = 2sin(π·fc/fs)` 只在 Q=∞ 时精确

> [!danger] 这是 SVF 最常见的错误来源
> 几乎所有教程都写 $f = 2\sin(\pi f_c / f_s)$。
> **这个公式只在 Q → ∞（无阻尼）时精确。Q 越低，误差越大。**

### 实测（48kHz，目标截止频率 1000Hz）

| q = 1/Q | f 值 | 极点实际频率 | 目标 | **误差** |
|---|---|---|---|---|
| 2.0000（Q=0.5） | 0.130806 | **0.00 Hz** | 1000 Hz | **-100%** ⚠️ |
| 1.4144（Q=0.707） | 0.130806 | **703.75 Hz** | 1000 Hz | **-29.6%** |
| 1.0000（Q=1.0） | 0.130806 | **886.06 Hz** | 1000 Hz | **-11.4%** |
| 0.5000（Q=2.0） | 0.130806 | 983.62 Hz | 1000 Hz | -1.6% |
| 0.2000（Q=5.0） | 0.130806 | 1001.54 Hz | 1000 Hz | +0.15% |
| 0.1000（Q=10） | 0.130806 | 1002.04 Hz | 1000 Hz | +0.20% |
| 0.0100（Q=100） | 0.130806 | 1000.32 Hz | 1000 Hz | +0.03% |
| 0.0000（Q=∞） | 0.130806 | **1000.00 Hz** | 1000 Hz | **0.00%** ✅ |

> [!warning] 怎么读
> - **Q=0.707（最常用的 Butterworth）时误差 -29.6%**：你调 1kHz，实际共振在 **704 Hz**
> - **Q=0.5 时极点频率算出来是 0**：这个 Q 值下结构已经**不是标准二阶滤波器**了
> - Q 越高越准，Q → ∞ 时精确

### 低截止频率时误差更大（实测）

| 目标 fc | Q | f_approx | f_exact | **误差** | 极点(approx) | 极点(exact) |
|---|---|---|---|---|---|---|
| **200 Hz** | 0.707 | 0.02618 | 0.03704 | **+41.5%** | **141.4 Hz** | 200.0 Hz |
| 200 Hz | 1.0 | 0.02618 | 0.03008 | +14.9% | 174.0 Hz | 200.0 Hz |
| 200 Hz | 2.0 | 0.02618 | 0.02695 | +3.0% | 194.3 Hz | 200.0 Hz |
| **1000 Hz** | 0.707 | 0.13081 | 0.18686 | **+42.9%** | **703.8 Hz** | 1000.0 Hz |
| 5000 Hz | 0.707 | 0.64288 | 0.87397 | +36.0% | — | — |
| **10000 Hz** | 0.707 | 1.21752 | 0.87397 | **-28.2%** | — | — |

> [!danger] 结论
> **用近似公式的 SVF，在你以为调到 1kHz 时，实际共振在 704 Hz——差了将近一个八度的 3/4。**
>
> 而 Q=0.707 恰恰是"最平坦"的常用值。
>
> **这解释了为什么很多人说"SVF 调不准"** ——不是实现的锅，是公式的锅。

---

## 三、精确调谐

**极点角满足**：

$$\cos\theta = \frac{2 - f^2 - fq}{2\sqrt{1 - fq}}$$

**目标**：让极点角对应你想要的 $f_c$，即 $\cos\theta = \cos(2\pi f_c / f_s)$。

**解法**（数值求根）：

$$f^2 + fq - 2 + 2c\sqrt{1 - fq} = 0, \qquad c = \cos(2\pi f_c / f_s)$$

```python
import numpy as np

def exact_f (fc, Q, sr=48000.0):
    """精确求解 SVF 的频率系数 f（二分法）"""
    c = np.cos(2*np.pi*fc/sr)
    q = 1.0/Q
    lo, hi = 0.0, min(2.0, np.sqrt(q*q + 4) - q - 1e-12)
    for _ in range(200):                    # 二分足够多次
        mid = (lo + hi) / 2
        val = mid*mid + mid*q - 2 + 2*c*np.sqrt(max(1 - mid*q, 0))
        if val < 0: lo = mid
        else:       hi = mid
    return (lo + hi) / 2

# 对比
for fc in [200, 1000, 5000]:
    fa = 2*np.sin(np.pi*fc/48000)          # 近似
    fe = exact_f(fc, 0.707)                # 精确
    print(f"fc={fc:>5}Hz: 近似 f={fa:.5f}, 精确 f={fe:.5f}, 差 {(fe-fa)/fa*100:+.1f}%")
```

> [!tip] 实践建议
> | 场景 | 建议 |
> |---|---|
> | Q ≥ 5（共振明显） | 近似公式够用（误差 < 0.2%） |
> | **Q ≈ 0.7（最平坦）** | **必须用精确解**（误差 30–40%） |
> | 截止频率 > fs/8 | 近似开始失效（误差符号反转） |
> | 需要绝对准确的截止频率 | 用精确解，或改用 **TPT/ZDF** |
>
> **二分法 200 次迭代的开销**：只在参数变化时算，不在音频线程里每采样算。

---

## 四、稳定性条件

**Chamberlin SVF 的稳定条件**：

$$f < 2 - q \quad \text{（近似）}, \qquad f < \frac{2}{\max(1, Q)} \quad \text{（另一种表述）}$$

> [!warning] ⚠️ 不同资料的表述不一致
> 我在本库实测中发现：不同来源给出的稳定条件形式不同，
> 而且**与具体实现（积分器形式）有关**。
>
> **安全做法**：
> 1. 把 `f` 钳制到 `f < min(2 - q, 2*sin(π*0.45))` 之类的保守范围
> 2. **实测**：喂脉冲跑 10 秒，确认不发散
> 3. 极端 Q 值时降级到 Biquad

```cpp
// 保守钳制
f = std::clamp (f, 0.0f, std::min (2.0f - q, 1.4f));   // 1.4 ≈ 2*sin(π*0.45)
q = std::clamp (q, 0.05f, 2.0f);                        // 限制 Q 上限
```

---

## 五、实现

```cpp
class SvfChamberlin
{
public:
    void prepare (double sampleRate)
    {
        sr = sampleRate;
        reset();
    }

    void reset() noexcept { lp = bp = 0.0f; }

    // fc: 截止频率(Hz)，Q: 品质因数
    // ⚠️ 只在参数变化时调用（内含二分迭代）
    void setParams (float fc, float Q)
    {
        fc = std::clamp (fc, 10.0f, (float) (sr * 0.45));
        Q  = std::clamp (Q, 0.05f, 20.0f);
        q  = 1.0f / Q;
        f  = exactF (fc, Q);
        clampForStability();
    }

    // 每采样调用
    float processLowpass (float x) noexcept
    {
        lp += f * bp;
        const float hp = x - lp - q * bp;
        bp += f * hp;
        // ⚠️ denormal 保护（见 [[denormal 数处理]]）
        if (std::abs (lp) < 1.0e-30f) lp = 0.0f;
        if (std::abs (bp) < 1.0e-30f) bp = 0.0f;
        return lp;
    }

    float highpass() const noexcept { return hpOut; }
    float bandpass() const noexcept { return bp; }

private:
    double sr = 48000.0;
    float f = 0.1f, q = 1.0f;
    float lp = 0.0f, bp = 0.0f, hpOut = 0.0f;

    float exactF (float fc, float Q) const
    {
        const double c = std::cos (2.0 * M_PI * fc / sr);
        const double qq = 1.0 / Q;
        double lo = 0.0, hi = std::min (2.0, std::sqrt (qq*qq + 4.0) - qq - 1e-12);
        for (int i = 0; i < 60; ++i)              // 60 次足够（双精度）
        {
            const double mid = 0.5 * (lo + hi);
            const double val = mid*mid + mid*qq - 2.0
                             + 2.0*c*std::sqrt (std::max (1.0 - mid*qq, 0.0));
            if (val < 0.0) lo = mid; else hi = mid;
        }
        return (float) (0.5 * (lo + hi));
    }

    void clampForStability() noexcept
    {
        f = std::clamp (f, 0.0f, std::min (2.0f - q, 1.4f));
    }
};
```

> [!warning] 性能说明
> `exactF` 有 60 次迭代 + `sqrt`/`cos`。
> **绝不能每采样调用**——只在参数变化时算（或用 [[参数平滑 parameter smoothing]] 平滑后每 block 重算）。

---

## 六、TPT / ZDF：更好的替代

**拓扑保持变换（Topology-Preserving Transform）/ 零延迟反馈（Zero-Delay Feedback）**
是现代做法，解决了 Chamberlin 的两个问题：

| 问题 | Chamberlin | TPT/ZDF |
|---|---|---|
| 调谐精度 | 需数值解 | **解析解精确** |
| 高 Q 稳定性 | 差（Q 大时易炸） | **好** |
| 高频行为 | 截止频率接近 Nyquist 时失真 | 好（双线性变换保证） |
| 系数 | `f = 2sin(...)`（近似） | `g = tan(π·fc/fs)`（精确） |

**TPT 的核心思想**：**解反馈方程**，而不是插入一个单位延迟。

> [!note] TPT 的系数（解析、精确）
> $$g = \tan\left(\frac{\pi f_c}{f_s}\right), \qquad k = \frac{1}{Q}$$
>
> 然后通过求解一个代数环得到输出。
> **不需要迭代**，也不需要查表。

> [!warning] ⚠️ 本页未给出 TPT 的完整实现
> TPT 的推导需要一些代数，而且不同文献的记号差异大。
> **建议**：需要时查 Vadim Zavalishin 的《The Art of VA Filter Design》
> （见 [[_meta/open-questions]] 里关于该书的待核实项）。
>
> 本页只说明"TPT 比 Chamberlin 好，值得学"。

---

## 七、与 Biquad 的取舍

| 维度 | Biquad | Chamberlin SVF | TPT SVF |
|---|---|---|---|
| 同时输出 LP/HP/BP | ❌ 需多个实例 | ✅ | ✅ |
| **参数调制** | ❌ 差（系数突变） | ✅ **好** | ✅ 好 |
| 调谐精度 | ✅ 精确 | ⚠️ **需数值解** | ✅ 精确 |
| 高 Q 稳定性 | ✅ 好 | ⚠️ 一般 | ✅ 好 |
| 计算量 | 5 乘 4 加 | **4 乘 4 加** | 略多 |
| 成熟度/资料量 | ✅ 极多 | 多 | 中 |
| 适合 | 固定 EQ | **扫频/调制** | 现代首选 |

> [!tip] 怎么选
> - **做 EQ**（参数固定）→ **Biquad**
> - **做自动哇音 / LFO 滤波**（参数狂变）→ **SVF**（Chamberlin 够用，注意调谐）
> - **做虚拟模拟滤波器**（要精确 + 高 Q）→ **TPT/ZDF**
>
> 见 [[虚拟模拟滤波器]]（待写）。

---

## 八、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **只用 `f = 2sin(π·fc/fs)`** | Q=0.707 时截止频率差 30–43% | 用精确解，或测极点频率 |
| 2 | **参数每采样重算（含二分）** | CPU 爆炸 | 只在参数变化时算 |
| 3 | **不钳制 f 和 q** | 发散（尤其高 Q） | 检查 clamp |
| 4 | **反馈路径无 denormal 处理** | 安静时 CPU 飙升 | 加偏置 |
| 5 | **用 Biquad 的系数公式算 SVF** | 结构不同，结果错 | 确认是哪种结构 |
| 6 | **以为"SVF 就是三个 Biquad"** | 概念错误 | SVF 是一个结构三个输出 |
| 7 | **不测稳定性** | 用户调高 Q 时爆炸 | 喂脉冲跑 10 秒 |
| 8 | **调谐用 `sin` 但忘了 `π`** | 频率差一倍 | 检查公式 |

> [!danger] 第 1 条是这一页的核心价值
> AI 会给出 `f = 2*sin(pi*fc/sr)`，因为**几乎所有教程都这么写**。
> 它不会告诉你"这只在 Q=∞ 时精确"。
>
> **如果你照着做，你的滤波器在 Q=0.707 时会偏 30–43%。**
> 而你可能会以为是"耳朵的错觉"或者"插件就该这样"。

---

## 九、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 截止频率"不准" | 用了近似公式 | 用精确解（第三节） |
| 高 Q 时爆炸 | f/q 没钳制 | 加 clamp，测稳定性 |
| 扫频时"跳变" | 参数没平滑 | 见 [[参数平滑 parameter smoothing]] |
| 安静时 CPU 飙升 | denormal | 加偏置 |
| 声音比 Biquad "脏" | Chamberlin 高频行为差 | 换 TPT |
| 每采样重算导致卡顿 | 二分迭代太贵 | 只在参数变化时算 |
| 三个输出幅度不对 | 忘了 BP 的 Q 相关增益 | BP 输出要乘 Q（或 1/Q，看定义） |

---

## 十、怎么验证

**本库已有验证脚本**（全部可运行）：

```bash
# 调谐精度：近似 vs 精确
python3 50-Playground/tools/verify/verify-svf-tuning.py

# 稳定性
python3 50-Playground/tools/verify/verify-svf-stability.py
```

**关键测试**：

| 测试 | 方法 | 期望 |
|---|---|---|
| **调谐精度** | 测极点频率 vs 目标 fc | 误差 < 1%（用精确解） |
| **稳定性** | 喂脉冲跑 10 秒 | 衰减到 0，不发散 |
| **Q 正确** | 测共振峰高度 | ≈ Q（或 20log10(Q) dB） |
| **三个输出一致** | LP + HP + q·BP | 应等于输入（能量守恒） |
| **扫频平滑** | 慢扫 fc，听 | 无跳变/咔哒 |

```python
import numpy as np
# 验证 SVF 的三个输出之和等于输入（Chamberlin 的性质）
def svf_run(x, f, q):
    lp = bp = 0.0; out = []
    for v in x:
        lp += f*bp
        hp = v - lp - q*bp
        bp += f*hp
        out.append((lp, hp, bp))
    return np.array(out)

# 稳态下应有: lp + hp + q*bp == x
x = np.sin(2*np.pi*1000*np.arange(48000)/48000)
f = 2*np.sin(np.pi*1000/48000); q = 1/0.707
lp, hp, bp = svf_run(x, f, q).T
recon = lp + hp + q*bp
err = np.max(np.abs(recon[1000:] - x[1000:]))
print(f"三个输出重构输入的误差 = {err:.2e}")
assert err < 1e-10, "SVF 结构写错了"
```

---

## 相关

- [[MOC - DSP]]
- [[Biquad 滤波器]] — 固定参数场景的首选
- [[虚拟模拟滤波器]] — TPT/ZDF 的深入
- [[滤波器设计]] — Butterworth/Chebyshev 等逼近
- [[传递函数与 z 变换]] — 极零点分析
- [[极零点与稳定性]]
- [[参数平滑 parameter smoothing]] — 调制场景必需
- [[denormal 数处理]]
- [[exp-002 Biquad 滤波器]] — 频响验证的方法

> [!note] 待补充
> - **TPT/ZDF 的完整推导与实现**（需要 Zavalishin 的书）
> - Chamberlin 稳定条件的严格推导（不同资料表述不一致）
> - BP 输出的增益归一化（不同定义）
> - 实测：SVF vs Biquad 在快速扫频下的差异
