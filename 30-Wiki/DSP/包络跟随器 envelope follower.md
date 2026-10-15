---
title: 包络跟随器 envelope follower
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 包络跟随器 envelope follower

> [!important] 一句话
> **包络跟随器把"音频波形"变成"随时间变化的电平"。**
> 它是压缩器、限制器、门限、自动增益、侧链检测的**共同前端**。

## 为什么这一页重要

你调压缩器时拧的 attack / release，**本质是在调包络跟随器的时间常数**。
理解它的数学，才能理解"为什么这个压缩器听起来这样"。

| 你熟悉的现象 | 工程原因 |
|---|---|
| "快 attack 削瞬态" | 包络上升快 → 增益衰减立刻生效 |
| "release 太快会抽吸" | 包络下降快 → 增益来回摆 |
| "这个压缩器表头跳得凶" | 检测器纹波大（快平滑） |
| "RMS 模式的压缩更柔和" | 慢平滑 → 输出趋于 mean\|x\| 而非峰值 |
| "低频老是触发压缩" | 检测器没加高通 |

---

## 一、两种基本结构

> [!note] 下面两段是**核心逻辑片段**（省略了成员变量声明）
> 完整可编译的实现见第八节。

### 峰值检测（peak）

```cpp
// 整流 + 一阶低通（env 是成员变量，跨调用保持状态）
float peakEnv (float x, float attackCoeff, float releaseCoeff)
{
    const float rect = std::fabs (x);
    const float c = (rect > env) ? attackCoeff : releaseCoeff;
    env += c * (rect - env);       // env 必须是成员变量
    return env;
}
// 成员: float env = 0.0f;
```

**attack / release 分开**：上升用快系数，下降用慢系数。

### RMS 检测

```cpp
// 平方 → 低通 → 开方
float rmsEnv (float x, float coeff)
{
    const float sq = x * x;
    meanSq += coeff * (sq - meanSq);   // meanSq 必须是成员变量
    return std::sqrt (meanSq);
}
// 成员: float meanSq = 0.0f;
```

> [!note] RMS 检测器的开销
> 每个采样多一次乘法和一次开方。
> **开方可以用近似或每隔 N 个采样算一次**（包络变化慢，不需要每采样）。

---

## 二、系数公式与实测验证

**时间常数 → 系数**：

$$c = 1 - e^{-1/(\tau \cdot f_s)}$$

其中 $\tau$ 是时间常数（秒），$f_s$ 是采样率。

**实测：往返一致性**（给定 τ 算系数，再从系数反算 τ）：

| 目标 τ (ms) | 系数 | 反算 τ (ms) | 误差 |
|---|---|---|---|
| 0.1 | 0.18806365 | 0.100000 | 4.2e-17 |
| 1.0 | 0.02061782 | 1.000000 | 2.6e-15 |
| 10.0 | 0.00208116 | 10.000000 | 2.7e-14 |
| 100.0 | 0.00020831 | 100.000000 | 2.1e-11 |
| 300.0 | 0.00006944 | 300.000000 | 2.1e-10 |

✅ 公式精确。注意 **τ 越大，浮点误差越大**（但仍可忽略）。

> [!tip] 用 τ 而不是"百分比时间"
> 有些文档说"到达 63% 的时间"，有些说"到达 90%"。
> **一定要确认是哪个定义**——它们差 2.3 倍。
> 本库统一用 **τ（63.2%）**。

---

## 三、指数逼近"永远不到达"

**实测**（τ = 10 ms）：

| 到达 | 样本数 | 时间 | 相对 τ |
|---|---|---|---|
| 50.0% | 332 | 6.92 ms | 0.69 τ |
| **63.2%** | 479 | **9.98 ms** | **1.00 τ** |
| 90.0% | 1105 | 23.02 ms | 2.30 τ |
| 99.0% | 2210 | 46.04 ms | 4.61 τ |
| **99.9%** | 3315 | 69.06 ms | **6.91 τ** |

> [!important] 这个性质的实际影响
> **指数逼近永远不到达目标值**，只是无限接近。
> - 线性斜坡有确定的完成时间
> - 指数逼近只有时间常数，剩余误差永远存在
>
> **对压缩器的意义**：
> release 设成 100ms，实际"听起来恢复"可能要 **700ms**（6.9τ）。
> 这就是为什么"标称 release"和"听感 release"经常对不上。

---

## 四、⚠️ 最反直觉的一条：peak 检测是参数选择，不是结构

> [!danger] 这一条颠覆直觉
> **同一个"整流 + 一阶低通"结构，只改系数，就能从 peak 检测变成均值检测。**

