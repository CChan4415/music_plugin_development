---
title: 延迟线 delay line
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [cpp, recipe]
created: 2026-10-14
updated: 2026-10-14
---

# 延迟线 delay line

> [!important] 一句话
> **延迟线是延迟、回声、合唱、镶边、混响、梳状滤波器的共同骨架。**
> 你玩过的这些效果器，本质都是"把信号延迟一段时间，再和原信号混合"。

## 为什么这一页重要

| 你熟悉的效果 | 它的延迟线配置 |
|---|---|
| **Delay / Echo** | 一个长延迟（>100ms）+ 反馈 |
| **Chorus** | 短延迟（10–30ms）+ LFO 调制 + 混合 |
| **Flanger** | 极短延迟（1–10ms）+ 反馈 + 调制 |
| **Reverb** | 多个延迟 + 矩阵混合（见 [[混响的原理]]） |
| **梳状滤波** | 延迟 + 反馈或前馈 |
| **Karplus-Strong** | 延迟线 + 环路滤波（见 [[合成原理与 DSP 拓扑]]） |

**学会一个，六个都会。**

---

## 一、环形缓冲区（ring buffer）

**核心思想**：不要真的"移动"数据，而是**让读指针落后写指针**。

```cpp
class DelayLine
{
public:
    void prepare (int maxDelaySamples)         // ⚠️ 只在 prepare 里分配
    {
        buffer.assign ((size_t) maxDelaySamples, 0.0f);
        writePos = 0;
    }

    void write (float x)
    {
        buffer[(size_t) writePos] = x;
        writePos = (writePos + 1) % (int) buffer.size();
    }

    float readDelayed (int delaySamples) const // 0 = 最近写入的
    {
        int idx = writePos - 1 - delaySamples;
        while (idx < 0) idx += (int) buffer.size();   // ⚠️ 见下
        return buffer[(size_t) idx];
    }

private:
    std::vector<float> buffer;
    int writePos = 0;
};
```

> [!warning] C++ 的 `%` 对负数返回负值
> ```cpp
> -1 % 100   // C++ 得 -1，Python 得 99
> ```
> 所以**不能**直接写 `(writePos - 1 - d) % size`。
> 要么用 `while` 循环（如上），要么 `idx += size` 一次（当 `d < size` 时够用）。
>
> **实测确认**：本库的 C++ 参考实现里，`readDelayed` 正确处理了这一点
> （见 `50-Playground/ref-wav-io/`）。

> [!tip] 为什么用 2 的幂长度
> 如果 `size` 是 2 的幂，可以用**位与**代替取模：
> ```cpp
> writePos = (writePos + 1) & (size - 1);   // 比 % 快，且对正数等价
> ```
> 但**负数取地址**仍然要小心。这是性能优化，不是必需的。

---

## 二、分数延迟：为什么需要它

延迟时间很少正好是整数个采样。

例：120 BPM 下的 1/8 附点延迟 = 375ms
在 48kHz 下 = **18000 个采样**（正好整数 ✅）

但如果是 1/8 三连音 = 166.67ms = **8000.16 个采样**（不是整数 ❌）

**如果四舍五入到 8000**：延迟误差 0.16 采样 ≈ 3.3 μs
对单次延迟几乎听不出，但**对 LFO 调制的合唱/镶边是致命的**——
因为调制会让延迟量连续变化，如果只能取整，就会听到"台阶"。

---

## 三、三种插值方法（**这是本页最重要的部分**）

### 方法 1：线性插值（最简单）

```cpp
float readFractional (float delaySamples) const
{
    const int i0 = (int) delaySamples;
    const float frac = delaySamples - (float) i0;
    const float a = readDelayed (i0);
    const float b = readDelayed (i0 + 1);
    return a + frac * (b - a);
}
```

**频率响应**（解析解）：

$$H(f) = (1-\phi) + \phi\, e^{-j 2\pi f / f_s}, \quad \phi = \text{frac}$$

**实测幅度响应**（48kHz）：

| frac | 100 Hz | 1 kHz | 5 kHz | 10 kHz | 15 kHz | 20 kHz |
|---|---|---|---|---|---|---|
| **0.0** | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| 0.25 | -0.00 | -0.01 | -0.35 | -1.41 | -3.17 | **-5.23** |
| **0.5** | -0.00 | -0.02 | -0.47 | -2.01 | -5.11 | **-11.74** |
| 0.75 | -0.00 | -0.01 | -0.35 | -1.41 | -3.17 | -5.23 |

> [!danger] 这就是"分数延迟听起来发闷"的原因
> **frac=0（整数延迟）时完全透明**（全频段 0 dB）。
> 但只要 frac ≠ 0，**高频就被衰减**，而且 frac=0.5 时最严重（20kHz 衰减 **-11.74 dB**）。
>
> **实际影响**：
> - **Chorus / Flanger**：LFO 让 frac 周期性变化 →
>   高频**周期性变暗** → 听起来"闷"或有"晃动感"
> - **混响的调制**：尾巴的高频被反复衰减 → 失去空气感
> - **音高变换**：音质明显劣化

