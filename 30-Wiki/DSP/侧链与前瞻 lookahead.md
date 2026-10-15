---
title: 侧链与前瞻 lookahead
type: wiki
domain: dsp
status: solid
confidence: high
sources: []
tags: [math, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 侧链与前瞻 lookahead

> [!important] 一句话
> **侧链 = 用别的信号决定压缩量；前瞻 = 提前看到信号，好提前动手。**
> 前者改变"谁触发"，后者改变"什么时候触发"。

## 两个独立的概念

| 概念 | 改变什么 | 典型用途 |
|---|---|---|
| **侧链（sidechain）** | **谁**触发压缩 | 踢鼓触发贝斯闪避；去齿音 |
| **前瞻（lookahead）** | **什么时候**触发 | 限制器抓住瞬态；母带 |

> [!note] 它们经常一起出现，但**是两件事**
> 一个压缩器可以只有侧链、只有前瞻、或两者都有。
> 混在一起讲会导致理解混乱。

---

## 一、前瞻：为什么必须"提前看"

> [!important] 因果性的问题
> 检测器需要**时间**才能响应（attack 时间）。
> 但峰值来得**很快**——等检测器反应过来，峰值**已经输出了**。
>
> **结果：瞬态漏过压缩器。**

**实测**（本库验证，1 个采样宽的尖峰，peak = 0.9）：

| 前瞻 | 输出峰值 | 结论 |
|---|---|---|
| **0 ms** | **0.9000** | ❌ **完整漏掉** |
| **1 ms** | **0.4862** | ✅ 已压制 |
| 5 ms | 0.5163 | ✅ 已压制 |
| 10 ms | 0.5565 | ✅ 已压制 |
| 20 ms | 0.6466 | ✅（压制变弱） |

> [!important] 怎么读
> - **0 ms：输出峰值 = 输入峰值（0.9）→ 完全没压到**
> - **1 ms 起：峰值降到 0.49 左右 → 压制成功**
> - 前瞻越长，峰值反而略升？—— 因为检测器"提前"看到的时间更久，
>   但**延迟也更大**，峰值在延迟线上等待更久（细节见第三节）
>
> **关键结论：只要有哪怕 1 ms 的前瞻，瞬态压制就完全不同。**

**原理**：

```
无前瞻：
  输入峰值 → 检测器 → (attack 延迟) → 增益开始下降
  └──────── 但峰值已经输出了！────────┘

有前瞻：
  输入峰值 → 检测器 → 提前衰减
  输入峰值 → 延迟线(L) → 输出（此时增益已降好）✅
```

---

## 二、前瞻的代价：延迟

> [!danger] 前瞻 = **真实延迟**，必须报告

| 前瞻 | 延迟（采样 @48kHz） |
|---|---|
| 1 ms | 48 |
| 5 ms | 240 |
| 10 ms | 480 |
| 20 ms | 960 |

```cpp
void prepareToPlay (double sampleRate, int) override
{
    lookaheadSamples = (int) std::round (lookaheadMs * 0.001 * sampleRate);
    delayLine.resize (lookaheadSamples);
    setLatencySamples (lookaheadSamples);          // ⚠️ 必须报告
}
```

> [!danger] 不报告延迟的后果
> 宿主不会做补偿 → 这条轨**整体提前** lookahead 毫秒
> → 和其他轨相位错位 → **梳状滤波 / 低频抵消**
>
> 见 [[延迟报告 latency reporting]] 和 [[旁路 bypass 的正确实现]]。
>
> **实测**：1 个采样的延迟差就已经造成 **-17.7 dB** 的差异
> （见 [[Null Test 与 bit-exact 对比]]）。

> [!warning] 前瞻的延迟在**录音时**很明显
> 10 ms 的前瞻 = 乐手听到自己声音延后 10 ms。
> **演奏会明显感到不适**（>10ms 就很难弹了）。
>
> 所以：**限制器用前瞻，但要让用户知道代价**。

---

## 三、前瞻的两种实现

### 实现 A：音频延迟，检测器看原始信号

```
输入 ──┬─→ 延迟线(L) ──→ 乘增益 ──→ 输出
       └─→ 检测器 ──→ 增益计算
```

✅ 简单，检测器看到"未来"
⚠️ **检测器和音频路径不一致**（一个是原始，一个是延迟的）

### 实现 B：检测器延迟，音频直通

```
输入 ──┬─→ 检测器 → 延迟(L) → 增益计算 ──→ 乘
       └─→ ────────────────── 输出
```

⚠️ 这**不是**真正的"提前",只是把检测结果延后对齐。

> [!important] 用实现 A
> 只有 A 能真正做到"提前看到峰值"。
> B 只是补偿了检测器的处理延迟。

---

## 四、侧链

> [!important] 侧链 = 用**另一个信号**驱动检测器

```
主输入 ──→ 处理链 ──→ 输出
              ↑
侧链输入 ──→ 检测器 ──→ 增益
```

**常见用途**：

| 用途 | 谁触发 | 效果 |
|---|---|---|
| **闪避（ducking）** | 踢鼓触发贝斯 | 踢鼓时贝斯让路 |
| **去齿音（de-esser）** | 高频带触发 | 只压"s"音 |
| **多段压缩** | 各频段自己 | 分频段控制 |
| **外部侧链 EQ** | 侧链先过 EQ | 只让某些频率触发 |

**去齿音的典型结构**：

```
输入 → 带通滤波(5-10kHz) → 检测器 → 增益
  └──────────────────────────────→ 乘
```

> [!tip] 去齿音 = "带通侧链的压缩器"
> 只在 5-10 kHz 有能量时才压——这样"s"音被压，其他音不受影响。
>
> 如果对整个信号做检测，元音也会被压 → 声音变闷。

---

## 五、实现

```cpp
class LookaheadCompressor
{
public:
    void prepare (double sampleRate, int maxBlockSize)
    {
        sr = sampleRate;
        delayLine.assign ((size_t) maxDelaySamples, 0.0f);
        writePos = 0;
        env = 0.0f;
        // ⚠️ 前瞻延迟在参数变化时改变 → 需要在消息线程调 setLatencySamples
    }

    void setLookaheadMs (float ms)
    {
        const int newSamples = (int) std::round (ms * 0.001 * sr);
        lookahead = std::clamp (newSamples, 0, maxDelaySamples - 1);
        // ⚠️ 不要在音频线程调 setLatencySamples（见 [[延迟报告 latency reporting]]）
        pendingLatency.store (lookahead);
    }

    // 每采样：x 是主输入，sc 是侧链输入（不使用时传 x）
    float process (float x, float sc) noexcept
    {
        // ① 检测器（看侧链/原始信号）
        const float rect = std::fabs (sc);
        const float c = (rect > env) ? attackCoeff : releaseCoeff;
        env += c * (rect - env);

        // ② 算增益衰减
        const float lv = juce::Decibels::gainToDecibels (env + 1e-9f);
        const float grDb = curve.gainReductionDb (lv);
        const float g = juce::Decibels::decibelsToGain (grDb);

        // ③ 把输入推进延迟线，取出"过去"的样本
        delayLine[(size_t) writePos] = x;
        int readPos = writePos - lookahead;
        if (readPos < 0) readPos += (int) delayLine.size();
        const float delayed = delayLine[(size_t) readPos];

        if (++writePos >= (int) delayLine.size()) writePos = 0;

        // ④ 对**延迟后的**样本应用增益
        return delayed * g;
    }

private:
    double sr = 48000.0;
    std::vector<float> delayLine;
    int writePos = 0, lookahead = 0, maxDelaySamples = 1;
    float env = 0.0f, attackCoeff = 0.01f, releaseCoeff = 0.0001f;
    CompressorCurve curve;
    std::atomic<int> pendingLatency { 0 };
};
```

> [!warning] 三个实现细节
> 1. **延迟线长度按最大前瞻分配**（避免运行时重新分配）
> 2. **`setLatencySamples` 不能在音频线程调**（见 [[旁路 bypass 的正确实现]]）
> 3. **增益要平滑**（见 [[参数平滑 parameter smoothing]]）

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **忘了 `setLatencySamples`** | 多轨错位（-17.7 dB 级差异） | grep `setLatencySamples` |
| 2 | **在音频线程调 `setLatencySamples`** | 宿主加锁 → 爆音 | 检查调用位置 |
| 3 | **前瞻延迟线每次重新分配** | 违反实时契约 | prepare 里分配 |
| 4 | **检测器看了延迟后的信号** | 前瞻失效（等于没用） | 检查检测器输入 |
| 5 | **延迟线的读写索引搞反** | 输出超前/错位 | 测脉冲位置 |
| 6 | **增益没平滑** | 喀哒声/失真 | 见 [[参数平滑 parameter smoothing]] |
| 7 | **侧链没做高通** | 低频老是触发 | 检测器前加 HP |
| 8 | **去齿音用全频检测** | 元音也被压（变闷） | 用带通侧链 |
| 9 | **前瞻改变了延迟但没通知宿主** | PDC 错乱 | 见 [[延迟报告 latency reporting]] |
| 10 | **把侧链和前瞻混为一谈** | 概念错，实现也错 | 见开头对照表 |

> [!danger] 第 4 条最容易犯
> 写成"检测器看延迟后的信号"时，代码**看起来完全正常**，
> 但前瞻**完全失效**——峰值照样漏过。
>
> **判据**：喂一个尖峰脉冲，有前瞻时输出峰值应显著低于无前瞻。
> 实测：0ms → 0.9000，1ms → 0.4862。**如果两者相同，就是这个问题。**

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 瞬态漏过压缩 | 没有前瞻 / 检测器看了延迟信号 | 检查检测器输入 |
| 多轨错位 | 没报告延迟 | `setLatencySamples` |
| 改前瞻时爆音 | 音频线程调宿主 API | 移到消息线程 |
| 录音时演奏不适 | 前瞻延迟太大 | 让用户可关掉 |
| 低频老是触发 | 检测器没高通 | 加 HP |
| 去齿音让声音变闷 | 全频检测 | 用带通侧链 |
| 压缩有喀哒声 | 增益没平滑 | 加平滑 |
| 前瞻改了但没生效 | 延迟线长度/索引错 | 测脉冲位置 |

---

## 八、怎么验证

**三个必做测试**：

| # | 测试 | 判据 |
|---|---|---|
| 1 | **前瞻有效** | 尖峰输出峰值显著低于无前瞻 |
| 2 | **延迟正确** | 脉冲位置 = 报告的延迟 |
| 3 | **透明性**（增益=1 时） | null test ≈ 0 |

```python
import numpy as np

SR = 48000

def compress (x, lookahead_ms, attack_ms, release_ms, thr_db=-12, ratio=4):
    L = int (lookahead_ms * SR / 1000)
    xd = np.concatenate ([np.zeros(L), x])[:len(x)]
    a_c = 1 - np.exp (-1/(attack_ms*0.001*SR))
    r_c = 1 - np.exp (-1/(release_ms*0.001*SR))
    env = 0.0; envs = np.zeros (len(x))
    for i, v in enumerate (np.abs(x)):
        c = a_c if v > env else r_c
        env += c*(v-env); envs[i] = env
    lv = 20*np.log10 (envs + 1e-12)
    gr = np.where (lv > thr_db, (thr_db-lv)*(1-1/ratio), 0.0)
    return xd * (10**(gr/20))

# ① 前瞻有效性
x = np.zeros (SR); x[SR//2] = 0.9; x[SR//2+1:SR//2+50] = 0.9
peak_no_la = np.max (np.abs (compress (x, 0,  1.0, 50)))
peak_la    = np.max (np.abs (compress (x, 1.0, 1.0, 50)))

print (f"  无前瞻峰值: {peak_no_la:.4f}")
print (f"  有前瞻峰值: {peak_la:.4f}")
assert peak_no_la > 0.8,  "无前瞻应该漏掉瞬态（这是预期行为）"
assert peak_la    < 0.6,  "有前瞻应该压制瞬态！"
print ("  ✅ 前瞻有效")

# ② 延迟正确
imp = np.zeros (SR); imp[SR//4] = 1.0
y = compress (imp, 5.0, 1.0, 50, thr_db=0, ratio=1)   # 不压缩，只看延迟
first = np.argmax (np.abs (y) > 1e-6)
expected = SR//4 + int (5.0*SR/1000)
print (f"  脉冲位置: {first}（期望 {expected}）")
assert first == expected, "延迟不对！"
print ("  ✅ 延迟正确")
```

> [!important] 第一个断言特别有价值
> `assert peak_no_la > 0.8` 把"没有前瞻就会漏掉瞬态"**固化成断言**。
> 这样如果实现意外地"有效"了（比如检测器看错了信号），测试也会失败。

---

## 相关

- [[MOC - DSP]]
- [[动态范围处理]] — 压缩器的完整数学
- [[软膝 soft knee]] — transfer curve
- [[包络跟随器 envelope follower]] — 检测器
- [[延迟报告 latency reporting]] — 前瞻的延迟必须报告
- [[旁路 bypass 的正确实现]] — 延迟在旁路时也要保持
- [[参数平滑 parameter smoothing]]
- [[多段压缩]]

> [!note] 待补充
> - 前瞻与 attack 时间的**交互**（前瞻多久才够？）
> - 零延迟限制器（zero-latency limiter）的技术
> - 侧链的**立体声链接**策略
> - 实测：不同前瞻时长对瞬态的听感影响（ABX）
> - 去齿音的带通参数选择