**实测**（1kHz 正弦，幅度 0.5，固定结构 `y += c*(|x| - y)`）：

| τ (ms) | 系数 | 稳态均值 | 稳态纹波 (pk-pk) | 纹波 (dB) | 性质 |
|---|---|---|---|---|---|
| **0.05** | 0.340759 | 0.317855 | **0.379834** | **7.905** | **peak 检测** |
| 0.50 | 0.040811 | 0.317855 | 0.066496 | 0.960 | 中间态 |
| 5.00 | 0.004158 | 0.317855 | 0.006730 | 0.092 | 均值检测 |
| **50.00** | 0.000417 | 0.317830 | **0.000698** | **0.010** | **均值检测** |

**理论值**：平滑足够慢时，输出 → $\text{mean}|x| = \frac{2}{\pi}A = 0.6366 \times 0.5 = 0.31831$

> [!important] 怎么读
> - τ = 0.05ms：输出在 **0.0001 ~ 0.5** 之间摆动 → **真的在跟随波形峰值**
> - τ = 50ms：纹波趋近 0，输出稳定在 **0.318** → 这是 **mean|x|，不是峰值**
>
> **"peak 检测"不是一个电路结构，而是"快 attack"这个参数选择。**
>
> ⚠️ 推论：**慢平滑的 peak 检测器，读数比 RMS 还低**
> （0.318 vs RMS 的 0.3536）。

---

## 五、peak vs RMS 的读数差异 = crest factor

**实测**：

| 信号 | peak 检测器 | RMS 检测器 | 差值 |
|---|---|---|---|
| 1kHz 正弦（峰值 0.5） | 0.497808（-6.06 dBFS） | 0.353552（-9.03 dBFS） | **+2.97 dB** |
| 白噪声（峰值 0.5） | 0.308081（-10.23 dBFS） | 0.105606（-19.53 dBFS） | **+9.30 dB** |

> [!tip] 差值就是 crest factor（峰均比）
> - 正弦：理论 crest factor = $20\log_{10}(\sqrt{2}) = 3.01$ dB ✅ 实测 2.97 dB
> - 白噪声：crest factor 大得多（实测 9.3 dB）
>
> **这就是为什么同一个压缩器设置，对鼓和对 pad 的效果完全不同**——
> 两者的 crest factor 差很多，检测器读到的"电平"关系就不一样。

---

## 六、RMS 的等效积分时间 ≈ 2τ

**实测**（白噪声输入，测方差比）：

| τ (ms) | 系数 α | 实测方差比 | 理论 α/(2-α) | 等效窗长 N_eq | 2·τ·fs |
|---|---|---|---|---|---|
| 1.0 | 0.020618 | 0.010260 | 0.010416 | 97.5 | 96.0 |
| 5.0 | 0.004158 | 0.002043 | 0.002083 | 489.6 | 480.0 |
| 10.0 | 0.002081 | 0.001026 | 0.001042 | 974.5 | 960.0 |
| 50.0 | 0.000417 | 0.000202 | 0.000208 | 4957.9 | 4800.0 |

$$N_{eq} \approx \frac{2-\alpha}{\alpha} \approx 2\tau f_s$$

> [!warning] 为什么"RMS window = 10ms"这个标称不可比
> **指数平均是无限记忆**（旧样本的影响永远存在，只是指数衰减）。
> **矩形滑动平均是有限记忆**（超过窗口的样本完全丢弃）。
> **双时间常数**又是第三种。
>
> 三者都叫"RMS window = 10ms"，**实际响应差别很大**。
> 对比不同压缩器时要注意这一点。

---

## 七、检测器前加高通（压缩器的标准做法）

**实测**（120 Hz 高通**只加在检测路径**）：

| 信号 | 无高通 | 120 Hz HP（**二阶**） | 差 |
|---|---|---|---|
| **kick 单独**（55 Hz） | -2.25 dBFS | -15.85 dBFS | **13.60 dB** |
| mid 单独（1 kHz） | -16.51 | -15.90 | -0.61 dB |
| kick + mid | -0.79 | -10.27 | 9.48 dB |

<!-- derived: 50-Playground/exp-004-dynamics-math/exp_envelope.py §7，2026-10-15 实测 -->

