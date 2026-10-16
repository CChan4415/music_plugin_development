---
title: 音频缓冲区与 block size
type: wiki
domain: realtime
status: solid
confidence: high
sources: ["[[Bencina - Real-time audio programming 101]]"]
tags: [gotcha, cpp, recipe]
created: 2026-10-16
updated: 2026-10-16
---

# 音频缓冲区与 block size

> [!important] 一句话
> **block size 是宿主决定的，不是你能选的。**
> 而且它**会变**——你必须在任何尺寸下都正确。

## 为什么这是插件崩溃的头号原因

> [!danger] 最常见的崩溃模式
> ```
> 你开发时：宿主给的 block size = 512
> 你写死：   float temp[512];
> 用户那边：宿主给 1024 → 栈溢出 / 越界
> ```
>
> **而且症状是"换个宿主/改个设置就崩"**——
> 你本地永远复现不了。

---

## 一、block size 是**变量**

> [!important] 它会因为很多原因变化
> | 原因 | 结果 |
> |---|---|
> | 宿主设置（用户改缓冲区大小） | 512 → 256 → 2048 |
> | **采样率变化** | 宿主可能同时改 block size |
> | 宿主内部处理需要 | 有时给大块，有时给小块 |
> | **离线导出（bounce）** | 通常给很大的块（如 4096+） |
> | 轨道路由/侧链 | 可能是不同的块 |
>
> **实测经验**：常见的 block size 有
> **32、64、128、256、512、1024、2048、4096**——
> 你的代码必须对**所有**这些尺寸正确。

> [!warning] 极端的 block size
> - **`numSamples == 0`**：宿主可能在"空转"时调用 → **必须处理**
> - **1 个采样**：某些宿主在特殊情况下会这样调用
> - **非常大的块**（8192+）：离线导出时
>
> **都不应该崩溃。**

---

## 二、正确写法

```cpp
void processBlock (juce::AudioBuffer<float>& buffer,
                   juce::MidiBuffer&) override
{
    // ① ⚠️ 必须处理 0 长度（宿主会这样调）
    const int numSamples = buffer.getNumSamples();
    if (numSamples == 0)
        return;

    // ② ⭐ 只用传入的值，绝不假设
    const int numChannels = buffer.getNumChannels();

    // ③ 用缓冲区自己的声道遍历（不假设 stereo）
    for (int ch = 0; ch < numChannels; ++ch)
    {
        auto* data = buffer.getWritePointer (ch);
        for (int i = 0; i < numSamples; ++i)
        {
            // DSP...
        }
    }
}
```

> [!danger] 四个"绝不"
> | # | 绝不 |
> |---|---|
> | 1 | **绝不**假设 `numSamples` 是某个固定值 |
> | 2 | **绝不**假设声道数是 2 |
> | 3 | **绝不**在栈上开固定大小的数组 |
> | 4 | **绝不**忽略 `numSamples == 0` |

---

## 三、缓冲区在哪里分配

> [!important] 音频线程**不能分配内存**
> 所以缓冲区必须在 `prepareToPlay` 里按**最大可能**的 block size 分配。

```cpp
class MyProcessor : public juce::AudioProcessor
{
public:
    void prepareToPlay (double sampleRate, int samplesPerBlock) override
    {
        // ⭐ 按宿主声明的最大块分配
        scratchBuffer.setSize (getTotalNumOutputChannels(), samplesPerBlock);
        // ⚠️ 不要假设下一块不会更大——但 JUCE 保证不超过 samplesPerBlock
    }

    void processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
    {
        const int n = buffer.getNumSamples();
        if (n == 0) return;

        // ✅ 用预分配的缓冲，不再分配
        // 但要检查 n <= scratchBuffer.getNumSamples()
        jassert (n <= scratchBuffer.getNumSamples());
    }

private:
    juce::AudioBuffer<float> scratchBuffer;
};
```

