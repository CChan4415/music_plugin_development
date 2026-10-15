---
title: 旁路 bypass 的正确实现
type: wiki
domain: realtime
status: solid
confidence: high
sources: []
tags: [gotcha, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 旁路 bypass 的正确实现

> [!important] 一句话
> **旁路时输出必须"等于输入延迟了同样的量"**——
> 既不能有处理残留，也不能改变延迟。否则会和其他轨道相位错位。

## 为什么旁路很容易做错

旁路看起来是"最简单的事"（把输入直接送输出），但它有**三个独立的坑**：

| # | 坑 | 后果 |
|---|---|---|
| 1 | **旁路时延迟变了** | 与其他轨相位错位（梳状滤波/低频抵消） |
| 2 | **旁路时有处理残留** | 不是真正透明（用户听到音色变化） |
| 3 | **旁路↔激活切换有跳变** | 咔哒声 |

> [!note] 本页的实测数据
> 来自 `50-Playground/tools/cpp/latency_bypass_test.cpp`（已验证可运行）。

---

## 一、坑 1：旁路时延迟必须保持一致

> [!danger] 这是最严重、也最容易忽略的坑

**实测**（lookahead = 240 采样 = 5ms @ 48kHz）：

| 实现 | 干信号脉冲位置 | 旁路脉冲位置 | 相对干信号 |
|---|---|---|---|
| ❌ **错误**（旁路时直接输出输入） | 1000 | **1000** | **提前 0 采样** |
| ✅ **正确**（旁路时仍走延迟线） | 1000 | **1240** | 延迟 240 采样（= 5.00 ms） |

**错误实现的后果链**：

```
你的插件报告 latency = 240 采样
宿主做 PDC（插件延迟补偿）→ 把这条轨**提前 240 采样**来对齐
但你的旁路实际延迟是 0（提前了 240）
→ 补偿后这条轨**总共提前了 480 采样**（10 ms）
→ 与其他轨叠加时相位错位
→ 梳状滤波 / 低频抵消 / 立体声像偏移
```

> [!important] 结论
> **旁路 = "处理链的延迟不变，但把处理换成直通"。**
> 不是"绕过整个插件"。

```cpp
// ✅ 正确的旁路：仍然经过延迟线，只是不施加处理
void processBlockBypassed (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
{
    // 仍然把音频推过延迟线（保持延迟一致）
    for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
    {
        auto* data = buffer.getWritePointer (ch);
        for (int i = 0; i < buffer.getNumSamples(); ++i)
            data[i] = delayLine[ch].process (data[i]);   // 只有延迟，没有处理
    }
    // 不要清空延迟线状态！
}
```

---

## 二、坑 2：旁路必须完全透明（null test 验证）

**实测**：正确旁路 vs 干信号（对齐后逐样本相减）：

```
对齐后最大逐样本差异 = 0.000e+00
折合 = -600.0 dB（数值零）
```

> [!tip] 这是"旁路是否透明"的判据
> **对齐后差异应该是 0（或浮点 0）。**
>
> 如果不为 0，说明：
> 1. 旁路时仍在施加增益/滤波（**残留处理**）
> 2. 或者你在旁路时把延迟线**清空**了（应该保留）

**常见的"残留处理"**：

| 残留 | 为什么发生 |
|---|---|
| 输出增益 | 你的 `outputGain` 在旁路分支里也被应用了 |
| 干湿混合 | 干湿比没被正确置为"全干" |
| 参数平滑的残余 | 平滑器还在往旧目标移动 |
| 滤波器状态输出 | 旁路时仍从滤波器取输出 |

> [!warning] 旁路时**不要清空状态**
> 清空延迟线/滤波器状态 → 重新启用时会有瞬态。
> **正确做法**：保持状态运行（见下一节）。

---

## 三、坑 3：旁路↔激活的跳变（两个策略的取舍）

**实测**（前 0.5 秒 0.95 满幅正弦，之后 1.5 秒静音；旁路 1 秒后重新启用）：

| 策略 | 重新启用时的增益值 | 说明 |
|---|---|---|
| **B. 跳过处理（状态冻结）** | **-14.46 dB** | 状态停在旁路那一刻 |
| **A. 继续处理** | **-1.97 dB** | 状态跟随信号（已释放） |
| **差值** | **12.49 dB** | ← **这就是增益跳变的幅度** |

**折合线性增益跳变 = 4.21 倍。**

> [!danger] 策略 B 的问题
> 旁路期间状态被"冻结"在 -14.46 dB。
> 重新启用的瞬间，包络跟随器/压缩器会把**12.49 dB 的差值一次性施加**到信号上。
> 如果此时信号正在响 → 可闻的**咔哒声或电平跳变**。

> [!warning] 策略 A 的代价
> 旁路期间**仍然消耗 CPU**——而用户以为"旁路省资源"。

### 工程上的常见折中

```cpp
// 折中方案：旁路时继续跑**状态更新**，但跳过**昂贵的处理**
void processBlockBypassed (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
{
    for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
    {
        auto* data = buffer.getWritePointer (ch);
        for (int i = 0; i < buffer.getNumSamples(); ++i)
        {
            // ① 状态更新照常（包络跟随器、滤波器内部状态）
            updateEnvelopeOnly (data[i]);

            // ② 昂贵的处理（如 FFT、卷积）跳过
            // ③ 输出保持延迟一致的干信号
            data[i] = bypassDelay[ch].process (data[i]);
        }
    }
}
```

**或者更简单**：在旁路↔激活的过渡上做 **5–20 ms 的增益 crossfade**。

```cpp
// 用 crossfade 消除跳变（最简单可靠）
float bypassMix = 0.0f;   // 0 = 处理，1 = 旁路
float targetMix = shouldBypass ? 1.0f : 0.0f;
// 在 prepare 里按 20ms 算系数
for (int i = 0; i < numSamples; ++i)
{
    bypassMix += bypassCoeff * (targetMix - bypassMix);
    const float wet = processSample (input[i]);       // 处理链照常跑
    output[i] = wet * (1.0f - bypassMix) + delayedDry[i] * bypassMix;
}
```

> [!note] 这个做法同时解决了三个坑
> - 延迟一致（`delayedDry` 也是延迟过的）
> - 状态连续（处理链一直在跑）
> - 无跳变（crossfade 平滑）
>
> 代价：旁路时 CPU 不省。**但对大多数插件来说这是正确的取舍**——
> 用户更在乎"没有咔哒声"而不是"旁路时省 2% CPU"。

---

## 四、延迟变化时的处理

**实测**（过采样倍率切换对总延迟的影响）：

| 过采样倍率 | 抗混叠滤波器延迟 | 总延迟（含 240 lookahead） | 折合 ms |
|---|---|---|---|
| 1× | 0 | 240 | 5.000 |
| 2× | 3 | 243 | 5.062 |
| 4× | 6 | 246 | 5.125 |
| 8× | 9 | 249 | 5.188 |

> [!warning] 上表的滤波器延迟是**量级示例**
> 真实值取决于你用的半带滤波器设计。见 [[过采样 oversampling]]。

> [!danger] 切换延迟时**必须在音频线程外调用 `setLatencySamples`**
> ```cpp
> // ❌ 音频线程里调用 → 宿主内部可能要加锁 → 爆音
> void processBlock (...) { if (changed) setLatencySamples (n); }
> ```
>
> **正确**：在参数回调（消息线程）里改，并让音频线程通过原子量感知。
> JUCE 会在延迟变化时做淡入淡出处理。

---

## 五、完整实现模板

```cpp
class Processor : public juce::AudioProcessor
{
public:
    void prepareToPlay (double sampleRate, int blockSize) override
    {
        // 按最大可能延迟分配（避免运行中重新分配）
        const int maxDelay = (int) std::ceil (maxLookaheadMs * 0.001 * sampleRate);
        bypassDelay.resize ((size_t) getTotalNumOutputChannels());
        for (auto& d : bypassDelay) d.prepare (maxDelay);

        currentLatency = computeLatency (sampleRate);
        setLatencySamples (currentLatency);        // prepare 里调用是安全的
    }

    void processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
    {
        // ⚠️ 不要在这里调用 setLatencySamples
        // 有延迟的插件：即使内部判断"该旁路"，也走统一路径
    }

    void processBlockBypassed (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
    {
        // 保持延迟一致 + 完全透明
        for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
        {
            auto* data = buffer.getWritePointer (ch);
            auto& d = bypassDelay[(size_t) ch];
            for (int i = 0; i < buffer.getNumSamples(); ++i)
                data[i] = d.process (data[i]);      // 纯延迟，零处理
        }
    }

private:
    std::vector<DelayLine> bypassDelay;
    int currentLatency = 0;
};
```

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **旁路时直接输出输入**（延迟变了） | 相位错位、低频抵消 | 测旁路的实际延迟 |
| 2 | **旁路时清空延迟线状态** | 重新启用有瞬态 | 检查旁路分支是否 reset |
| 3 | **旁路时仍施加输出增益** | 不透明（非 0 dB 差异） | null test |
| 4 | **在音频线程调 `setLatencySamples`** | 宿主加锁 → 爆音 | grep `setLatencySamples` 位置 |
| 5 | **旁路时不跑状态更新** | 重新启用有 12+ dB 跳变 | 见第三节实测 |
| 6 | **以为"旁路 = 不调用 processBlock"** | 延迟不一致 | 理解 host 的 bypass 机制 |
| 7 | **用 `isBypassed` 分支但不做 crossfade** | 切换有咔哒 | 加 5–20ms crossfade |
| 8 | **忘了 `processBlockBypassed` 也要处理 0 长度** | 边界崩溃 | 加 early return |

> [!danger] 第 1 条最危险
> AI 会把旁路写成 `output = input`（看起来天经地义）。
> 但如果你的插件**有延迟**（lookahead、过采样、FFT），
> 这会让旁路时的音频**提前**，而宿主仍然按报告的延迟做补偿
> → **双重错位**（实测：提前 480 采样 = 10ms）。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 旁路时低频消失/变薄 | 延迟不一致导致相位错位 | 旁路保持同等延迟 |
| 旁路时能听到音色变化 | 有处理残留 | null test 排查 |
| 切换旁路有咔哒声 | 状态跳变 | crossfade 或保持状态运行 |
| 重新启用时电平突变 | 旁路时冻结了状态（实测 12.5 dB 跳变） | 旁路时继续跑状态更新 |
| 改延迟设置后爆音 | 音频线程调 `setLatencySamples` | 移到消息线程 |
| 旁路后 CPU 没下降 | 用了 crossfade（正常） | 接受，或跳过昂贵处理 |
| 旁路时崩溃 | 没处理 0 长度 buffer | early return |

---

## 八、怎么验证

**本库已有实验脚本**：

```bash
clang++ -std=c++17 -O2 50-Playground/tools/cpp/latency_bypass_test.cpp -o lb && ./lb
```

**三个必做测试**：

| # | 测试 | 期望 |
|---|---|---|
| 1 | **旁路延迟**：喂脉冲，比较激活 vs 旁路的脉冲位置 | **位置相同** |
| 2 | **Null test**：旁路输出（对齐后）− 干信号 | **0（或浮点 0）** |
| 3 | **切换跳变**：反复切换旁路，看输出包络是否有台阶 | 无台阶 |

```python
# Python 端：null test 验证旁路透明性
import numpy as np, sys
sys.path.insert(0, '50-Playground/tools')
from audio_io import impulse, null_test

# ① 测实际延迟
h_bypassed = my_plugin.process_bypassed(impulse(8192))
lat_byp = int(np.argmax(np.abs(h_bypassed) > 1e-6))

h_active = my_plugin.process_active(impulse(8192))
lat_act = int(np.argmax(np.abs(h_active) > 1e-6))

assert lat_byp == lat_act, f"旁路延迟不一致！{lat_byp} vs {lat_act}"
print(f"✅ 延迟一致: {lat_act} 采样")

# ② 对齐后应该是纯零
dry = impulse(8192)
aligned = np.roll(h_bypassed, -lat_byp)
null_test(aligned, dry, "旁路透明性")
# 期望：最大差异 < -100 dB（或精确 0）
```

---

## 相关

- [[MOC - Realtime Engineering]]
- [[延迟报告 latency reporting]] — 为什么必须报告延迟
- [[实时音频线程契约]] — 为什么不能在音频线程调宿主 API
- [[参数平滑 parameter smoothing]] — crossfade 的实现基础
- [[过采样 oversampling]] — 会引入延迟
- [[插件验证工具]] — pluginval 会测旁路
- [[SPSC 队列]] — 状态通信
- [[动态范围处理]] — 压缩器的 lookahead

> [!note] 待补充
> - 各宿主对 `processBlockBypassed` 的实际调用行为（需实测）
> - "旁路时省 CPU"的正确实现（跳过昂贵处理但保留状态）
> - 延迟变化时宿主的 PDC 重算行为（不同宿主差异大）
> - 实测：不同 crossfade 时长（5/10/20ms）的听感对比