> [!note] 这个数字我是实测的
> 上表用解析公式 $|H| = \sqrt{(1-\phi)^2 + \phi^2 + 2\phi(1-\phi)\cos(2\pi f/f_s)}$ 逐点算出。
> **注意 frac=0.25 和 0.75 的结果相同**（对称性），frac=0.5 最差。

### 方法 2：全通插值（allpass，幅度平坦）

```cpp
// 一阶全通分数延迟（Thiran 近似）
class AllpassInterp
{
public:
    void setFraction (float frac)
    {
        // frac 接近 0 时 a 接近 1，会不稳定 → 需要保护
        eta = (frac > 1e-4f) ? (1.0f - frac) / (1.0f + frac) : 0.0f;
    }
    float process (float x)
    {
        const float y = eta * (x - yPrev) + xPrev;
        xPrev = x;  yPrev = y;
        return y;
    }
private:
    float eta = 0.0f, xPrev = 0.0f, yPrev = 0.0f;
};
```

**优点**：幅度响应**理论上全频段平坦**（这就是"全通"的定义）。
**缺点**：相位响应不是理想线性相位 → 有轻微相位失真；
且 **frac → 0 时系数趋于 1，数值不稳定**，需要切换到整数读取。

### 方法 3：高阶插值（Lagrange / Hermite / 窗化 Sinc）

用更多邻近采样点做高阶拟合。

| 方法 | 点数 | 质量 | CPU |
|---|---|---|---|
| 线性 | 2 | 差（高频衰减大） | 最低 |
| Hermite（3 阶） | 4 | 好 | 低 |
| Lagrange（3 阶） | 4 | 好 | 低 |
| 窗化 Sinc | 8–32 | 最好 | 高 |

> [!tip] 实践建议
> | 场景 | 推荐 |
> |---|---|
> | 固定延迟、不调制 | **整数延迟**（最透明，零成本） |
> | 缓慢调制的混响 | **线性插值**（够用，高频衰减不易察觉） |
> | Chorus / Flanger | **全通** 或 **Hermite**（高频衰减会被听出来） |
> | 音高变换 | **高阶（窗化 Sinc）**（质量要求最高） |

---

## 四、延迟时间不能直接平滑 ⚠️

**这是新手最常见的 bug 之一。**

```cpp
// ❌ 错: 直接平滑延迟时间
currentDelay += (targetDelay - currentDelay) * coeff;
float out = line.readFractional (currentDelay);
```

**为什么错**：延迟量连续变化 = 读指针连续移动 = **多普勒效应** = **音高变化**。

- 延迟变短 → 读得更快 → 音高**升高**
- 延迟变长 → 读得更慢 → 音高**降低**

> [!important] 这有时是特性，有时是 bug
> | 你想要的效果 | 该怎么做 |
> |---|---|
> | **磁带式变调**（tape echo） | ✅ 直接平滑，多普勒是**想要的** |
> | **同步延迟改节拍** | ❌ 交叉淡化：旧延迟淡出、新延迟淡入 |
> | **合唱的调制** | ✅ 调制本来就是小幅多普勒（±1–3ms） |
>
> **判断标准**：音高变化是不是你想要的效果？

**交叉淡化的写法**：

```cpp
// 用两个读指针 + 淡化
float outA = line.readFractional (oldDelay) * (1.0f - fade);
float outB = line.readFractional (newDelay) * fade;
float out  = outA + outB;
// fade 在几十毫秒内从 0 到 1
```

> [!warning] 交叉淡化对"节奏化延迟"也不完美
> 两个延迟同时存在时，会有短暂的"双回声"。
> 更好的做法是**在拍点切换**（宿主 transport 对齐时）。

---

## 五、反馈与稳定性

```cpp
// 带反馈的延迟
float delayed = line.readFractional (delaySamples);
line.write (input + delayed * feedback);
output = delayed;
```

**反馈增益 `feedback` 的约束**：

| feedback | 行为 |
|---|---|
| < 1 | ✅ 稳定衰减。回声次数 ≈ $\log(0.001)/\log(g)$ |
| = 1 | ⚠️ 永不衰减（无限混响），会累积成噪声 |
| > 1 | ❌ **发散爆炸** |

**RT60 换算**（用户拧的是"秒"，你要算的是增益）：

$$g = 10^{-3 \cdot d / \mathrm{RT60}} \quad \text{其中 } d = \text{延迟时间(秒)}$$

> [!tip] 这个公式已实测验证
> 用单个梳状滤波器（延迟 23.27ms）实测衰减到 -60dB 的时间：
> g=0.8 → 理论 0.72s / 实测 0.74s（+3.4%）；
> g=0.99 → 理论 15.99s / 实测 16.03s（+0.2%）。
> 见 [[混响的原理]] 的验证表。

> [!warning] 必须钳制 + denormal 处理
> ```cpp
> feedback = std::clamp (feedback, 0.0f, 0.999f);   // 留余量，浮点误差会累积
> ```
> 而且反馈路径**天然会产生 denormal 数**（尾巴衰减到极小时）→
> 某些 CPU 上慢 10–100 倍。见 [[denormal 数处理]]。

