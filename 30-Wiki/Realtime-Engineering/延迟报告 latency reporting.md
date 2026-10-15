---
title: 延迟报告 latency reporting
type: wiki
domain: realtime
status: solid
confidence: high
sources: ["[[Bencina - Real-time audio programming 101]]"]
tags: [gotcha, cpp, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 延迟报告 latency reporting

> [!important] 一句话
> **你的插件只要让音频"晚出来"哪怕 1 个采样，就必须告诉宿主。**
> 宿主用这个数字做**延迟补偿（PDC）**，让所有轨道重新对齐。
> **报错的延迟比不报更糟**——宿主会按错误的值补偿，产生固定但错误的错位，
> 而用户几乎无法诊断。

## 为什么这一页重要

**实测**（本库，lookahead 限制器，5 ms = 240 采样 @ 48 kHz）：

| 旁路实现 | 脉冲位置 | 相对干信号 |
|---|---|---|
| 干信号（无处理） | 1000 | — |
| ❌ **旁路时跳过延迟线** | 1000 | **提前 0 采样** |
| ✅ **旁路时保持延迟** | **1240** | **延迟 240 采样 = 5.00 ms** |

<!-- derived: 50-Playground/tools/cpp/latency_bypass_test.cpp，2026-10-15 实测 -->

**后果链**：

```
插件有 240 采样延迟但不报告
   → 宿主不补偿这条轨
   → 这条轨比别的轨晚 240 采样（5 ms）
   → 叠加时相位错位 → 梳状滤波 / 低频抵消
   → 用户听到"这个插件一挂上声音就变薄了"
```

> [!danger] 5 ms 的错位在低频是灾难性的
> 5 ms 对应 200 Hz 的**一个完整周期**。
> 两条相同的低频信号错开半个周期（2.5 ms）就会**完全抵消**。
> **这不是"音质变差"，是"低频消失了"。**

---

## 一、`setLatencySamples` 的用法

```cpp
// JUCE
void prepareToPlay (double sampleRate, int samplesPerBlock) override
{
    // ① 先算出你的处理引入多少延迟
    const int lookaheadSamples = (int) std::round (lookaheadMs * 0.001 * sampleRate);

    // ② 按这个长度分配延迟线
    lookaheadBuffer.assign ((size_t) lookaheadSamples, 0.0f);

    // ③ 报告给宿主
    setLatencySamples (lookaheadSamples);
}
```

> [!warning] `setLatencySamples` 的调用时机（JUCE 文档明确要求）
> JUCE 文档原文：**"The processor should call this as soon as it can during
> initialisation, and can call it later if the value changes."**
> 即：**初始化时尽早调用**，值变化时**可以再次调用**。
>
> | 位置 | 可以吗 | 说明 |
> |---|---|---|
> | 构造函数 | ⚠️ 可以但不推荐 | 此时还不知道采样率，算不出采样数 |
> | **`prepareToPlay`** | ✅ **推荐** | 采样率已知，缓冲区已分配 |
> | `processBlock`（音频线程） | ❌ **不要** | 见下 |
> | 参数回调（消息线程） | ✅ 可以 | 过采样倍率变化时 |
>
> **绝对不要在音频线程调用。** 它会让宿主重新计算 PDC，
> 涉及宿主内部的锁与图重排——违反 [[实时音频线程契约]]。

> [!important] `setLatencySamples` 与 `getLatencySamples` 的关系
> - **`setLatencySamples(n)`** — 你的插件**声明**"我引入了 n 个采样延迟"
> - **`getLatencySamples()`** — 宿主**查询**这个值（宿主内部通常也缓存一份）
>
> **它们只是"声明"，不是"自动补偿"。** 真正的补偿由**宿主**完成：
> 宿主把所有轨道的延迟对齐到最大值（或它的缓冲区粒度）。
> **你的责任只是报准。**

---

## 二、哪些处理会引入延迟

| 处理 | 延迟来源 | 典型量级（48 kHz） | 能否避免 |
|---|---|---|---|
| **Lookahead 限制器/压缩器** | 音频被故意推后 | 1–10 ms（48–480 采样） | ❌ 不可避免（因果性要求） |
| **过采样（FIR 半带）** | 线性相位滤波器的群延迟 | 每 2× 级约 10–40 采样 | ⚠️ 可用 IIR 降到几采样 |
| **过采样（IIR polyphase allpass）** | 全通的相位延迟 | 每 2× 级约 2–6 采样 | ⚠️ 已是最小，但非线性相位 |
| **FFT / STFT 处理** | 需要一整帧才能变换 | 1–2 个窗长（1024–4096 采样） | ❌ 不可避免 |
| **线性相位 FIR EQ** | 群延迟 = (N-1)/2 | 可达数千采样 | ✅ 换 IIR（有相位失真） |
| **卷积混响（分区）** | 分区大小 / 2 | 64–512 采样 | ⚠️ 分区越小延迟越低、CPU 越高 |
| **多段压缩的分频器** | Linkwitz-Riley 全通相位 | 通常几十采样 | ⚠️ 用零延迟分频器 |

### 实测：过采样倍率对总延迟的影响

| 过采样倍率 | 抗混叠滤波器延迟 | 总延迟（含 240 采样 lookahead） | 折合 ms |
|---|---|---|---|
| 1× | 0 | 240 | 5.000 |
| 2× | 3 | 243 | 5.062 |
| 4× | 6 | 246 | 5.125 |
| 8× | 9 | 249 | 5.188 |

<!-- derived: latency_bypass_test.cpp §4，2026-10-15 实测 -->

> [!warning] 上表的滤波器延迟是**量级示例**，不是某个具体实现的精确值
> 它假设每级 2× 的 IIR allpass 半带滤波器约 3 采样延迟。
> **真实值取决于你的滤波器设计**（见 [[过采样 oversampling]]）。
> 关键是**数量级**：IIR 过采样的延迟很小（个位数采样），FIR 的大得多。
>
> **你自己的插件必须实测**：喂脉冲，看输出的第一个非零样本出现在第几个采样。

> [!important] 关键认识：**延迟是因果性的代价，不是 bug**
> Lookahead 限制器**必须**延迟，因为它需要"先看到未来"才能提前衰减增益
> （见 [[动态处理的原理]] §5）。FFT 处理**必须**攒够一帧。
> **这些延迟不能"优化掉"，只能"报准"。**

---

## 三、不报告的后果

| 场景 | 后果 |
|---|---|
| **多轨混音** | 各轨错位 → 相位抵消、梳状滤波、立体声像偏移 |
| **并行处理**（如并联压缩） | 干湿两路错位 → 低频被梳状抵消（最典型的症状） |
| **录音监听** | 演奏者听到的自己有延迟 → 演奏"跟不上"（> 10 ms 明显） |
| **离线导出（bounce）** | 导出结果与实时播放**不一致** |
| **多实例串联** | 延迟累积，宿主补偿错误 |
| **宿主 PDC 失效** | 整个工程的延迟补偿链条算错 → **所有轨道**都错位 |

> [!danger] "并行处理"是最容易暴露的场景
> 用户把一个有延迟的插件**并联**在干信号旁边（或用宿主自带的 dry/wet），
> 如果插件不报延迟：
>
> | 干湿错位 | 结果 |
> |---|---|
> | 0 采样 | ✅ 正常 |
> | 几个采样 | 高频梳状滤波（"金属声"） |
> | 半周期 @ 100 Hz（5 ms） | **100 Hz 完全抵消** |
>
> **用户会以为"这个插件吃低频"，而实际上是延迟没报。**

> [!warning] 报错的延迟比不报更糟
> | 情况 | 宿主行为 | 用户能诊断吗 |
> |---|---|---|
> | 不报（报 0） | 不补偿 | ⚠️ 难，但至少"没动过" |
> | **报错值** | 按错值补偿 → **固定但错误的错位** | ❌ **极难**——用户会怀疑自己的耳朵 |
>
> **"差不多就行"是错的。** 报 240 而实际 243，误差 3 采样
> 在 10 kHz 处已经是明显的相位差。

---

## 四、延迟变化时怎么办

有些参数会**改变**延迟：

| 参数 | 为什么改变延迟 |
|---|---|
| **过采样倍率**（1×/2×/4×） | 每级滤波器都有延迟 |
| **Lookahead 时间** | 直接就是延迟量 |
| **FFT 窗长** | 帧越长延迟越大 |
| **卷积混响的分区大小** | 分区越大延迟越大 |
| **线性相位 EQ 的阶数** | 群延迟 = (N-1)/2 |

### 处理流程

```cpp
// ❌ 错误：在音频线程里直接改
void processBlock (...) override
{
    if (oversamplingChanged)
        setLatencySamples (newLatency);   // ⚠️ 音频线程 → 宿主内部锁 → 爆音
}

// ✅ 正确：在消息线程（参数回调）里改
void parameterChanged (const String& id, float newValue) override
{
    if (id == "oversampling")
    {
        const int newLatency = computeLatencyFor (newValue);
        if (newLatency != getLatencySamples())
        {
            // ① 让音频线程知道"要切换了"（原子标志）
            pendingOversamplingFactor.store (factorFromValue (newValue));
            // ② 通知宿主延迟变了
            setLatencySamples (newLatency);
        }
    }
}
```

> [!important] 宿主重新计算 PDC 时会发生什么
> 宿主可能：
> - **短暂静音**或做**淡入淡出**（JUCE 的 wrapper 会尝试处理）
> - **重新排布处理图**（某些宿主会重建整个信号链）
> - 在极端情况下**重新加载插件**
>
> **所以：延迟变化应当少见、且由用户显式操作触发。**
> 不要做"自动根据素材切换过采样倍率"这种设计——每次切换都是一次 PDC 重算。

> [!warning] 切换瞬间的音频线程安全
> 倍率切换涉及**重新分配过采样缓冲区**。
> **不能在音频线程分配**（[[实时音频线程契约]]）。标准做法：
> 1. 消息线程**预先分配好**两个倍率的缓冲区
> 2. 音频线程通过原子标志切换指针
> 3. 在切换点做**短交叉淡化**（5–20 ms）避免爆音
>
> **或者更简单**：在 `prepareToPlay` 里为**最大倍率**分配一次，
> 切换时只改变"用多少"，不重新分配。

---

## 五、AI 会怎么写错

| # | AI 常写 | 为什么错 | 怎么查 |
|---|---|---|---|
| 1 | **完全忘了 `setLatencySamples`** | 宿主不补偿 → 相位错位 | grep `setLatencySamples` 是否存在 |
| 2 | **在 `processBlock` 里调用** | 音频线程 → 宿主内部锁 → 爆音 | 查调用位置 |
| 3 | **在构造函数里调用** | 此时不知道采样率，值算错 | 查是否在 `prepareToPlay` 里重算 |
| 4 | **报告"缓冲区长度"而不是"延迟"** | 概念错误 | 延迟 = 音频被推后的采样数 |
| 5 | **过采样忘了算滤波器延迟** | 少报几十采样 | 见 §2 的表 |
| 6 | **只报 lookahead，忘了过采样** | 少报 | 总延迟 = 所有环节之和 |
| 7 | **延迟变化时不重新报告** | 宿主用旧值补偿 | 参数回调里重算 |
| 8 | **用毫秒而不是采样数** | API 要的是采样数 | 查 `setLatencySamples` 的参数 |
| 9 | **以为报告了宿主就"自动补偿"** | 宿主补偿的是**轨道对齐**，不是"消除延迟" | 见 §1 的说明 |
| 10 | **切换倍率时在音频线程重新分配** | 违反实时契约 | 预先分配最大倍率 |
| 11 | **旁路时忘了保持延迟** | 旁路瞬间音频提前 | 见 [[旁路 bypass 的正确实现]] |
| 12 | **离线渲染时假设延迟为 0** | 导出与实时不一致 | 离线路径也要走同样的延迟线 |

> [!tip] 第 1 条是最常见的，也是最好查的
> **让 AI 写完一个带 lookahead/过采样/FFT 的插件后，第一件事就是 grep `setLatencySamples`。**
> 如果不存在，那这个插件在多轨工程里一定是坏的——
> **而且它在单独试听时完全正常**，这就是为什么很难发现。

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 挂上插件后"声音变薄" | 延迟未报 → 相位错位 | 正确 `setLatencySamples` |
| 并联压缩的低频消失 | 干湿两路错位 | 同上（或用宿主 dry/wet） |
| 录音监听有延迟感 | 插件延迟大且未报 | 报告延迟；或减小 lookahead |
| 导出结果和播放不一样 | 离线路径没走延迟线 | 两条路径共用同一实现 |
| 切换过采样时爆音 | 音频线程重新分配/报告 | 预分配 + 消息线程报告 |
| 宿主显示延迟数字不对 | 报错了值 | 喂脉冲实测 |
| 旁路时音量跳变/相位跳变 | 旁路没保持延迟 | 见 [[旁路 bypass 的正确实现]] |
| 多实例串联后错位 | 延迟累积但只报了一个 | 每个实例各报各的 |
| 某些宿主正常、某些不正常 | 宿主对延迟变化的处理不同 | 避免频繁变化延迟 |

---

## 七、怎么验证

> [!important] 延迟必须**实测**，不能靠"算出来应该是对的"
> 一行断言就能验证，而且能进 CI。

| # | 验证什么 | 方法 | 通过标准 |
|---|---|---|---|
| 1 | **实际延迟** | 喂单位脉冲，找输出的第一个非零样本 | 索引 == `getLatencySamples()` |
| 2 | **报告值与实际一致** | 同上 | 差值 == 0 |
| 3 | **旁路时延迟不变** | 旁路前后各喂脉冲 | 两次的峰值位置相同 |
| 4 | **延迟不随 block size 变** | 用 32/64/512 的 block size 各测一次 | 延迟恒定 |
| 5 | **过采样倍率变化时更新** | 切换倍率，重测 | 报告值 == 实测值 |
| 6 | **离线渲染一致** | 实时渲染 vs 离线渲染同一段 | null test < -100 dB |

```cpp
// 最实用的一个测试：直接测出实际延迟
int measureLatencySamples()
{
    const int N = 8192;
    std::vector<float> in (N, 0.0f), out (N, 0.0f);
    in[0] = 1.0f;                        // 单位脉冲

    // 用你插件的 processBlock 处理（分块，模拟宿主）
    for (int i = 0; i < N; i += blockSize)
    {
        const int n = std::min (blockSize, N - i);
        processBlockForTest (in.data() + i, out.data() + i, n);
    }

    for (int i = 0; i < N; ++i)
        if (std::abs (out[(size_t) i]) > 1e-6f)
            return i;                     // 第一个非零样本的位置 = 延迟
    return -1;
}

// 断言：必须和报告值一致
assert (measureLatencySamples() == getLatencySamples());
```

```python
# Python 端：null test 验证延迟补偿是否正确
import numpy as np, sys
sys.path.insert(0, '50-Playground/tools')
from audio_io import impulse, null_test

# ① 测实际延迟
h = my_plugin.process(impulse(8192))
lat = int(np.argmax(np.abs(h) > 1e-6))
print(f"实测延迟 = {lat} 采样 ({lat/48000*1000:.2f} ms)")
assert lat == my_plugin.get_latency_samples(), "报告值与实际不符！"

# ② 对齐后做 null test：旁路输出应与干信号完全一致
dry = impulse(8192)
bypassed = my_plugin.process_bypassed(impulse(8192))
null_test(bypassed[lat:], dry[:len(dry)-lat], "旁路 vs 干信号（对齐后）")
# 期望：最大差异 < -300 dB（即浮点 0）
```

> [!tip] 测试 1 和 2 是同一个测试，但价值极高
> 它同时抓住了：忘了报告、报错值、延迟随 block size 变、
> 旁路没保持延迟（测试 3）。
> **而且它不需要人耳、不需要宿主、可以进 CI。**

---

## 相关

- [[旁路 bypass 的正确实现]] — 有延迟的插件旁路时**必须保持延迟**
- [[过采样 oversampling]] — 抗混叠滤波器的延迟量级
- [[动态处理的原理]] — lookahead 为什么必然引入延迟
- [[实时音频线程契约]] — 为什么不能在音频线程调用 `setLatencySamples`
- [[插件验证工具]] — pluginval 会检查延迟报告
- [[音频测量基础]] — null test 与脉冲响应测量
- [[MOC - Realtime Engineering]] · [[MOC - Plugin Formats]]

> [!note] 待补充
> - **实测各种过采样实现的真实延迟**（FIR vs IIR polyphase，各倍率）
> - **各宿主对延迟变化的处理差异**（Logic / Ableton / Reaper / Cubase）
> - **VST3 的 `setInitialDelay` 与 AU 的对应 API**（本页只覆盖 JUCE 层）
> - **线性相位 EQ 的延迟与 CPU 权衡实测**
> - **分区卷积的延迟 vs 分区大小实测**
> - **录音监听场景下"可接受延迟"的主观阈值**（需要听音实验）

> [!warning] 未验证
> - 本页 §2 的"典型量级"是**基于常见实现的估算**，不是对具体产品的测量。
>   你自己的插件必须实测（见 §7）。
> - "5 ms 错位导致低频抵消"是基于相位关系的**推导**，本库未做听音实验。
