---
title: 参数平滑 parameter smoothing
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [gotcha, recipe, cpp]
created: 2026-10-14
updated: 2026-10-14
---

# 参数平滑 parameter smoothing

> [!note] 一句话
> 用户拧旋钮或宿主跑自动化时，参数值是**跳变**的。
> 直接把这个跳变喂给 DSP，就会听到"咔哒"声——这叫 **zipper noise（拉链噪声）**。

## 为什么会有 zipper noise

假设增益参数从 0.1 瞬间变成 0.9：

```cpp
// ❌ 错误
float gain = *gainParam;          // 某一瞬间从 0.1 → 0.9
out[i] = in[i] * gain;
```

信号幅度在**一个采样点内**跳了 9 倍。这个不连续在频域上是宽带能量 → 听到"啪"的一声。

> [!important] 关键认识
> 问题不在"参数变了"，而在**变化发生得太快**。
> 人耳对**不连续**极度敏感（这正是瞬态能被听见的原因）。
> 平滑的本质是：**把阶跃变成斜坡，让变化速率低于听觉的敏感阈值。**

---

## 方法 1：一阶低通（最常用）

```cpp
class SmoothedValue
{
public:
    void reset (double sampleRate, double timeMs)
    {
        // 时间常数：达到目标值 ~63% 所需时间
        coeff = 1.0f - std::exp (-1.0f / (float)(sampleRate * timeMs * 0.001));
        current = target;
    }

    void setTarget (float t) { target = t; }

    float next()
    {
        current += (target - current) * coeff;   // 每 sample 靠近一点
        return current;
    }

private:
    float current = 0.0f, target = 0.0f, coeff = 0.01f;
};
```

**时间常数的选择**：

| 参数 | 建议平滑时间 | 理由 |
|---|---|---|
| 增益 | 10–20 ms | 更短会听到咔哒，更长会感觉"迟钝" |
| 滤波器截止频率 | 20–50 ms | 频率变化比幅度变化更容易被察觉 |
| Q 值 | 20–50 ms | |
| 声像 pan | 20–30 ms | 太短会"跳"，太长会"拖" |
| 混音干湿比 | 20–50 ms | |
| 开关 / 枚举 | **不平滑** | 切换滤波器类型本来就应该有变化 |
| 延迟时间 | 特殊处理 | 直接平滑会产生**音高变化**（多普勒效应），见下 |

> [!warning] 指数平滑的数学性质
> 一阶低通**永远不会精确到达**目标值，只是无限接近。
> 如果需要精确到达，用线性斜坡（方法 2）或加一个阈值判断。

---

## 方法 2：线性斜坡（linear ramp）

```cpp
// 在 block 开头计算，block 内线性插值
const float start = current;
const float step  = (target - start) / numSamples;

for (int i = 0; i < numSamples; ++i)
{
    current = start + step * (i + 1);
    out[i] = in[i] * current;
}
```

**优点**：精确到达、可预测、零额外状态。
**缺点**：斜率突变处仍有轻微不连续（二阶不连续），在极端情况下可闻。

> [!tip] 实践建议
> **大多数情况下用方法 2 就够了**，而且它比逐 sample 的指数平滑更省 CPU。
> 一阶低通更适合"需要连续追踪快速变化"的场景（如包络跟随器）。

---

## 方法 3：块级插值 + 系数插值（滤波器专用）

滤波器的**系数**平滑比增益平滑更微妙。**不要直接平滑系数**——那会导致滤波器不稳定或频响异常。

**正确做法**：

```cpp
// ❌ 错误：直接平滑 b0, b1, a1...
b0 = lerp (b0_old, b0_new, t);   // 中间状态的滤波器可能不稳定

// ✅ 正确：平滑"参数"（频率、Q），每个 block 重算系数
float freq = smoothedFreq.next();
auto coeffs = makeLowpass (sampleRate, freq, Q);
```

或者用**状态变量滤波器（SVF）**——它的系数和参数是近似线性的，可以直接平滑。

> [!warning] 常见错误
> 在 block 边界**一次性**更新滤波器系数，block 内保持不变。
> block size 大时（如 2048），频率扫频会听到"阶梯感"。
> **解法**：分小段更新（如每 32 samples 重算一次系数），或每 sample 更新。

---

## 特殊情况：延迟时间不能直接平滑

延迟时间从 100ms 变到 200ms，如果直接插值，延迟线读指针会**连续移动** → 产生**音高偏移**（多普勒效应）。

| 场景 | 处理方式 |
|---|---|
| 想要"磁带式"变调 | ✅ 直接平滑，多普勒效应是**特性** |
| 想要"干净"的延迟变化 | ❌ 不能平滑。用**交叉淡化**：旧延迟淡出，新延迟淡入 |
| 同步到节拍的延迟 | 变化通常发生在拍点，配合淡入淡出 |

见 [[延迟线 delay line]]。

---

## 怎么验证

**听觉测试**：
1. 播放持续音（正弦或 pad）
2. 用宿主自动化让参数**快速**来回扫
3. 如果听到"沙沙"或"咔咔"的颗粒感 → 平滑不够

**数值测试**（更可靠）：
```cpp
// 喂直流信号 1.0，突然改参数，看输出是否有跳变
// 输出的一阶差分最大值应该小于某个阈值
```

> [!tip] 用你的耳朵，但要用工具确认
> 你能听出 zipper noise 是优势。但**把"我听到了"变成"差分超过 X"** 才能写成自动化测试，
> 才能防止以后改代码时重新引入。这正是 [[AI 生成音频测试]] 该做的事。

---

## 相关

- [[实时音频线程契约]] — 为什么参数传递要无锁
- [[Biquad 滤波器]]
- [[状态变量滤波器 SVF]]
- [[延迟线 delay line]]
- [[包络跟随器 envelope follower]]

> [!note] 待补充
> - 不同平滑曲线的听感对比（指数 / 线性 / S 曲线）
> - 自适应平滑：变化大时用更长的时间常数
> - CLAP / VST3 的参数调制（per-sample modulation）如何改变这一套做法
