---
title: C++ 零基础到音频 DSP 路线
type: wiki
domain: frameworks
status: seed
confidence: medium
sources: []
tags: [todo, cpp]
created: 2026-10-14
updated: 2026-10-14
---

# C++ 零基础到音频 DSP 路线

> [!important] 唯一的设计原则
> **每个阶段都必须产出一个"能听到"或"能看到"的东西。**
> 不存在"先打三个月基础"这种阶段——那种路线你已经知道自己会放弃。
> 如果某个阶段结束时手上没有新东西可以听、可以看图、可以在 DAW 里加载，这个阶段的设计就是错的。

**本页不从"什么是变量"讲起。** 它假设你已经有变量/循环/条件/函数/数组的概念、知道源码和编译是什么、能读懂别人的代码、会用 git 和命令行。缺的只有两样：**C++ 的语法**（`&`、`const`、`::`、头文件、模板调用长什么样）和 **C++ 的内存模型**（栈 vs 堆、对象在哪、谁负责释放、指针指向哪）。

> [!note] 你不是"零基础"，是"零 C++"
> 这两者的路径完全不同。前者要从"程序是什么"开始，后者可以直接从"用 C++ 写一个能出声的东西"开始。

> [!warning] 但有一个真实的心理落差
> 会 Python 的人学 C++，最容易在**第 3 天到第 3 周**之间崩溃。Python 里一行 `x = [1,2,3]` 的事，C++ 里要处理类型、头文件、构建系统、链接错误。
> 你的生产力会**先下降再上升**。这不是退步，是工具链的固定成本——阶段 0 的唯一目的就是尽快把它付完。

## 诚实版难度说明

> [!warning] 未验证：下面所有时间数字都是判断，不是测量
> 基于"有编程基础、无 C++ 经验、无 DSP 数学"这个组合的常见经验，**没有引用任何学习研究或统计数据**。实际可能上下浮动 50%，请当**量级参考**，不要当承诺。

| 阶段 | 你会做出什么 | 估算小时 |
|---|---|---|
| 0 · C++ 最小可用子集 | 一个能编译运行的命令行程序 | 15–25 |
| 1 · 指针与内存 | 一个自己写的环形缓冲区 | 15–25 |
| 2 · 读写 WAV | 读 WAV → 改增益 → 写 WAV，**你能用耳朵听** | 10–18 |
| 3 · 第一个 DSP | 5 个 DSP 模块 + Python 验证图 | 30–50 |
| 4 · 进入 JUCE | **一个能在 DAW 里加载并出声的插件** | 20–35 |
| 5 · GUI 与参数 | 有旋钮、能自动化、状态能保存 | 20–30 |
| | **合计** | **110–183** |

| 每周投入 | 到阶段 4 结束（插件能出声） | 到阶段 5 结束（能给别人用） |
|---|---|---|
| **5 小时**（兴趣节奏） | 4.5–7 个月 | 5–8.5 个月 |
| **10 小时**（稳定推进） | 2–3.5 个月 | 2.5–4 个月 |
| **20 小时**（接近全职） | 1–2 个月 | 1.5–2 个月 |

几句实话：**阶段 3 全程最长**，比"进入 JUCE"长得多——多数人以为难点在框架，其实在 DSP；**阶段 1 最容易放弃**，因为它是唯一"产出不可听"的阶段；**上面的时间不含"卡住"**，第一次遇到链接错误、段错误、插件在宿主里不出现，每次都可能吃掉一整个周末。

## 阶段 0：C++ 的最小可用子集

**目标**：能用 C++ 写一个完整的、能编译运行的命令行程序。不求优雅，只求闭环。**学什么**：编译运行流程（源码 → 目标文件 → 可执行文件）；基本类型 `int`/`float`/`double`/`bool`；函数（声明、定义、参数、返回值）；`std::vector<float>`；引用 `&` 与 `const`；类的最基本用法；`#include` 与头文件的作用。

```cpp
#include <algorithm>
#include <vector>

// const 引用：不拷贝、也不许改 —— 音频代码里传缓冲区的标准姿势
float peakLevel (const std::vector<float>& buffer)
{
    float peak = 0.0f;
    for (float x : buffer)                          // 范围 for
        peak = std::max (peak, (x < 0.0f) ? -x : x);
    return peak;
}
```

**产出**：你能自己从零写出这种程序并解释每一行（含一个 `main` 把它跑起来）。**怎么验证**：`clang++ -std=c++17 -Wall main.cpp -o main && ./main` 打印 `peak = 0.8`。加 `-Wall` 是硬要求——C++ 的警告里有大量真实的 bug 提示。

