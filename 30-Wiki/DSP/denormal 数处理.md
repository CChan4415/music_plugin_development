---
title: denormal 数处理
type: wiki
domain: dsp
status: solid
confidence: high
sources: ["[[Bencina - Real-time audio programming 101]]"]
tags: [gotcha, cpp, recipe]
created: 2026-10-14
updated: 2026-10-14
---

# denormal 数处理

> [!important] 一句话
> 浮点数小到约 $10^{-38}$ 以下会掉进 **denormal（非规格化数）** 区间。
> 在 x86 上，涉及 denormal 的浮点运算会慢 **10–100 倍**——**这是硬件行为，不是软件 bug**。
> 它由混响/延迟的**反馈路径**天然产生，**只在安静时发作**：你测试时听不出来，CPU 却会飙升。

本库有 10 个页面在「常见坑」里写了「静音时 CPU 飙升 → denormal」，但都只说了"是什么"。本页是那个"怎么办"。

## 一、什么是 denormal

32-bit float 的位：`s eeeeeeee fffffffffffffffffffffff`（符号 1 / 指数 8 位偏置 127 / 尾数 23）

- **normal**：指数位不全为 0，隐含前导 1 → $(-1)^s \times 1.f \times 2^{e-127}$
- **denormal**：**指数位全为 0**，隐含前导变成 **0**，指数固定最小值 → $(-1)^s \times 0.f \times 2^{-126}$

> [!note] 为什么要有 denormal
> 否则最小的 normal 数 $2^{-126} \approx 1.18\times10^{-38}$ 与 0 之间有**巨大空隙**，掉进去的中间结果被截断成 0，导致 $a \ne b$ 但 $a-b=0$ 这类破坏代数性质的行为。denormal 用等间距的数填满空隙，叫**渐进下溢（gradual underflow）**。**它为数值正确性而存在，代价是性能。**

| 名称 | 值 | C 里的写法 |
|---|---|---|
| 最大 normal | $3.4028 \times 10^{38}$ | `FLT_MAX` |
| **最小 normal** | $1.1755 \times 10^{-38}$ | **`FLT_MIN`** |
| 最小 denormal | $1.4013 \times 10^{-45}$（$2^{-149}$） | 无宏，位模式 `0x00000001` |

> [!warning] `FLT_MIN` 不是"最小的 float"
> 它是**最小的规格化正数**。比它更小的正数还有 $2^{23}-1$ 个 denormal。判断"是不是 denormal"用的正是它：`x != 0 && std::abs(x) < FLT_MIN`。

**音频里它从哪来**——不是"算错了"，而是"信号本来就在衰减到 0"：

```cpp
float y = delayLine.read();
delayLine.write (input + y * feedback);   // feedback=0.95 → 每圈 ×0.95，必然穿过 denormal 区
```

| 结构 | 为什么会产生 |
|---|---|
| **反馈延迟 / 混响** | 尾音指数衰减，必然经过 denormal 区 |
| **IIR 滤波器内部状态** | `y1/y2` 无输入时衰减，同样穿过 |
| **包络 / 参数平滑** | `current += (target-current)*coeff` 是**永不精确到达**的指数趋近 |

> [!warning] 第三条最容易被忽略
> **任何一阶平滑器的状态都会进入 denormal 区**，见 [[参数平滑 parameter smoothing]]。

## 二、为什么它慢

CPU 的浮点单元为 normal 数做了高度优化（流水线、单周期乘加）。denormal 的**前导位是 0**，有效位数随数值变小而减少，硬件需要额外的前导零计数、移位、特殊舍入逻辑。x86 的实现是**微码辅助（microcode assist）**：一条浮点指令被拆成一段微码执行，期间**流水线被阻塞**。

> [!important] 这不是"你代码写得不好"
> 换写法、加 `-O3`、换更好的算法**都没用**。唯一的解法是**让 denormal 根本不出现**（第四节）。

**实测（本库，2026-10-14）**，一阶衰减 `y *= g`，clang 21 `-O2`：

| 平台 | denormal ON | FTZ/FZ ON | 比值 |
|---|---|---|---|
| **arm64（本机 M 系列）** | 0.112 s | 0.080 s | **约 1.4×** |
| **x86-64（Rosetta 2 转译）** | 0.095 s | 0.093 s | **约 1.0×** |