> [!warning] 上表的 13.60 dB 是**二阶** Butterworth 的结果——一阶只有一半
> 本库实测对比（55 Hz kick，同一检测器 τ_att=0.05 ms / τ_rel=100 ms）：
>
> | 高通实现 | 55 Hz 衰减 | 1 kHz 衰减 | kick+mid 检测电平 | 相对无高通 |
> |---|---|---|---|---|
> | 无 | — | — | -0.79 dBFS | — |
> | **一阶**（12 dB/oct 以下） | -7.99 dB | +0.45 dB | -6.97 dBFS | **6.18 dB** |
> | **二阶** Butterworth | **-13.60 dB** | +0.87 dB | -10.27 dBFS | **9.48 dB** |
>
> **一阶高通对 55 Hz 只有 8 dB 衰减，不足以解决"被 kick 触发"。**
> 压缩器一般用**二阶**（或更高）。§8 的代码给的是二阶 biquad。
> 如果你照 §8 之前的旧版一阶实现，只会得到约 6.2 dB，别以为自己做错了。

> [!important] 高通只加在**检测路径**，音频路径不变
> - kick 的检测电平掉 **13.6 dB**（二阶）→ 低频不再触发压缩
> - 中频几乎不变（-0.61 dB）
>
> **这是压缩器的标准做法**，也是"为什么我的压缩器总被贝斯触发"的解法。
>
> 注意：音频路径**不能**加这个高通——那会改变音色。

---

## 八、完整实现

```cpp
class EnvelopeFollower
{
public:
    enum class Mode { Peak, RMS };

    void prepare (double sampleRate, Mode m = Mode::Peak)
    {
        sr = sampleRate;
        mode = m;
        env = 0.0f;
        // 检测器前的高通（去低频触发），默认 120Hz
        setHighpass (120.0f);
    }

    void setAttack (double ms)  { attackCoeff  = coeffFor (ms); }
    void setRelease (double ms) { releaseCoeff = coeffFor (ms); }
    void setHighpass (double hz)
    {
        // 二阶 Butterworth 高通（RBJ），见 [[Biquad 滤波器]]
        // ⚠️ 一阶对 55Hz 只衰减 8dB，不够（见第七节）
        const double w0 = 2.0 * M_PI * hz / sr;
        const double cw = std::cos (w0);
        const double alpha = std::sin (w0) / (2.0 * 0.7071067811865476);   // Q = 1/√2
        const double a0 = 1.0 + alpha;

        hpB0 = (float) ((1.0 + cw) / 2.0 / a0);
        hpB1 = (float) (-(1.0 + cw) / a0);
        hpB2 = hpB0;
        hpA1 = (float) (-2.0 * cw / a0);
        hpA2 = (float) ((1.0 - alpha) / a0);
        resetHighpass();
    }

    void resetHighpass() noexcept { hx1 = hx2 = hy1 = hy2 = 0.0f; }

    float process (float x)
    {
        // 1. 检测路径高通（去掉低频）—— 二阶 Butterworth
        const float hp = hpB0 * x + hpB1 * hx1 + hpB2 * hx2
                       - hpA1 * hy1 - hpA2 * hy2;
        hx2 = hx1;  hx1 = x;
        // ⚠️ 状态必须防 denormal（见 [[denormal 数处理]]）
        hy2 = hy1;
        hy1 = (std::abs (hp) < 1.0e-30f) ? 0.0f : hp;

        if (mode == Mode::RMS)
        {
            meanSq += releaseCoeff * (hp * hp - meanSq);
            env = std::sqrt (meanSq);
        }
        else
        {
            const float rect = std::fabs (hp);
            const float c = (rect > env) ? attackCoeff : releaseCoeff;
            env += c * (rect - env);
        }
        return env;
    }

    float get() const noexcept { return env; }

private:
    double sr = 48000.0;
    Mode mode = Mode::Peak;
    float env = 0.0f, meanSq = 0.0f;
    float attackCoeff = 0.01f, releaseCoeff = 0.0001f;
    // 二阶高通（biquad）系数与状态
    float hpB0 = 1.0f, hpB1 = 0.0f, hpB2 = 0.0f, hpA1 = 0.0f, hpA2 = 0.0f;
    float hx1 = 0.0f, hx2 = 0.0f, hy1 = 0.0f, hy2 = 0.0f;

    float coeffFor (double ms) const
    {
        if (ms <= 0.0) return 1.0f;
        return (float) (1.0 - std::exp (-1.0 / (ms * 0.001 * sr)));
    }
};
```

> [!warning] 系数要在 prepare 里算
> `std::exp` 不便宜。**不要在音频线程每次调用重算**。
> 只在参数变化时重算（见 [[参数平滑 parameter smoothing]]）。

---