> [!important] 明确列出：这些现在**不用学**
> 这条比"学什么"更重要。零基础的人 90% 的时间浪费在这里。
> **暂时跳过**：模板与模板元编程、多重继承、异常（exception）的完整语义、移动语义（move）与完美转发、智能指针、`std::thread` 与原子操作、`constexpr`、C++20 concepts / ranges / coroutines。
> **什么时候再碰**：模板与智能指针在阶段 4 读 JUCE 源码时被动遇到；移动语义在阶段 3 之后关心拷贝开销时；并发与原子操作配合 [[SPSC 队列]] 学；其余长期不用。
> **判据**：如果一个特性在"读一段音频处理代码"时不会挡路，就推迟它。

**耗时与卡点**：15–25 小时；超过 35 小时还在原地，说明你在啃上面那张"暂时跳过"表——**回去写代码**。装不上编译器 → Xcode Command Line Tools 就够，见 [[MOC - Frameworks & Toolchain]]；分不清 `.h` 和 `.cpp` → 记住"声明放 `.h`、定义放 `.cpp`"；`#include <>` 找系统路径，`""` 先找当前目录。

## 阶段 1：指针与内存（C++ 的真正门槛）

**目标**：理解一个对象**在哪里**、**活多久**、**谁负责清理**——这是 Python/Java 背景的人唯一必须重新学习的部分。**为什么音频编程必须理解内存**：Python 里你从不问"这个数组在哪"，但在音频里这个答案决定了**插件会不会爆音**。数据在**栈（stack）**上 → 分配极快、自动回收，但空间小（通常几 MB）、生命周期限于函数作用域；在**堆（heap）**上 → 空间大、可跨函数存活，但分配要走系统调用，**耗时不可预测**。

> [!important] 阶段 1 真正的产出不是"会用指针"
> 而是**建立起"这块内存在哪"的本能**。因为 [[实时音频线程契约]] 的第一条禁令就是"音频线程里不能分配内存"——
> 如果你连"这一行会不会分配"都判断不出来，那条契约对你就是一句空话。

**学什么**：指针 `T*` 与取地址 `&`；栈 vs 堆；C 数组 `float buf[512]` 会退化成指针、**不知道自己的长度**；`std::vector` 的扩容行为（`push_back` 可能触发重新分配 → 音频线程禁用）；越界访问与段错误（不一定立刻崩，可能静默破坏别的数据）；`nullptr`。

**产出**：一个自己实现的**环形缓冲区（ring buffer）**。

```cpp
// 环形缓冲区：延迟线、混响、示波器的共同骨架，见 [[延迟线 delay line]]
class RingBuffer
{
public:
    void prepare (int n) { buffer.assign ((size_t) n, 0.0f); writePos = 0; }  // ⚠️ 只在这里分配
    void write (float x)                        // ✅ 音频线程可安全调用：只读写
    { buffer[(size_t) writePos] = x; writePos = (writePos + 1) % (int) buffer.size(); }
    float readDelayed (int d) const             // 0 = 最近写入的那个
    {   int idx = writePos - 1 - d;
        while (idx < 0) idx += (int) buffer.size();   // ⚠️ C++ 的 % 对负数返回负值
        return buffer[(size_t) idx]; }
private:
    std::vector<float> buffer;      // 容量在 prepare 时定死，之后不变
    int writePos = 0;
};
```

**怎么验证**：① 往 8 格缓冲区写 1..20，读 `readDelayed(3)` 应为 17，手算对照；② 故意写 `readDelayed(100)`（超容量），看它会不会崩——**理解为什么它不一定崩，比让它崩更重要**；③ 用 `-fsanitize=address` 重编译再跑，看越界有没有被抓到，见 [[AddressSanitizer]]。

**耗时与卡点**：15–25 小时。段错误只告诉你"崩了"不告诉你"哪一行" → 学 `lldb` 或 ASan，见 [[lldb 基础]]；`std::vector` 每次扩容都要分配 + 拷贝，别在音频线程里 `push_back`；写成 `buffer[writePos - delaySamples]` → 负数下标是未定义行为。

## 阶段 2：读写 WAV 文件 —— 第一次听到自己的代码

> [!important] 这是整条路线的情绪转折点
> 前两个阶段的产出都是"打印出来的数字"。这个阶段结束时，**你会第一次听到一段由你自己的 C++ 代码处理过的音频。**
> 这一声比后面任何阶段都重要——它是你坚持下去的燃料。