> [!warning] 这两个数字都不能外推
> **Rosetta 不可信**：它是二进制翻译层，x86 的微码辅助行为**不会被如实模拟**——测真实 x86 惩罚必须在真 x86 机器或 VM 上。
> **arm64 的 1.4× 也不代表"ARM 没问题"**：ARM 处理 denormal 比 x86 好得多，但**并非零代价**。
>
> **结论：本库无法给出可信的 x86 惩罚倍数。** 文献广泛引用 **10–100 倍**（[[Bencina - Real-time audio programming 101]] 也用这个量级），具体数字取决于 CPU 型号。**你需要的是知道它存在并处理它，而不是记住某个倍数。**

> [!warning] 待验证
> 有说法称 Intel Sandy Bridge 上 `mulps` 遇 denormal 有约 140 周期惩罚；也有说法称 ARM 平台惩罚很小、主要问题是"与 x86 结果不一致"。两条**均未在本库核实**。

## 三、为什么在音频里特别致命

**1. 反馈路径天然产生它。** 混响、延迟、IIR、包络跟随器——**所有带反馈的东西**都在做"指数衰减到 0"，而指数衰减**必然经过 denormal 区**。

**2. 只在安静时出现 —— 这是最坏的组合。** 你以为的测试是"播放鼓 loop → 信号很大 → 没有 denormal → 没问题"；实际用户是"音乐停了，混响尾巴还在响 → 尾巴衰减到 1e-39 → CPU 飙升"。**听不出来**（它不产生可闻声音）、**不报错**（不崩溃不 NaN）、**你的机器太快**（M 系列跑 1 个实例，用户跑 40 个轨）——所以你会去优化算法，而算法根本不是问题。

[[MOC - Realtime Engineering]] 把它列为新手插件故障第 4 名，并注明"表现是性能问题不是错误，你会在优化算法上白花很多时间"。

**3. 尾音不会自己衰减到 0（本库实测发现）。** 一阶衰减 `y *= g`（float32，round-to-nearest）：

| g | 结果 |
|---|---|
| 0.5 | ✅ 到达 0（第 149 步）—— 0.5 是 2 的幂，中点恰好舍入到 0 |
| 0.75 / 0.9 / 0.99 / 0.999 | ❌ 分别卡在 2.80e-45 / 5.61e-45 / 7.01e-44 / 7.01e-43 |

**机制**：设最小 denormal $s = 2^{-149}$。$s \times 0.9 = 1.26\times10^{-45}$，比 $s/2$ 大，按 round-to-nearest 又舍回 $s$。**乘任何 $g > 0.5$ 都跳不出这个不动点。**

真实反馈延迟（50 ms 梳状，float32）同样成立——**g = 0.80 / 0.90 / 0.95 / 0.99 时全部"永不归零"**，最终 buffer 最大值分别为 2.80e-45 / 5.61e-45 / 1.26e-44 / 7.01e-44，进入 denormal 的时间为 19.6 / 41.5 / 85.2 / 434.5 秒。

> [!important] 这条发现改变了两件事
> **1. "等它自己衰减到 0 就好了"是错的。** 音乐停止 20 秒后反馈环里仍有 denormal 在循环——**只要插件还挂着，CPU 就一直在付这个代价**。
> **2. 这给了你一个免费的检测信号**：应该静音时反馈 buffer 不为 0，就是抓到了它（第六节）。
>
> 注意这是**实测现象不是定理**：它依赖 round-to-nearest（IEEE 默认）和具体的 $g$。

**4. 多久进入 denormal 区？** 从满量程到 `FLT_MIN` 是 $20\log_{10}(1.1755\times10^{-38}) \approx -758.6$ dB，所以：

$$\boxed{t_{\text{denormal}} \approx \frac{758.6}{60} \times \mathrm{RT60} \approx 12.6 \times \mathrm{RT60}}$$

实测（50 ms 梳状，float32）：g = 0.80/0.90/0.95/0.99 时预测 19.50/41.30/84.84/433.0 s，实测 19.61/41.45/85.16/434.5 s，**偏差均 < 0.5%**。