> [!warning] `samplesPerBlock` 的含义
> JUCE 传给你的 `samplesPerBlock` 是**宿主声明的上限**。
> 正常情况下 `numSamples <= samplesPerBlock`。
>
> **但为了安全**：加 `jassert` 检查，并在发布版里做钳制（防御性编程）。

> [!tip] 更大的块要不要自己处理？
> 有些宿主在**离线导出**时会一次给很大的块（超过 `samplesPerBlock`）。
> 稳妥做法：
> ```cpp
> // 如果块超过预分配，分片处理
> int offset = 0;
> while (offset < n) {
>     const int chunk = std::min (n - offset, scratchBuffer.getNumSamples());
>     processChunk (buffer, offset, chunk);
>     offset += chunk;
> }
> ```
> ⚠️ 这种情况是否真的发生**需实测确认**。

---

## 四、缓冲区的布局

> [!important] `AudioBuffer` 的两种访问方式

| 方式 | 代码 | 何时用 |
|---|---|---|
| **按声道**（分开的指针） | `buffer.getWritePointer(ch)` | ✅ **默认**（JUCE 就是分声道的） |
| 交错（interleaved） | 需手动转换 | 某些第三方库要交错格式 |

```cpp
// ✅ 按声道（JUCE 的原生布局）
for (int ch = 0; ch < numChannels; ++ch)
{
    float* data = buffer.getWritePointer (ch);
    for (int i = 0; i < numSamples; ++i)
        data[i] = process (data[i]);
}

// 如果是立体声链接的处理（如压缩器），需要同时读两个声道
if (numChannels >= 2)
{
    auto* L = buffer.getWritePointer (0);
    auto* R = buffer.getWritePointer (1);
    for (int i = 0; i < numSamples; ++i)
    {
        const float linked = std::max (std::abs (L[i]), std::abs (R[i]));
        const float g = computeGain (linked);
        L[i] *= g;
        R[i] *= g;          // ⭐ 左右用**同一个**增益
    }
}
```

> [!danger] 立体声处理必须**链接**
> 如果左右独立算增益，会出现**声像漂移**：
> 左边响时左边被压，右边不压 → 声音跑到右边。
>
> **规则**：压缩器/限制器的增益衰减必须左右共用。

---

## 五、采样率也会变

> [!important] `prepareToPlay` 会被**反复调用**
> 用户改采样率、改缓冲区大小、切换音频设备 → 都会重新调用。
>
> **所以 `prepareToPlay` 必须幂等**：反复调用不能泄漏、不能累积。

```cpp
void prepareToPlay (double sampleRate, int samplesPerBlock) override
{
    // ⚠️ 这些赋值是幂等的（覆盖旧值）
    sr = sampleRate;
    blockSize = samplesPerBlock;

    // ⚠️ resize 是幂等的（JUCE 会复用已有内存）
    scratchBuffer.setSize (getTotalNumOutputChannels(), samplesPerBlock);

    // ⚠️ 状态必须重置（否则换采样率后有残留）
    resetState();
}
```

> [!danger] 忘了重置状态的后果
> 换采样率后，滤波器/延迟线里还留着**按旧采样率算的状态** →
> 瞬间的噪声或爆音。
>
> **`prepareToPlay` 里一定要重置所有 DSP 状态。**

见 [[采样率变化处理]]（待写）。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **写死 `float temp[512]`** | 大块时栈溢出 | grep 固定大小数组 |
| 2 | **不处理 `numSamples == 0`** | 边界崩溃 | 检查开头 |
| 3 | **假设声道数 == 2** | 单声道/多声道崩溃 | 用 `getNumChannels()` |
| 4 | **在 `processBlock` 里分配** | 违反实时契约 | 移到 `prepareToPlay` |
| 5 | **`prepareToPlay` 不幂等** | 反复调用泄漏 | 检查是否有累积 |
| 6 | **忘了重置 DSP 状态** | 换采样率后爆音 | 加 `reset()` |
| 7 | **左右独立算增益** | 声像漂移 | 链接增益 |
| 8 | **假设缓冲区是交错的** | 完全错的数据 | JUCE 是分声道的 |
| 9 | **不检查 `numChannels` 就访问 ch=1** | 单声道越界 | 先判断 |
| 10 | **用 `getNumSamples()` 当常量** | 缓存了旧值 | 每块重新取 |