**目标**：不借助任何音频库，手写 WAV 解析与写入。**为什么不用库**：因为你需要知道"音频数据到底是什么"——一个 16-bit 立体声 WAV，剥掉头部之后**就是一串交错的整数**。这个认识一旦建立，后面所有 DSP 都只是"对这串数字做运算"。**学什么**：RIFF / WAVE 结构（`RIFF` 头 + 一串 chunk：`fmt `、`data`，可能还有 `LIST`）；**小端（little-endian）**字节序；位深与 `[-1, 1]` 浮点的映射；交错（interleaved）存储 `L R L R ...`；浮点转 `int16` 前**必须钳制**。

```cpp
struct WavData { std::vector<float> samples; uint32_t sampleRate = 0;
                 uint16_t numChannels = 0, bitsPerSample = 0; };
// 逐字节读最稳：直接 read 进结构体会被 padding 搞错字段位置。WAV 一律小端。
static uint32_t readLE (std::ifstream& f, int n)   // 读 n 字节，按小端拼成整数
{   unsigned char b[4] = { 0 };  f.read ((char*) b, n);
    uint32_t v = 0;  for (int i = 0; i < n; ++i) v |= (uint32_t) b[i] << (8 * i);
    return v; }
// 剥掉头部后，音频就是一串交错的整数 —— 这就是 WAV 的全部
WavData loadWav (const std::string& path)
{
    std::ifstream f (path, std::ios::binary);   // ⚠️ 永远加 binary
    WavData out;  f.seekg (12);                 // 跳过 RIFF/size/WAVE
    while (f)                                   // 逐个 chunk 走，别假设顺序
    {
        char id[4];
        if (! f.read (id, 4)) break;
        const uint32_t size = readLE (f, 4);
        const auto chunkStart = f.tellg();
        const std::string tag (id, 4);
        if (tag == "fmt ")   // format(2) ch(2) rate(4) byteRate(4) align(2) bits(2)
        {   readLE (f, 2);  out.numChannels = (uint16_t) readLE (f, 2);
            out.sampleRate = readLE (f, 4);  readLE (f, 4); readLE (f, 2);
            out.bitsPerSample = (uint16_t) readLE (f, 2); }
        else if (tag == "data")
        {   out.samples.resize (size / (out.bitsPerSample / 8));
            for (float& x : out.samples)
                if (out.bitsPerSample == 16)   // int16 → float：除以 32768
                    x = (float) (int16_t) readLE (f, 2) / 32768.0f;
                else                           // 32-bit float：位模式即 IEEE-754
                { const uint32_t b = readLE (f, 4); std::memcpy (&x, &b, 4); } }
        // 跳到 chunk 末尾；size 为奇数时有一个补齐字节（WAV 硬规定）
        f.seekg (chunkStart + (std::streamoff) size + (std::streamoff) (size & 1));
    }
    return out;
}
```

**产出**：一个命令行程序 `gain in.wav out.wav -6`（降低 6 dB 并写出）。两个关键函数：`dbToGain(dB) = pow(10, dB/20)`，写回时的 `toPcm16(x)` —— **先 `clamp(x, -1, 1)` 再乘 32767**，不钳制就会整数回绕成爆音。

**怎么验证**：用 Python 对照读两个文件，确认峰值比正好是 -6 dB。

```python
import numpy as np
from scipy.io import wavfile
fs, x = wavfile.read("in.wav")       # 单声道示例
fs2, y = wavfile.read("out.wav")
ratio_db = 20 * np.log10(np.abs(y).max() / np.abs(x).max())
print(f"实测增益 = {ratio_db:.2f} dB")            # 应约等于 -6.02
assert abs(ratio_db + 6.0) < 0.1, "增益不对，或钳制出问题了"
```

> [!tip] 从这里开始，你的验证方式变了
> 阶段 0–1 是"打印数字对不对"。从阶段 2 起是**"耳朵 + 图 + 数字"三重验证**。
> 你有前电子音乐人的耳朵，这是纯 CS 背景的人没有的验证通道——但**耳朵不能替代断言**，两者都要有。见 [[DSP 单元测试怎么写]]。

**耗时与卡点**：10–18 小时。padding 导致字段错位；忽略 chunk 的奇数补齐字节 → 后面所有数据错位一位，声音变成噪声；只处理 `fmt ` 恰好 16 字节 → 很多文件带扩展字段。

## 阶段 3：第一个 DSP

**目标**：在命令行程序里实现 4 个模块，**每个都用 Python 画图验证**。

> [!warning] 这一阶段不要碰 JUCE
> 理由见 [[ADR-002 选择框架]]：框架会掩盖你对信号流的理解，而信号流是后面一切的基础。
> 在命令行里你能看到每一个采样；在 JUCE 里你只能看到 `processBlock` 的参数。