> [!tip] 实用含义
> **RT60 = 2 秒的混响 → 约 25 秒后进入 denormal 区。** 即"一首歌放完、尾巴响过 25 秒之后，你的插件开始变慢"——这个时间尺度和"用户切歌、走开喝咖啡"完全重合，**所以极难在开发中复现**。

## 四、四种解决方案

> [!note] 先给结论
> **生产代码用「FTZ/DAZ + 检测清零」组合。** 偏置法简单但引入 DC；`-ffast-math` 不要用。

### 方案 1：加极小直流偏置

```cpp
class CombFilter {
public:
    float process (float x) noexcept {
        const float y = buffer[index];
        //                              ↓ 这就是防 denormal 偏置
        buffer[index] = x + y * feedback + kAntiDenormal;
        if (++index >= kSize) index = 0;
        return y;
    }
private:
    static constexpr float kAntiDenormal = 1.0e-20f;  // 远大于 FLT_MIN，远小于音频
    static constexpr int   kSize = 1117;              // 互质延迟，见 [[混响的原理]]
    float buffer[kSize] {};
    int   index = 0;
    float feedback = 0.95f;
};
```

`1e-20` 比 `FLT_MIN` 大 $10^{18}$ 倍，比 24-bit LSB（$1.19\times10^{-7}$）小 $10^{13}$ 倍——两头都留足余量。

> [!warning] 代价：偏置会在反馈环里被放大成 DC
> 稳态直流增益是 $1/(1-g)$。实测（g=0.95，50 ms 延迟）：偏置 `1e-20` → 稳态 DC 2.0e-19（**-374 dBFS**）；`1e-15` → -274 dBFS；`1e-8` → 2.0e-7（**-134 dBFS** ⚠️）。
> `1e-20` 完全无害，但**图省事写 `1e-8` 会得到 -134 dBFS 的直流**——已接近 24-bit 噪声底（-138.5 dBFS）。**偏置值不是"随便取个小数"。**

**取舍**：一行、无分支、不会漏、对 SIMD 友好；代价是引入 DC，且每个反馈环都要记得加。

### 方案 2：检测并清零

```cpp
#include <cmath>

inline float flushDenormal (float x) noexcept
{ return (std::abs (x) < 1.0e-30f) ? 0.0f : x; }

// 用在反馈状态上（⚠️ 只清状态变量，不清输出 —— 清输出会在尾音里产生"台阶"）
float y = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2;
y1 = flushDenormal (y);
y2 = flushDenormal (y1);

// 无分支版本：利用"denormal 的指数位全为 0"
#include <cstring>
inline float flushDenormalBits (float x) noexcept {
    std::uint32_t bits;
    std::memcpy (&bits, &x, sizeof (bits));
    // 指数位非零 → normal/0/Inf/NaN → 原样返回；全零 → denormal → 0
    return (bits & 0x7f800000u) ? x : 0.0f;
}
```

**取舍**：不引入 DC、精确、可只作用于特定信号；代价是多一次比较，且阈值选错会误清正常小信号。

> [!warning] 无分支不一定更快
> 它需要在**浮点寄存器和整数寄存器之间搬数据**，ARM 上这个搬运有明确成本。**先写分支版本，测出来是瓶颈再换。** 而且音频里这个分支**几乎 100% 预测正确**（尾音期间一直走同一分支），代价本来就小。

> [!tip] 阈值怎么选
> **不要用 `FLT_MIN` 当阈值**——那样只在**已经**进入 denormal 之后才清零，而你要避免的是"进入之后的那次运算"。用大几个数量级的值（如 `1e-30`）留安全余量。`1e-30` 以下的信号**在任何位深下都不可闻、不可测**。

### 方案 3：编译选项（⚠️ 破坏 IEEE 语义）

```bash
-ffast-math          # GCC / Clang：把 denormal 当 0 处理
```

文献示例（纯衰减循环，x86）：默认 3.82 s → `-O3` 3.46 s → **`-O3 -ffast-math` 0.02 s（约 190×）**。