> [!danger] 第 1 条是最经典的
> AI 会写 `float temp[512]` 或 `float temp[samplesPerBlock]`（VLA，非标准 C++）。
> 前者在大块时溢出，后者**根本不是合法 C++**（GCC/Clang 作为扩展支持，MSVC 不支持）。
>
> **判据**：`processBlock` 调用链里 grep `[数字]` 形式的数组声明。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 换个宿主就崩 | 假设了固定 block size | 只用传入的值 |
| 大块时崩溃 | 栈上固定数组 | 预分配 |
| 单声道输入崩溃 | 假设 stereo | 检查 `numChannels` |
| 换采样率后有爆音 | 状态没重置 | `prepareToPlay` 里 reset |
| 声像漂移 | 左右独立算增益 | 链接增益 |
| 偶发爆音 | 块内分配 | 移到 prepare |
| 导出时崩溃 | 离线块特别大 | 分片处理 |
| 反复改设置后变慢 | `prepareToPlay` 不幂等 | 检查累积 |

---

## 八、怎么验证

> [!important] 用**多种 block size** 测（这是关键）

**四个必做测试**：

| # | 测试 | 判据 |
|---|---|---|
| 1 | **多种 block size** | 1 / 16 / 512 / 4096 都不崩 |
| 2 | **`numSamples == 0`** | 不崩 |
| 3 | **单声道 / 多声道** | 不越界 |
| 4 | **反复 `prepareToPlay`** | 无泄漏、无累积 |

```bash
# ⭐ 用 sanitizer 跑多种 block size（本库推荐）
clang++ -std=c++17 -O1 -g \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    test_dsp.cpp -o test_dsp_san

for bs in 0 1 16 64 256 512 1024 2048 4096; do
    printf "  blockSize=%-5s " "$bs"
    ./test_dsp_san "$bs" >/dev/null 2>&1 && echo "✅" || echo "❌"
done

for sr in 44100 48000 88200 96000 192000; do
    printf "  sampleRate=%-7s " "$sr"
    ./test_dsp_san 512 "$sr" >/dev/null 2>&1 && echo "✅" || echo "❌"
done
```

> [!tip] 这是 ASan 最有价值的用法
> ASan **只在真的越界时报错**。
> 如果你只测 512，而 bug 在 1024 时出现 → **它什么都不说**。
>
> **必须遍历参数。** 见 [[AddressSanitizer]]。

> [!warning] 本库的测试脚本用了 `blockSize=0`
> 上面循环里第一个值是 **0**——专门测"0 长度块"。
> 这是最容易被忽略的边界。

---

## 相关

- [[MOC - Realtime Engineering]]
- [[实时音频线程契约]] — 为什么不能分配/加锁
- [[AddressSanitizer]] — 用多种 block size 跑
- [[采样率变化处理]]（待写）— `prepareToPlay` 的幂等性
- [[参数自动化与线程安全]]
- [[旁路 bypass 的正确实现]] — 也要处理 0 长度
- [[DSP 单元测试怎么写]] — 参数化测试
- [[JUCE 的架构与模块划分]] — 生命周期
- [[Bencina - Real-time audio programming 101]]

> [!note] 待补充
> - **实测：各宿主实际的 block size 分布**（需真实插件）
> - 离线导出时块是否真的超限（需实测）
> - 交错格式的转换开销
> - 多声道（5.1/7.1）的处理
> - block size 对算法选择的影响（FFT 分块等）