| # | 模块 | 一句话原理 | 验证方式 |
|---|---|---|---|
| 1 | 增益（gain）/ 淡入淡出（fade） | 逐采样乘系数 / 系数随时间线性变化 | 峰值比 = dB 换算值；首尾为 0 且中间无跳变 |
| 2 | 一阶低通 | 输出向输入缓慢逼近 | 高频衰减 -6 dB/oct |
| 3 | Biquad 低通 | 二阶 IIR，见 [[Biquad 滤波器]] | 截止频率处 -3 dB，之后 -12 dB/oct |
| 4 | 延迟线 | 环形缓冲区 + 分数延迟插值 | 脉冲进、延迟后脉冲出 |

```cpp
// 一阶低通：y[n] = y[n-1] + a · (x[n] - y[n-1])，a = 1 - exp(-2π·fc/fs)
class OnePole
{
public:
    void setCutoff (float fc, float fs)
    { a = 1.0f - std::exp (-2.0f * 3.14159265f * fc / fs); }   // fc 越低，a 越小
    float process (float x) { y += a * (x - y); return y; }    // 一次乘加，极省 CPU
private:
    float a = 0.0f, y = 0.0f;
};
// 分数延迟：线性插值读出"两个采样之间"的值（延迟时间很少正好是整数个采样）
float readFractional (const RingBuffer& rb, float d)          // 见 [[插值]]
{   const int i0 = (int) d;  const float frac = d - (float) i0;
    const float a = rb.readDelayed (i0), b = rb.readDelayed (i0 + 1);
    return a + frac * (b - a); }
```

> [!important] 从阶段 3 开始，参数必须平滑
> 增益和滤波器频率**不能直接跳变**，否则会听到拉链噪声（zipper noise）。这不是优化，是正确性要求。
> 滤波器还有一个额外的坑：**不要直接平滑系数**，要平滑"频率、Q"这些参数然后重算系数。见 [[参数平滑 parameter smoothing]]。

**怎么验证**（每个模块都做）：① **脉冲响应**——喂单位脉冲（首采样 1，其余 0），看稳定性与衰减；② **频响**——喂对数扫频，对输出做 FFT，看曲线是否符合理论；③ **直流**——喂恒定 1.0，低通应输出 1.0，高通应输出 0.0。

> [!tip] 让 AI 写验证脚本，不要让它写 DSP
> 这三类测试的 Python 脚本非常适合交给 Agent 生成。但 DSP 必须你自己写——**否则你不会有"这个数不对"的直觉**。

**耗时与卡点**：30–50 小时，**全程最长**，收益也最持久。滤波器"爆炸"（输出变 `inf`/`nan`）→ 系数没归一化、符号约定抄错、参数没钳制，见 [[Biquad 滤波器]]；静音时 CPU 飙升 → denormal 数，见 [[denormal 数处理]]；立体声串音 → **一个声道一个滤波器实例**；扫频有阶梯感 → 系数每 block 才更新一次，见 [[窗函数]]。

## 阶段 4：进入 JUCE

**目标**：**一个能在 DAW 里加载并出声的插件。** 前置条件：阶段 3 的 4 个模块你都能自己写、能解释、能验证——达不到就回去补，**在 JUCE 里调试 DSP 比在命令行里难十倍**。

**学什么**：JUCE 项目结构（见 [[JUCE 的架构与模块划分]]）；`AudioProcessor` 生命周期（构造 → `prepareToPlay` → `processBlock` × N → `releaseResources`）；`AudioBuffer<float>`（它是**分离声道**而非交错）；CMake 构建（见 [[JUCE 的 CMake API]]、[[CMake 插件项目结构]]）；Standalone 模式（**调试利器**，不用开 DAW 就能测）。