> [!danger] 不要用在 DSP 代码上
> 它打开的不只是 denormal 处理，而是一整套"假设浮点满足实数代数律"的优化：
>
> | 允许编译器 | 后果 |
> |---|---|
> | 假设没有 NaN / Inf | **你写的"检测 NaN 并复位"保护会被静默删掉** |
> | 重排浮点运算顺序 | 结果**不可复现**，null test 失效 |
> | `a*b + a*c` → `a*(b+c)` | 数值行为改变 |
>
> 本库立场（与 [[实时音频线程契约]] 一致）：**用方案 1 或 2，保留 IEEE 语义。**

> [!warning] 待验证：`-ffast-math` 并不修改 FPCR
> 实测：**`-ffast-math` 在本机（arm64 clang 21）不会修改 FPCR 的 FZ 位**——编译后运行时读 FPCR 仍是 `0x0`。它的效果来自**编译期优化**，而不是"帮你打开了 FTZ"，这与很多人的直觉不符。**仅在本机验证过。**

### 方案 4：平台特定的 FTZ / DAZ（推荐）

- **x86** — `MXCSR`：`FTZ`（bit 15）刷 denormal **输出**；`DAZ`（bit 6）把 denormal **输入**当 0
- **ARM (AArch64)** — `FPCR`：`FZ`（bit 24）**同时**管输入和输出

> [!important] 跨平台的关键差异（本页最实用的一段）
> | | x86 | ARM (AArch64) |
> |---|---|---|
> | 寄存器 | `MXCSR` | `FPCR` |
> | 读 / 写 | `_mm_getcsr()` / `_mm_setcsr()` | `mrs x, FPCR` / `msr FPCR, x` |
> | 输出刷零 | `FTZ` bit 15 | `FZ` bit 24 |
> | 输入刷零 | `DAZ` bit 6（**独立**位） | `FZ` bit 24（**同一个**位） |
> | mask | `(1<<15) \| (1<<6)` | `(1<<24)` |
> | 作用范围 | **仅 SSE/AVX**（x87 不受影响） | 标量 + Advanced SIMD 都受控 |
>
> **最容易写错的地方**：ARM 上**只有一个 FZ 位**同时管输入和输出。照抄 x86 的 `(1<<15)|(1<<6)` 到 ARM 会设错位（bit 6 在 FPCR 里是别的含义）。
> 另注：ARMv8 后来加了 `FEAT_AFP`，提供独立的 `FIZ`（bit 0）对应 x86 的 DAZ，但它是**可选特性**，不要依赖。

```cpp
// ─────────  denormal.h —— 跨平台 FTZ/DAZ 控制  ─────────
#pragma once
#include <cstdint>

#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
  #include <xmmintrin.h>
  #include <pmmintrin.h>
  using FpControl = std::uint32_t;
  inline FpControl fpGet() noexcept { return _mm_getcsr(); }
  inline void      fpSet (FpControl v) noexcept { _mm_setcsr (v); }
  inline FpControl denormalMask() noexcept { return (1u << 15) | (1u << 6); }  // FTZ | DAZ
#elif defined(__aarch64__) || defined(_M_ARM64)
  using FpControl = std::uint64_t;
  inline FpControl fpGet() noexcept
  { FpControl v; __asm__ __volatile__ ("mrs %0, FPCR" : "=r" (v)); return v; }
  inline void fpSet (FpControl v) noexcept
  { __asm__ __volatile__ ("msr FPCR, %0" :: "r" (v)); }
  inline FpControl denormalMask() noexcept { return (1ull << 24); }            // FZ
#endif

// RAII：进入作用域开启，离开时恢复原值（不是关掉）
class ScopedNoDenormals {
public:
    ScopedNoDenormals() noexcept : saved (fpGet()) { fpSet (saved | denormalMask()); }
    ~ScopedNoDenormals() noexcept { fpSet (saved); }
    ScopedNoDenormals (const ScopedNoDenormals&) = delete;
    ScopedNoDenormals& operator= (const ScopedNoDenormals&) = delete;
private:
    FpControl saved;
};
// 用法：processBlock 第一行 → const ScopedNoDenormals noDenormals;
```

**取舍**：零运行时代价、覆盖整个 block、真正的"根治"；代价是平台相关代码，且必须恢复原值。