## 九、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **在音频线程重算 `exp()`** | 浪费 CPU | 检查系数是否在 prepare 里算 |
| 2 | **用线性斜坡冒充指数逼近** | 响应形状不对（听感不同） | 检查 `y += c*(x-y)` 还是 `y += step` |
| 3 | **peak 和 RMS 混用但只改一处** | 检测行为不一致 | 明确 mode |
| 4 | **检测器前没高通** | 低频老是触发 | 检查是否有 HP |
| 5 | **把高通也加到音频路径** | 音色被改（低频没了） | **只加在检测路径** |
| 6 | **release 系数不钳制** | 参数为 0 时除零或冻结 | 检查 `ms <= 0` 的处理 |
| 7 | **忘记 denormal 处理** | 静音时 CPU 飙升 | 见 [[denormal 数处理]] |
| 8 | **RMS 每采样开方** | 浪费 CPU | 可以每 N 采样算一次 |
| 9 | **attack > release**（反了） | 压缩器行为异常 | 通常 attack 应快于 release |

> [!danger] 第 5 条最常见也最容易被忽略
> AI 看到"加高通"就加到 `process()` 的入口——
> 那会**改变音频本身**，用户会发现"低频少了"。
> **高通必须只作用于检测分支。**

---

## 十、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 低频老是触发压缩 | 检测器没高通 | 检测路径加 HP |
| 加高通后低频没了 | 加到了音频路径 | 只加检测路径 |
| 静音时 CPU 飙升 | denormal | 加偏置或 FTZ |
| release 听起来比标称长 | 指数逼近永远不到达 | 记住 6.9τ 才到 99.9% |
| 表头跳得凶 | 平滑太慢（纹波大） | 增大 τ |
| 压缩器"不灵敏" | 平滑太快（变成均值检测） | 减小 τ |
| 不同信号效果差异大 | crest factor 不同 | 正常现象，理解它 |

---

## 十一、怎么验证

```python
import numpy as np
SR = 48000

def coeff_for(tau_ms, sr=SR):
    return 1.0 - np.exp(-1.0 / (tau_ms * 0.001 * sr))

# 1. 系数往返一致性
for tau_ms in [0.1, 1.0, 10.0, 100.0]:
    c = coeff_for(tau_ms)
    tau_back = -1.0 / (np.log(1.0 - c) * SR) * 1000
    assert abs(tau_back - tau_ms) < 1e-6 * max(tau_ms, 1)
print("✅ 系数公式精确")

# 2. 阶跃响应：到达 63.2% 的样本数应等于 tau*fs
tau_ms = 10.0; c = coeff_for(tau_ms)
env = 0.0; hits = []
for n in range(2000):
    env += c * (1.0 - env)
    if env >= 0.632 and not hits: hits.append(n)
print(f"✅ 63.2% 在 {hits[0]} 样本，理论 {tau_ms*0.001*SR:.0f}")

# 3. 快平滑 = peak 检测；慢平滑 = 均值检测
#    ⚠️ 必须看**一段时间内的最大值**，不能只看最后一个瞬时值
x = 0.5*np.sin(2*np.pi*1000*np.arange(SR)/SR)

def steady(x, tau_ms):
    c = coeff_for(tau_ms); env = 0.0; vals = []
    for v in x:
        env += c * (abs(v) - env)
        vals.append(env)
    return np.array(vals[-1000:])       # 最后 1000 样本 = 稳态

for tau_ms, label in [(0.05, "快（peak 检测）"), (50.0, "慢（均值检测）")]:
    st = steady(x, tau_ms)
    print(f"  τ={tau_ms:>5}ms {label}: 最大 {st.max():.4f} 最小 {st.min():.4f} "
          f"纹波 {20*np.log10(st.max()/(st.min()+1e-12)):.1f} dB")

# 期望：
#   快 → 最大值接近峰值 0.5，纹波大（~7.9 dB）
#   慢 → 稳定在 mean|x| = 2A/π = 0.3183，纹波接近 0
assert steady(x, 50.0).max() < 0.33, "慢平滑应趋近 mean|x|"
print(f"✅ mean|x| 理论值 = {2*0.5/np.pi:.4f}")
```

---

## 相关

- [[MOC - DSP]]
- [[动态处理的原理]] — 音乐视角（attack/release 的听感含义）
- [[动态范围处理]] — 压缩器的完整数学
- [[侧链与前瞻 lookahead]]
- [[软膝 soft knee]]
- [[denormal 数处理]]
- [[参数平滑 parameter smoothing]]
- [[exp-005 动态与浮点实测]] — 本页数据的来源

> [!note] 待补充
> - 双时间常数检测器（program-dependent）的数学
> - 检测器的 lookahead 缓冲
> - 立体声链接（link）的实现
> - 实测：不同检测器对鼓组的响应对比