```cpp
class MyFirstProcessor : public juce::AudioProcessor
{
public:
    // 构造函数只做轻活：宿主扫描插件时会构造它（BusesProperties 声明立体声进出）
    MyFirstProcessor() : juce::AudioProcessor (BusesProperties()
          .withInput ("In", juce::AudioChannelSet::stereo(), true)
          .withOutput ("Out", juce::AudioChannelSet::stereo(), true))
    {   addParameter (gainDb = new juce::AudioParameterFloat (
            juce::ParameterID { "gain", 1 }, "Gain", -24.0f, 24.0f, 0.0f)); }
    void prepareToPlay (double sampleRate, int) override   // 会被反复调用，必须幂等
    {   smoothedGain.reset (sampleRate, 0.02);             // 20 ms 平滑
        smoothedGain.setCurrentAndTargetValue (juce::Decibels::decibelsToGain (gainDb->get())); }
    void processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
    {
        const int n = buffer.getNumSamples();
        if (n == 0) return;                             // ⚠️ 合法情况，别漏
        smoothedGain.setTargetValue (juce::Decibels::decibelsToGain (gainDb->get()));
        for (int i = 0; i < n; ++i)
        {   const float g = smoothedGain.getNextValue();  // 每采样只推进一次
            for (int ch = 0; ch < buffer.getNumChannels(); ++ch)
                buffer.getWritePointer (ch)[i] *= g; }
    }
private:
    juce::AudioParameterFloat* gainDb = nullptr;
    juce::SmoothedValue<float> smoothedGain;
};
```

> [!warning] 这段代码里有两个新手必踩的坑
> 1. `processBlock` 第一行不判断 `n == 0` → 某些宿主会给空 block
> 2. 把 `getNextValue()` 写进**声道循环内部** → 平滑器每个声道各推进一次，左右声道得到不同增益，声像漂移。**平滑器每采样只能推进一次。**
> 另外：`AudioParameterFloat` 的第一个参数在较新的 JUCE 里是 `juce::ParameterID { "id", versionHint }`，老版本接受裸字符串。以你锁定的 release tag 的文档为准。

**产出与验证**：构建产物出现在 `_artefacts/` 下，DAW 能扫描到。① **先跑 Standalone**，不要一上来就开 DAW——这一步能把"宿主交互问题"和"DSP 问题"分流；② 再在 DAW 里加载，确认能出声；③ 跑 `pluginval` 或 `auval`，见 [[插件合规性测试：pluginval]]、[[auval 与 AU 验证]]。

**耗时与卡点**：20–35 小时，其中**至少一半花在工具链而不是 DSP 上**。DAW 里不出现 → 扫描机制、安装路径、格式没勾选，见 [[插件扫描机制]]；一加载就崩 → 构造函数里做了重活；改采样率后声音错乱 → 系数只在构造函数里算过一次，见 [[采样率变化处理]]。

## 阶段 5：加上 GUI 和参数

**目标**：插件有旋钮、能被宿主自动化、关掉工程再打开参数还在。**学什么**：参数系统 `AudioParameterFloat` / `AudioProcessorValueTreeState`（见 [[参数自动化与线程安全]]）；参数范围与曲线（**频率参数必须用对数映射**，见 [[MOC - UI & UX]]）；`juce::Slider` 与 `SliderAttachment`（见 [[JUCE 的 Slider 与旋钮]]）；`getStateInformation` / `setStateInformation`（见 [[状态保存与恢复]]）；布局 `resized()` + `FlexBox`/`Grid`（见 [[JUCE Component 体系]]）。

> [!important] 参数设计是你的主场
> 你在合成器上拧了十年旋钮，你知道**什么范围、什么默认值、什么曲线是对的**。
> 这是纯 CS 背景的开发者最容易做砸的地方——他们会把 cutoff 做成 0–20000 Hz 的线性旋钮，然后没人愿意用。
> 把这份直觉写进 [[从音乐制作人到插件开发者]] 的翻译表里。

**产出与验证**：插件有 2–3 个旋钮，能自动化，能保存状态。① 拖旋钮 → 声音连续变化，**没有咔哒声**；② 宿主里画自动化曲线 → 播放时参数跟着走；③ 关掉工程重开 → 旋钮位置和声音完全恢复；④ `pluginval --strictness-level 10` 通过，见 [[插件验证工具]]。

**耗时与卡点**：20–30 小时。旋钮动了但声音不变 → 参数没在 `processBlock` 里读；旋钮一动就爆音 → 没做平滑，见 [[参数平滑 parameter smoothing]]；关掉再打开回默认值 → 忘了实现 `getStateInformation`；销毁顺序导致崩溃 → Attachment 的生命周期陷阱，见 [[MOC - UI & UX]]。

## 为什么不用先学完数学

> [!important] 核心判断
> 做**效果器**需要的数学是**很窄的一片**：复数、z 变换、差分方程、一点三角函数。
> 而且它有一个别的学科没有的性质：**你可以用到哪学到哪，因为每一步都有听觉反馈**——你不需要"理解"一个滤波器才能听出它把高频砍掉了。