> [!warning] 必须"恢复原值"，不能"关掉"
> `MXCSR` / `FPCR` 是**每线程**的寄存器状态，而音频线程可能被宿主复用。**改了不恢复，会影响同线程上跑的其他代码**（包括宿主自己的）。RAII 保存/恢复是唯一安全的做法。**用 JUCE 的话直接用自带的 `juce::ScopedNoDenormals`**（在 `juce_core` 里）；本页代码是为了让你看懂它在做什么。

## 五、跨平台注意

你的机器是 **Apple Silicon (arm64)**，要兼容 **Windows (x86-64)**。三个坑：

> [!important] ① 开发机上看不到问题（你最大的风险）
> 本机 arm64 实测约 **1.4×**，而 x86 公开数据是 **10–100×**。**你在 Mac 上跑 40 个混响实例可能毫无压力，用户在同一份代码的 Windows 机器上会爆音。**
> 对策：**denormal 处理必须是代码里的显式逻辑，而不是"等测出来再说"。**
>
> **② mask 位不同** — x86 是 `(1<<15)|(1<<6)`，ARM 是 `(1<<24)`，抄错就静默失效。
> **③ 结果会不一致** — 开 FTZ 后刷零的**时机和范围**两边定义不同，**逐 bit 一致仍无保证**。

```cpp
// 自检：开启后，一个 denormal 运算应该返回 0
static bool verifyFlushToZeroWorks() noexcept {
    ScopedNoDenormals guard;
    const volatile float tiny = 1.0e-40f;      // volatile 防常量折叠
    return (tiny * 1.0f) == 0.0f;
}
```


> [!warning] 这个自检**可能失败，而且失败是正常的**
> `1e-40f` 在编译期就可能被折叠。加 `volatile` 能缓解，但不保证。更可靠的做法是运行时**从一个不会被优化掉的来源**产生 denormal（比如让真实反馈环跑几千次）。**不要把自检失败当成"平台不支持"。**

## 六、怎么检测

> [!tip] 最有辨识度的特征
> **CPU 占用与信号电平反相关。** 正常：声音大 → CPU 高。denormal：**声音没了 → CPU 反而更高**。这个特征非常独特，见过一次就不会再误判。

```cpp
// 调试期：统计（不要用 assert，会刷屏）
inline float checkDenormal (float y) noexcept {
   #ifndef NDEBUG
    static std::uint64_t count = 0;
    if (y != 0.0f && std::abs (y) < FLT_MIN && (++count % 100000 == 1))
        std::fprintf (stderr, "⚠️ denormal 出现 %llu 次, 值 = %g\n",
                      (unsigned long long) count, (double) y);
   #endif
    return y;
}

// 最实用的检测器：利用第三节第 3 条的实测现象
bool isTailTrulySilent (const float* buffer, int size) noexcept {
    for (int i = 0; i < size; ++i)
        if (buffer[i] != 0.0f) return false;   // 有非零值 = 有 denormal 在循环
    return true;
}
```

> [!important] 为什么这个检查特别有价值
> **正确的实现返回 `true`，错误的实现返回 `false`**——这是一个**布尔结果**，不是"看起来快不快"。可以写成自动化测试，**不需要真机器、不需要 profiler、可以进 CI**：`assert np.all(tail == 0.0), "尾音没有归零 → 反馈环里有 denormal"`。

```python
# Python 复现：几秒钟跑 10 万步，直接看中间值
import numpy as np
y = np.float32(1.0)
for _ in range(100_000):
    y = np.float32(y * np.float32(0.9))
    if y == np.float32(0.0): break
print("卡住的值:", y)      # → 5.605194e-45   ← 这就是 denormal
```

## 七、AI 会怎么写错

> [!important] 这是本页最实用的一节
> AI **通常完全不知道 denormal 这回事**。这不是它"写错了"，而是**它的训练数据里 99% 的 C++ 代码不是音频 DSP 代码**，而 denormal 只在音频里才是问题。
> **所以 AI 一定会写出"干净的反馈路径"**——逻辑完全正确、数学完全正确、在开发机上跑得完全正常，然后在用户的 Windows 机器上安静时卡死。