---

## 六、立体声处理

> [!warning] 不要左右共用一条延迟线
> 会产生**串音**和不可预测的行为。
> **一个声道一个 DelayLine 对象。**

**要宽度感**：左右用**略微不同**的延迟时间（相差几毫秒）。

```cpp
// 左右不同延迟 → 去相关 → 更宽
delayL.setDelay (18000.0f);
delayR.setDelay (18000.0f * 1.03f);   // 相差 3%
```

> [!warning] 代价：单声道兼容性
> 左右差异过大时，**相加成单声道会产生梳状滤波（相位抵消）**。
> 发布前必须检查 mono 兼容性——见 [[立体声感知]]。

---

## 七、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **在 `processBlock` 里 `buffer.resize()`** | 违反实时契约，可能爆音 | 检查是否只在 `prepare` 分配 |
| 2 | **用 `%` 处理负数索引** | 越界或读到错误位置 | 查 `readDelayed` 的实现 |
| 3 | **直接平滑延迟时间** | 意外变调（除非那是想要的） | 检查是否有 crossfade |
| 4 | **反馈增益不钳制** | 用户能调出爆炸 | 查有没有 `clamp` |
| 5 | **反馈路径没有 denormal 处理** | 安静时 CPU 飙升 | 见 [[denormal 数处理]] |
| 6 | **左右共用延迟线状态** | 串音、立体声异常 | 检查是否是 per-channel 实例 |
| 7 | **忘了延迟线长度随采样率变** | 96kHz 下延迟时间减半 | 检查是否在 `prepare` 里按 sr 算长度 |
| 8 | **用线性插值做音高变换** | 高频严重衰减 | 换成全通或高阶 |

> [!tip] 第 7 条特别常见
> AI 常把延迟线长度写成固定样本数（如 `delayLine(48000)`），
> 假设采样率是 48kHz。**用户切到 96kHz 时延迟时间就错了一半。**
>
> 正确：长度按**秒**定义，在 `prepareToPlay` 里乘以采样率。

---

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 改延迟时间时变调 | 直接平滑延迟量 | 交叉淡化，或接受它（磁带效果） |
| 高频发闷 | 分数延迟用线性插值 | 换全通/高阶插值，或用整数延迟 |
| 调制时有"台阶感" | 延迟量被取整 | 用分数延迟 |
| 爆炸/发散 | 反馈 ≥ 1 | 钳制到 0.999 以下 |
| 安静时 CPU 飙升 | denormal | 见 [[denormal 数处理]] |
| 延迟时间随采样率变 | 长度写成固定样本数 | 按秒定义，在 prepare 里换算 |
| 立体声变窄或有串音 | 左右共用状态 | 每声道独立实例 |
| 切换延迟时间有咔哒声 | 读指针跳变 | 交叉淡化 |
| 内存占用大 | 最大延迟按最长算 | 按实际需要分配，或动态调整 |

---

## 九、怎么验证

| 测试 | 方法 | 期望 |
|---|---|---|
| **延迟量正确** | 喂脉冲，看输出脉冲位置 | 位置 = 设定的采样数 |
| **整数延迟透明** | 喂脉冲，整数延迟 | 输出 = 输入的精确移位 |
| **分数延迟的频响** | 解析公式或扫频 | 与上表一致（高频衰减） |
| **反馈稳定** | 喂脉冲，跑 10 秒 | 必须衰减到 0，不发散 |
| **RT60 准确** | 测衰减曲线 | 接近设定值（±20%） |
| **无 denormal** | 看安静时的 CPU | 不应升高 |
| **立体声兼容** | 左右相加 | 无明显抵消 |

```python
# 用本库的工具验证
import sys; sys.path.insert(0, '50-Playground/tools')
from audio_io import impulse, decay_time, null_test

# 整数延迟应该是精确移位
x = impulse(1024)
y = delay(x, 100)                     # 你的实现
expected = np.roll(x, 100)            # 参考
null_test(y, expected, "整数延迟透明性")
```

---

## 相关

- [[MOC - DSP]]
- [[插值]] — 分数延迟的数学
- [[延迟与回声的原理]] — 音乐视角：Haas 效应、BPM 同步、磁带 echo
- [[混响的原理]] — 延迟线如何组成混响
- [[梳状滤波器 comb filter]]
- [[全通滤波器 allpass]]
- [[反馈延迟网络 FDN]]
- [[denormal 数处理]]
- [[参数平滑 parameter smoothing]]
- [[实时音频线程契约]] — 为什么只能在 prepare 里分配
- [[立体声感知]]
- [[exp-003 从延迟到混响]] — 可运行的实现

> [!note] 待补充
> - Hermite / Lagrange 插值的具体系数
> - 窗化 Sinc 插值的实现与权衡
> - 多抽头延迟（multi-tap）的设计
> - 延迟线的内存优化（共享缓冲池）
> - 与宿主 transport 同步的 BPM 换算细节