| DSP 主题 | 需要的数学 | 什么时候真的需要 |
|---|---|---|
| 增益、淡入淡出、混音、一阶低通/高通 | 四则运算、dB 换算、指数函数 `exp` | 立刻 |
| [[Biquad 滤波器]] | `sin`/`cos`、`ω = 2πf/fs` | 做 EQ 时 |
| [[传递函数与 z 变换]] · [[极零点与稳定性]] | 复数、`z⁻¹` 表示延迟、复平面与单位圆 | 想**预测**滤波器行为、或滤波器爆炸想搞清为什么时 |
| [[延迟线 delay line]] 与 [[插值]] | 线性插值（初中数学） | 立刻 |
| [[FFT 与 STFT]] | 复数、欧拉公式 | 做频域效果或频谱显示时 |
| [[过采样 oversampling]] / [[动态范围处理]] | 多速率基本概念 / 对数、dB、指数平滑 | 做失真、饱和、压缩器时 |
| [[物理建模]] | 微分方程、数值积分 | **很久以后** |
| 神经网络音频 | **线性代数** | 你的强项，见 [[MOC - AI Audio]] |

> [!tip] 你只需要理解到"能看懂"的深度
> 对 z 变换，目标不是"能推导"，而是：① 看到 $H(z)$ 知道它描述一个滤波器；② 知道 $z^{-1}$ 就是"延迟一个采样"；③ 知道极点跑出单位圆就会发散。**这三条足够你读完 [[MOC - DSP]] 里的绝大多数内容**；完整推导等你要做滤波器设计或读论文时再补。
>
> [!note] 关于"线性代数没问题"这件事
> 它的实际含义是：**多声道 / 空间音频**（Ambisonics、波场合成，本质都是矩阵运算）；**反馈延迟网络 FDN**（混响的核心是一个反馈矩阵，见 [[反馈延迟网络 FDN]]）；**神经网络音频**（实时推理就是矩阵乘法，见 [[MOC - AI Audio]]）；**自适应滤波**（LMS 的推导是向量内积与梯度，见 [[自适应滤波 LMS 与 RLS]]）。
> **你的数学缺口是"复数 + z 变换"这一小块，不是"数学"整体**——一个很具体的、两三个周末能补上的洞。

> [!warning] 但有一个例外
> 做**合成器**（振荡器抗混叠、滤波器稳定性）或**物理建模**，数学门槛会显著上升，且很难"用到再学"。**建议先做效果器**——效果器的正确性容易验证（输入输出对比），合成器难。

## 练习项目清单

由易到难，每条都能独立完成，且都有明确的验证方式。

| # | 做什么 | 验证什么 |
|---|---|---|
| 1 | 写函数 `dbToGain(dB)`，打印 -6 / 0 / +6 的结果 | 得到 0.501 / 1.0 / 1.995 —— **记住 -6 dB ≈ 一半** |
| 2 | 把 WAV 音量降低 6 dB，用 Python 验证峰值确实是原来的一半 | WAV 读写正确；钳制没出错 |
| 3 | 给上题加淡入淡出（前 100 ms 从 0 升到 1） | 首尾无跳变；用 Python 画前 5000 个采样 |
| 4 | 手写环形缓冲区，写 1..20 进 8 格缓冲，验证 `readDelayed(3)` | 取模与负数下标处理正确 |
| 5 | 用环形缓冲区做 100 ms 固定延迟，听 `in.wav` | 能听出明确回声；用 Python 找脉冲位置验证延迟量 |
| 6 | 把延迟改成 100.5 个采样（分数延迟），对比插值前后的声音 | 插值正确；听高频差异，见 [[插值]] |
| 7 | 实现一阶低通，截止 1000 Hz，喂白噪声 | FFT 看曲线：-6 dB/oct，1000 Hz 处约 -3 dB |
| 8 | 实现 Biquad 低通，用手算系数和代码输出对比 | 系数公式抄对了，见 [[Biquad 滤波器]] |
| 9 | 做一个扫频滤波器（截止 200 Hz → 8000 Hz），再做参数平滑版 A/B 对比 | 听有没有阶梯感/咔哒声——有就说明需要 [[参数平滑 parameter smoothing]]；平滑后消失 |
| 10 | 实现峰值检测器并打印包络曲线 | 为压缩器铺路，见 [[包络跟随器 envelope follower]] |
| 11 | 用检测器做一个固定阈值的硬膝压缩器 | 超过阈值时增益下降；用 Python 画输入输出曲线 |
| 12 | 写 impulse 响应测试：喂单位脉冲，输出到文件 | 滤波器稳定（衰减到 0）；这是所有 DSP 的第一测试 |
| 13 | 用 JUCE 做空插件（不改音频），在 DAW 里加载出声 | 整条工具链打通——**这一步的产出比前 12 步加起来都重要** |
| 14 | 把练习 9 的扫频滤波器搬进 JUCE，加一个旋钮控制 | 第一次听到"自己的 DSP + 自己的界面" |