| # | AI 常写 | 为什么错 | 怎么查 |
|---|---|---|---|
| 1 | **反馈路径完全没有任何 denormal 处理** | 这是默认行为，AI 不会主动加 | grep 反馈写回那一行有没有 `+1e-20f` 或 flush |
| 2 | `if (y < 1e-30f) y = 0;` | **忘了负数**！denormal 有正有负 | 查有没有 `std::abs()` |
| 3 | 用 `1e-8f` 当偏置 | 反馈环里放大成 **-134 dBFS 的 DC** | 算 `bias/(1-feedback)` 折合多少 dBFS |
| 4 | 在**输出**上清零而非**状态** | 尾音里产生可闻的**台阶** | 看清零作用在哪个变量上 |
| 5 | 只处理了 Biquad，忘了延迟线/混响 | 每个反馈结构都要单独处理 | 数有几个反馈环，是不是每个都有 |
| 6 | 用 `-ffast-math` 当"解决方案" | 破坏 IEEE 语义，可能删掉 NaN 检测 | 查 CMakeLists 有没有 `-ffast-math` |
| 7 | 写了 `_mm_setcsr` 但**不恢复** | 污染同线程其他代码的浮点状态 | 查是否用 RAII 保存/恢复 |
| 8 | 把 x86 的 `(1<<15)\|(1<<6)` 抄到 ARM | ARM 只有一个 FZ 位（bit 24） | 检查两个 `#if` 分支的 mask |
| 9 | 在 `processBlock` 里**每样本**调 `_mm_getcsr()` | 读写控制寄存器有成本且没必要 | 查 Scoped 是否在循环外 |
| 10 | 假设"尾音会自己衰减到 0" | 实测证明**不会**（非 2 的幂的 g 会卡住） | 见第三节第 3 条 |

> [!tip] 第 1 和 10 条是同一个认知缺口
> AI 的心智模型是"浮点能表示任意小的数，衰减就是趋向 0"。**真实情况是：浮点有下限，而且衰减会卡在下限上。** 你只要在 prompt 里点出这一点 AI 就能写对——**但前提是你自己知道。**

```
这段代码是反馈延迟/混响。请检查并修复 denormal：
1. 反馈状态无输入时会衰减到 1e-38 以下，进入 denormal 区
2. x86 上这让运算慢 10-100 倍，且只在安静时出现
3. 用「跨平台 FTZ/DAZ（RAII 保存恢复）+ 反馈状态清零」解决
4. ARM 的 FPCR.FZ 是 bit 24（同时管输入输出）；
   x86 的 MXCSR 是 FTZ bit 15 + DAZ bit 6（分开的）
5. 不要用 -ffast-math；清零时不要忘记负数（用 std::abs）
```

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| **安静时 CPU 飙升** | 反馈尾音进入 denormal | FTZ/DAZ + 状态清零（第四节） |
| 加偏置后出现直流/低频嗡声 | 偏置太大（如 `1e-8`），被 $1/(1-g)$ 放大 | 用 `1e-20`；或改用检测清零 |
| 清零后尾音有"台阶"感 | 在**输出**上清零而非状态 | 只清反馈状态变量 |
| Mac 上没问题，Windows 用户爆音 | ARM 惩罚小（实测 1.4×），x86 大 | **代码里显式处理，不要靠测** |
| FTZ 设了但没效果 | mask 位写错（ARM 抄了 x86 的） | 核对 `(1<<24)` vs `(1<<15)\|(1<<6)` |
| 宿主里其他插件行为异常 | 改了 MXCSR/FPCR 没恢复 | 用 RAII，恢复**原值** |
| `-ffast-math` 后 NaN 检测失效 | 编译器假设无 NaN，删掉了分支 | 去掉 `-ffast-math` |
| 尾音"永不消失"，CPU 一直高 | 实测现象：g 非 2 的幂时卡在最小 denormal | 必须显式清零 |
| 单精度没问题，双精度也有 | double 的 denormal 阈值是 $2.2\times10^{-308}$ | 同样处理，`FLT_MIN` 换成 `DBL_MIN` |

## 九、怎么验证

> [!important] 数值验证优先于听感
> denormal **不产生声音**，所以"听"是完全无效的验证手段。

| # | 验证什么 | 方法 | 通过标准 |
|---|---|---|---|
| 1 | **尾音是否归零** | 喂脉冲，跑足够长，检查尾音 | `np.all(tail == 0.0)` |
| 2 | **需要跑多久** | $t \approx 12.6 \times \mathrm{RT60}$ | RT60=2s → 跑 30 秒以上 |
| 3 | FTZ/DAZ 是否生效 / 清零是否漏了负数 | `verifyFlushToZeroWorks()`；再喂**负**脉冲重复测试 1 | 返回 `true`；同样归零 |
| 5 | 偏置是否引入 DC | 无输入跑 60 秒，测输出均值 | < -200 dBFS |
| 6 | CPU 是否与电平反相关 | profiler 长录，看安静段 | 安静段不高于响段 |
| 7 | 跨平台一致性 | 两平台跑同一 null test | 差异 < -100 dB，见 [[音频测量基础]] |

```python
import sys, numpy as np
sys.path.insert(0, '50-Playground/tools')
from audio_io import impulse, peak_db

h = my_reverb.process(impulse(int(48000 * 60)))            # 60 秒虚拟时间
tail = np.asarray(h[int(48000 * 40):], dtype=np.float32)   # ← float32 是必须的
print(f"尾音峰值: {peak_db(tail):.1f} dB")
print(f"尾音精确为 0? {np.all(tail == 0.0)}")               # ← 关键断言
```

> [!warning] 必须用 `float32` 测，不能用 numpy 默认的 `float64`
> **这是本页最容易犯的验证错误。**
> - `float64` 的 denormal 阈值是 $2.2\times10^{-308}$，**比 float32 低 270 个数量级**
> - 用 `float64` 跑，尾音一路衰减到 $10^{-300}$，你**永远看不到"卡住"的现象**
> - 而插件里用的是 `float`（32-bit），**行为完全不同**
>
> 同理，`50-Playground/tools/audio_io.py` 内部统一用 `float64`（为了测量精度），**所以不能直接用它测 denormal**——要先把数组转成 `float32` 再做衰减运算。

> [!note] 我的判断
> 1. **denormal 处理是"必须有"，不是"优化项"**，和"反馈增益必须钳制"同级。
> 2. **写每个反馈结构时立刻加上**——因为在 Mac 上你测不出来。
> 3. **优先用 `juce::ScopedNoDenormals`**；本页代码用于理解原理和 JUCE-free 场景。
> 4. **把"尾音归零"写成自动化测试放进 CI**——这是唯一能在开发机上抓到这个 bug 的方法。
> 5. 文献里"10–100 倍"**本库未能独立验证**。**但"必须处理"的结论不受影响**——即使只有 1.4×，也没人想为一个纯 bug 付这个代价。

## 相关

- [[实时音频线程契约]] — 本页是它禁止清单最后一行那条 denormal 规则的展开
- [[Biquad 滤波器]] · [[混响的原理]] · [[延迟与回声的原理]] · [[延迟线 delay line]] · [[反馈延迟网络 FDN]]
- [[参数平滑 parameter smoothing]] — 一阶平滑器的状态**也**会进入 denormal 区
- [[动态处理的原理]] — 检测器与平滑器同理
- [[浮点音频表示]] · [[浮点确定性与可复现性]] · [[浮点异常]] — 相邻的浮点话题
- [[性能剖析]] · [[SIMD]] · [[Python 优先的 DSP 学习路径]]
- [[MOC - DSP]] · [[MOC - Realtime Engineering]]

> [!note] 待补充
> - **在真 x86 机器上实测 10–100 倍这个数字**（本库只有 Rosetta 数据，不可信）
> - 不同 x86 微架构（Nehalem / Sandy Bridge / Skylake / Zen）的惩罚差异
> - Apple Silicon 各代（M1/M2/M3/M4）的 denormal 行为是否一致
> - MSVC 的 `/fp:fast` 是否也影响 FTZ；JUCE `ScopedNoDenormals` 的确切位掩码
> - SIMD 路径下 denormal 惩罚是否与标量相同
> - 是否应该在 `releaseResources` 里恢复浮点控制寄存器