> [!tip] 每完成一个练习，写一页笔记
> 不是写"我学会了 X"，而是写**你踩到的坑**，打上 `#gotcha` 标签。
> 见 [[2026-10-14 Obsidian 链接名不能含斜杠]] 那个例子——那种"设计带来的盲区"才是知识库里最值钱的内容。

## 常见卡点与解法

| 卡点 | 一句实用建议 |
|---|---|
| **编译 / 链接错误** | 编译错误**永远从输出的第一行读起**（一个缺失的分号能报出 200 行）。链接错误（linker error）不是语法问题，是"找不到实现"或"实现了两次"：函数声明了没定义？`.cpp` 忘了加进构建？头文件里定义了函数？ |
| **段错误（segfault）** | 99% 是访问了不该访问的内存（空指针、越界、用了已释放的对象）。**用 `-fsanitize=address` 重编译**，见 [[AddressSanitizer]] |
| **浮点精度 / 越界** | `float` 只有约 7 位有效数字——**滤波器内部状态、长时间累加用 `double`**。`std::vector::operator[]` **不做边界检查**，调试用 `.at()` 或 ASan |
| **头文件与实现分离 / 构建系统** | **声明放 `.h`，定义放 `.cpp`**；头文件里只放 `inline` 函数和类定义。构建系统：抄一个能用的模板改路径和文件名，**别从零写 CMakeLists**（见 [[CMake 基础]]） |
| **符号约定 / 类型混用** | 不同资料的差分方程符号约定不同，抄公式前先确认（见 [[Biquad 滤波器]]）；`size_t` 无符号，`for (int i = v.size() - 1; i >= 0; --i)` 是死循环陷阱 |
| **Debug 能跑，Release 崩** | 未定义行为（UB）的典型特征。**UB 不是"随机"，是"编译器可以随便处理"**，见 [[UndefinedBehaviorSanitizer]] |
| **宿主里行为不同 / 改参数就爆音** | 先把同一个二进制当 Standalone 跑，分流"宿主交互问题"还是"DSP 问题"；拖动参数爆音 → 参数平滑，见 [[参数平滑 parameter smoothing]] |

> [!danger] 特别警告：AI 生成的 C++ 代码对新手特别危险
> 原因不是"AI 写得差"，而是**它的失败模式恰好对新手最不友好**：
>
> | 失败模式 | 为什么新手抓不住 |
> |---|---|
> | **能编译、能出声、但逻辑错** | 比如 Biquad 的 `A = 10^(dB/40)` 写成 `/20`——声音"有变化"，听起来"像那么回事"，但增益差一倍。**没有对照基准就发现不了** |
> | **违反实时契约** | AI 默认写出"教科书 C++"：`std::vector::push_back`、`std::mutex`、`std::string`、`printf`。这些在普通程序里完全正确，在 [[实时音频线程契约]] 里全是禁忌。它**不会主动告诉你** |
> | **用你听不懂的写法 / 接口是编的 / 过度设计** | 模板、lambda 捕获、`auto&&`——代码能跑，但你改不动也 debug 不了；方法名看着合理但根本不存在；你要一个增益，它给你一个带策略模式的 `GainProcessorFactory` |
>
> **防御办法**（缺一不可）：① **每一行都要能解释**，解释不了的行删掉重写，或让 AI 逐行讲解到你能复述；② **让它遵守 [[实时音频线程契约]]**，提示词里明确写"音频线程内不得分配、加锁、打日志、抛异常"；③ **用测试验证而不是用编译验证**——"能编译"和"能出声"都不是正确性证据；④ **DSP 核心逻辑自己写**（见下一节）；⑤ **查 API 是否存在**，编译一次就知道，别在脑子里推理。
> 更完整的清单见 [[AI 生成代码的审查清单]]、[[为什么 AI 写不好实时音频代码]]。

## 关于"用 AI 辅助"的正确姿势

你想用 AI/Agent 写代码，这是对的——但**分工搞错会毁掉整条路线**。

**让 AI 做最划算的事**：
| 任务 | 为什么划算 |
|---|---|
| **写 Python 分析脚本** | FFT、画图、扫频生成、对比两个文件——"我懂要什么但不想查 API"的活，省 80% 时间，且错了立刻能看出来 |
| **解释报错 / 解释不熟悉的语法** | 把编译器输出整段贴给它；问 `const auto&` 是什么意思、`override` 干什么用的——比翻书快 |
| **写测试用例与边界输入** | 让它生成"喂 0 长度缓冲区""喂 NaN""喂超范围参数"这类用例，你判断结果对不对 |
| **写构建配置与样板代码** | CMakeLists、插件骨架、状态序列化——没有学习价值，抄就行 |
| **当"源码导游" / 审查实时安全性** | 问它"`prepareToPlay` 会被调用几次""这个类的生命周期是什么"（见 [[用 AI 读懂 JUCE 源码]]）；或把 `processBlock` 贴给它问"这里有没有分配、加锁、阻塞" |

> [!important] DSP 核心逻辑必须自己写
> 原因不是道德，是**功能性**的：**你需要建立直觉，否则你无法调试。**
>
> 音频 bug 的表现形式是"听起来不对"。当混响尾巴里有金属味、当压缩器在鼓上抽气、当扫频时有阶梯感——**没有任何编译器或测试会告诉你原因**。
> 你只能靠"我知道这个滤波器应该长什么样"来判断。
>
> 如果 DSP 是 AI 写的，你手上就只有一个黑盒。当它出问题时（一定会），你的调试手段只剩下"把代码贴回给 AI，让它猜"——它会猜错，而且你没法判断它猜错了。
> **你的耳朵是你唯一的优势，而耳朵只有配上"知道代码在干什么"才有用。**

**必须自己写**：所有滤波器、延迟线、检测器的实现；参数怎么映射到 DSP 内部（范围、曲线、单位）；平滑时间常数的选择；信号流的拓扑（先滤波还是先饱和？侧链从哪取？）。**可以让 AI 写**：测试脚本、绘图、构建配置、UI 布局样板、状态序列化的代码。

**为什么"能跑但不懂"的代码在音频领域特别危险**——普通 CRUD 程序里，一段不懂的代码最多是"以后维护麻烦"。音频插件里，它会导致三类你在别处遇不到的问题：

1. **实时契约违规不会立刻报错。** 在音频线程里 `push_back` 一个 vector，在你的 M2 上、3 个音轨的测试工程里**完全听不出问题**。它在用户的旧机器上、40 个音轨的工程里爆音。见 [[实时音频线程契约]]。
2. **DSP 的错误往往"听起来是对的"。** 系数差一倍、符号抄反、平滑时间常数差 10 倍——这些都会产生"确实变了声音"的结果。**只有对照理论值或参考实现才能发现。**
3. **音频的 bug 报告是主观的。** "听起来很塑料""尾巴不自然""压缩器不懂鼓"——用户无法给你可复现的步骤，你只能靠理解代码来定位。

> [!note] 建议的协作模式
> 参见 [[_meta/open-questions]] Q8：**用"结对"模式起步**——你设计 + 写 DSP，Agent 写测试 + 解释 + 审查。不要用"代笔"模式，那样你三个月后会有一个自己看不懂的插件，和一个被 AI 自言自语污染的知识库。

## 相关

- [[从音乐制作人到插件开发者]] — 你的知识盘点与缺口地图，本页是它的执行版
- [[_meta/roadmap]] — 项目级路线图（本页是**学习**路线，那一页是**项目**路线）
- [[MOC - Frameworks & Toolchain]] · [[MOC - DSP]] · [[MOC - Realtime Engineering]] · [[MOC - UI & UX]]
- [[实时音频线程契约]] · [[参数平滑 parameter smoothing]] · [[Biquad 滤波器]] · [[denormal 数处理]] · [[音频缓冲区 buffer 与 block size]]
- [[插件格式对比]] · [[ADR-002 选择框架]] · [[AI 辅助 C++ 音频开发的真实效果]]

> [!note] 待补充
> - **时间估算的实测校准**：本页所有小时数是判断而非测量。等你走完阶段 0–2，把实际耗时填回来，这张表才有资格从 `seed` 升到 `solid`
> - **阶段 1 是否该独立成阶段 / 阶段 2–3 之间要不要加"Python 原型"阶段**：指针与内存对计算机专业背景的人可能 3 小时就通；而先用 numpy 写一遍 DSP 再移植到 C++ 可能更快建立直觉，代价是稀释"用 C++ 做事"的训练量。两者都需要实测才知道
> - **CMake 该在哪一阶段引入**：本页推到阶段 4，但阶段 2 手写 `clang++ a.cpp b.cpp -o out` 在多文件时很痛苦。哪个更优未验证
> - **AI 辅助学习的提示词模板**：本页只给了分工原则，没给可复用的提示词；应在实践中积累一套，见 [[Agent 驱动的插件开发工作流]]
