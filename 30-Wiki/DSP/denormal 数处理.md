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
> 当浮点数小到 $10^{-38}$ 以下，它会掉进 **denormal（非规格化数）** 区间。
> 在 x86 上，涉及 denormal 的浮点运算会慢 **10–100 倍**，而且是**硬件行为，不是软件 bug**。
>
> **它在混响/延迟的尾音里几乎必然出现，只在安静时发作**——所以你测试时听不出来，CPU 却会飙升。
> 这是 [[实时音频线程契约]] 里唯一一条**关于数值而非关于线程**的铁律。

## 为什么这一页被 10 个页面引用

本库的 [[Biquad 滤波器]]、[[混响的原理]]、[[延迟与回声的原理]]、[[动态处理的原理]]、
[[合成原理与 DSP 拓扑]]、[[反馈延迟网络 FDN]]、[[延迟线 delay line]]、
[[实时音频线程契约]]、[[MOC - Realtime Engineering]]、[[C++ 零基础到音频 DSP 路线]]
都在「常见坑」里写了同一行：**静音时 CPU 飙升 → denormal**。

因为这一行只说了"是什么"，没说"怎么办"。本页就是那个"怎么办"。

---

## 一、什么是 denormal

### IEEE 754 的位布局

32-bit float（binary32）的位是：

```
s eeeeeeee fffffffffffffffffffffff
│ └──┬───┘ └──────────┬──────────┘
│    │                └── 尾数（23 bit）
│    └── 指数（8 bit，偏置 127）
└── 符号位
```

**normal（规格化）数**：指数位不全为 0，隐含前导 1，值 = $(-1)^s \times 1.f \times 2^{e-127}$

**denormal（非规格化）数**：**指数位全为 0**，隐含前导变成 **0**，指数固定为最小值：

$$x = (-1)^s \times 0.f \times 2^{-126}$$

> [!note] 为什么要有 denormal 这个设计
> 如果没有它，最小的正 normal 数 $2^{-126} \approx 1.18 \times 10^{-38}$ 和 0 之间会有一个**巨大的空隙**。
> 任何掉进这个空隙的中间结果都会被直接截断成 0，导致 $a \ne b$ 但 $a - b = 0$ 这类破坏代数性质的行为。
> denormal 把这个空隙用**等间距**的数填满，这叫**渐进下溢（gradual underflow）**。
>
> **它是为了数值正确性而存在的，代价是性能。**

### 关键数值（float32）

| 名称 | 值 | C 里的写法 |
|---|---|---|
| 最大 normal | $3.4028 \times 10^{38}$ | `FLT_MAX` |
| **最小 normal** | $1.1755 \times 10^{-38}$ | **`FLT_MIN`** |
| 最小 denormal | $1.4013 \times 10^{-45}$（$2^{-149}$） | 无宏，位模式 `0x00000001` |
| 机器 epsilon | $1.1921 \times 10^{-7}$ | `FLT_EPSILON` |

> [!warning] `FLT_MIN` 不是"最小的 float"
> 这是 C 语言最坑的命名之一。`FLT_MIN` 是**最小的规格化正数**，不是最小可表示的数。
> 比它更小的正数还有 $2^{23} - 1$ 个 denormal。
> **判断"是不是 denormal"用的正是 `FLT_MIN`**：`0 < |x| < FLT_MIN`。

### 音频里它从哪来

**不是"算错了"，而是"信号本来就在衰减到 0"**：

```cpp
// 一个最普通的反馈延迟
float y = delayLine.read();
delayLine.write (input + y * feedback);
```

`feedback = 0.95` 时，每圈乘 0.95。**乘到 0 需要乘多少次？** 约 1700 次。
但 `y` 不是"突然变 0"，而是**一格一格地穿过整个 denormal 区间**。

> [!important] 出现 denormal 的三个典型结构
> | 结构 | 为什么 |
> |---|---|
> | **反馈延迟 / 混响** | 尾音指数衰减，必然经过 denormal 区 |
> | **IIR 滤波器内部状态** | `y1/y2` 在无输入时衰减，同样穿过 |
> | **包络 / 参数平滑** | `current += (target - current) * coeff` 是**永不精确到达**的指数趋近 |
>
> 第三条最容易被忽略：**任何一阶平滑器的状态都会进入 denormal 区。**

---

## 二、为什么它慢（这是硬件行为）

CPU 的浮点单元为 normal 数做了高度优化（流水线、单周期乘加）。
denormal 的**前导位是 0**，尾数有效位数随数值变小而减少，
硬件需要额外的**前导零计数、移位、特殊舍入**逻辑。

x86 的实现方式是**微码辅助（microcode assist）**：一条浮点指令被拆成一段微码序列执行，
期间流水线被阻塞。这就是 10–100 倍差距的来源。

> [!warning] 这不是"你的代码写得不好"
> 换写法、加 `-O3`、用更好的算法**都没用**——这是 CPU 对 denormal 的处理方式决定的。
> 唯一的解法是**让 denormal 根本不出现**（见第四节）。

### 实测数据（本库自己测的，2026-10-14）

在本机（Apple Silicon arm64，clang 21，`-O2`）用一阶衰减 `y *= g` 测量：

| 平台 | 模式 | 结果 |
|---|---|---|
| **arm64（本机，M 系列）** | denormal ON | 0.112 s |
| | FZ（Flush-to-Zero）ON | 0.080 s |
| | **比值** | **约 1.4×** |
| **x86-64（Rosetta 2 转译）** | denormal ON | 0.095 s |
| | FTZ/DAZ ON | 0.093 s |
| | **比值** | **约 1.0×** |

> [!warning] 这两个数字都不能直接外推，原因不同
> - **Rosetta 的 x86 数字不可信**：Rosetta 是**二进制翻译层**，它把 x86 指令翻译成 ARM 指令执行。
>   x86 的微码辅助行为**不会**被如实模拟。**要测真实 x86 惩罚必须在真 x86 机器（或 VM）上跑。**
> - **arm64 的 1.4× 也不代表"ARM 没问题"**：ARM 的 denormal 处理比 x86 好得多，
>   但**并非零代价**，而且不同代核心的差距很大。
>
> **结论：以本库现有条件无法给出可信的 x86 惩罚倍数。**
> 文献里广泛引用的 **10–100 倍**（[[Bencina - Real-time audio programming 101]] 也用了这个数量级）
> 来自 x86 实测，但**具体数字取决于 CPU 型号和指令**。
> 你需要的是**知道它存在并处理它**，而不是记住某个倍数。
>
> 下面这张表是社区广为流传的说法，**本库未独立验证**：

> [!warning] 待验证
> 有说法称：Intel Sandy Bridge 上 `mulps` 遇到 denormal 有约 140 周期的惩罚；
> 也有说法称 ARM 平台 denormal 惩罚很小、主要问题是"与 x86 结果不一致"。
> 这两条**都未在本库核实**，不要当作结论引用。

---

## 三、为什么在音频里特别致命

### 1. 反馈路径天然产生 denormal

混响、延迟、IIR 滤波器、包络跟随器——**所有带反馈的东西**。
它们的工作方式就是"指数衰减到 0"，而**指数衰减必然经过 denormal 区**。

### 2. 它只在安静时出现 —— 这是最坏的情况

```cpp
// 你以为的测试场景
播放一个鼓 loop  →  信号很大  →  没有 denormal  →  CPU 正常  →  "没问题"

// 实际用户的场景
音乐停了，混响尾巴还在响  →  尾巴衰减到 1e-39  →  CPU 飙升
```

> [!important] 为什么这个组合最致命
> - **测试时听不出来**：denormal 不产生可闻的声音，它只吃 CPU
> - **你的机器太快**：M 系列跑 1 个实例，用户跑 40 个轨
> - **表现为"性能问题"不是"错误"**：没有崩溃、没有报错、没有 NaN
> - **所以你会去优化算法** —— 而算法根本不是问题所在
>
> [[MOC - Realtime Engineering]] 把它列为新手插件故障的 **第 4 名**，并特别注明
> "表现是性能问题不是错误，你会在优化算法上白花很多时间"。

### 3. 尾音**不会**自己衰减到 0（实测发现）

这一条是本库实测出来的，比"会有 denormal"更进一层：

```cpp
// 一阶衰减 y *= g，float32，round-to-nearest
// 当 g 不是 2 的幂时，y 会卡在最小 denormal 上，永不归零
```

| g | 结果 |
|---|---|
| 0.5 | ✅ 到达 0（第 149 步）—— 因为 0.5 是 2 的幂，中点恰好舍入到 0 |
| 0.75 | ❌ 卡在 $2.8026 \times 10^{-45}$ |
| 0.9 | ❌ 卡在 $5.6052 \times 10^{-45}$ |
| 0.99 | ❌ 卡在 $7.0065 \times 10^{-44}$ |
| 0.999 | ❌ 卡在 $7.0065 \times 10^{-43}$ |

**机制**：设最小 denormal $s = 2^{-149}$。`s * 0.9 = 1.26e-45`，它比 $s/2$ 大，
按 round-to-nearest 又舍入回 $s$。**乘任何 $g > 0.5$ 都跳不出这个不动点。**

在真实反馈延迟（50 ms 梳状，float32）里同样成立：

| g | RT60 | 进入 denormal | 最终 buffer 最大值 | 归零？ |
|---|---|---|---|---|
| 0.50 | 0.50 s | 6.4 s | 0 | ✅ |
| 0.80 | 1.55 s | 19.6 s | $2.80 \times 10^{-45}$ | ❌ **永不归零** |
| 0.90 | 3.28 s | 41.5 s | $5.61 \times 10^{-45}$ | ❌ **永不归零** |
| 0.95 | 6.73 s | 85.2 s | $1.26 \times 10^{-44}$ | ❌ **永不归零** |
| 0.99 | 34.4 s | 434.5 s | $7.01 \times 10^{-44}$ | ❌ **永不归零** |

> [!important] 这条发现改变了两件事
> **1. "等它自己衰减到 0 就好了"是错的。** 你的混响在音乐停止 20 秒后，
> 反馈环里仍然有 denormal 在循环——**只要插件还挂着，CPU 就一直在付这个代价**。
> **2. 这给了你一个完美的检测信号。** 如果反馈 buffer 在应该静音的时候不是 0，
> 你就抓到了 denormal（见第六节）。
>
> **注意这是"实测现象"，不是"定理"**：它依赖 round-to-nearest（IEEE 默认）和具体的 $g$。
> 换舍入模式、换 double、或 $g$ 恰好是 2 的幂，行为会不同。

### 4. 多久进入 denormal 区？—— 一个能用的估算公式

RT60 是"衰减 60 dB 的时间"。从满量程衰减到 `FLT_MIN` 是：

$$20 \log_{10}(1.1755 \times 10^{-38}) \approx -758.6 \ \text{dB}$$

所以：

$$\boxed{t_{\text{denormal}} \approx \frac{758.6}{60} \times \text{RT60} \approx 12.6 \times \text{RT60}}$$

**实测验证**（50 ms 梳状，float32）：

| g | RT60 | 预测 $12.6 \times$ RT60 | 实测 | 偏差 |
|---|---|---|---|---|
| 0.80 | 1.55 s | 19.50 s | 19.61 s | +0.5% |
| 0.90 | 3.28 s | 41.30 s | 41.45 s | +0.4% |
| 0.95 | 6.73 s | 84.84 s | 85.16 s | +0.4% |
| 0.99 | 34.37 s | 433.0 s | 434.5 s | +0.3% |

> [!tip] 这个公式的实用价值
> **RT60 = 2 秒的混响 → 约 25 秒后进入 denormal 区。**
> 也就是说：**一首歌放完、尾巴响过 25 秒之后，你的插件开始变慢。**
> 这个时间尺度和"用户切歌、走开喝咖啡"完全重合——所以这个 bug 极难在开发中复现。

---

## 四、四种解决方案

> [!note] 先给结论
> **生产代码用「FTZ/DAZ + 检测清零」组合。**
> 偏置法简单但会引入 DC；`-ffast-math` 不要用（见下）。

### 方案 1：加极小直流偏置

最简单，一行代码。

```cpp
class CombFilter
{
public:
    float process (float x) noexcept
    {
        const float y = buffer[index];
        //                              ↓ 这就是防 denormal 偏置
        buffer[index] = x + y * feedback + kAntiDenormal;
        if (++index >= kSize) index = 0;
        return y;
    }

private:
    static constexpr float kAntiDenormal = 1.0e-20f;   // 远大于 FLT_MIN，远小于音频
    static constexpr int   kSize = 1117;               // 互质延迟，见 [[混响的原理]]
    float buffer[kSize] {};
    int   index = 0;
    float feedback = 0.95f;
};
```

**为什么 `1e-20` 这个值合适**：

| 量 | 值 | 说明 |
|---|---|---|
| `FLT_MIN` | $1.18 \times 10^{-38}$ | 偏置必须**远大于**它，否则自己就是 denormal |
| `1e-20` | $10^{-20}$ | ✅ 比 `FLT_MIN` 大 $10^{18}$ 倍 |
| 16-bit LSB | $3.05 \times 10^{-5}$ | 偏置比它小 $10^{15}$ 倍 |
| 24-bit LSB | $1.19 \times 10^{-7}$ | 偏置比它小 $10^{13}$ 倍 |

> [!warning] 代价：偏置会在反馈环里被放大成 DC
> 偏置进入反馈环后，稳态直流增益是 $1/(1-g)$。实测（g = 0.95，50 ms 延迟）：
>
> | 偏置 | 稳态输出 DC | 折合 dBFS |
> |---|---|---|
> | `1e-20` | $2.0 \times 10^{-19}$ | -374.0 dB |
> | `1e-15` | $2.0 \times 10^{-14}$ | -274.0 dB |
> | `1e-12` | $2.0 \times 10^{-11}$ | -214.0 dB |
> | `1e-8` | $2.0 \times 10^{-7}$ | **-134.0 dB** ⚠️ |
>
> **`1e-20` 放大 20 倍后是 -374 dBFS，完全无害。**
> 但如果你图省事写 `1e-8`，得到的是 **-134 dBFS 的直流**——
> 这已经接近 24-bit 的噪声底（-138.5 dBFS），在某些分析场景下是可测的。
> **偏置值不是"随便取个小数"，选大了会真的引入 DC。**

**优点**：一行、无分支、不会漏、对 SIMD 友好。
**缺点**：引入 DC；每个反馈环都要记得加；**如果信号本身可能为负，偏置会持续推高状态**。

### 方案 2：检测并清零

```cpp
#include <cmath>

// 分支版本：语义最清晰
inline float flushDenormal (float x) noexcept
{
    return (std::abs (x) < 1.0e-30f) ? 0.0f : x;
}
```

用在反馈状态上：

```cpp
float process (float x) noexcept
{
    float y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;

    // 只清状态变量，不清输出 —— 清输出会在尾音里产生"台阶"
    y1 = flushDenormal (y);
    y2 = flushDenormal (y1);

    x2 = x1; x1 = x;
    return y;
}
```

**无分支版本**（位运算，利用"denormal 的指数位全为 0"）：

```cpp
#include <cstdint>
#include <cstring>

inline float flushDenormalBits (float x) noexcept
{
    std::uint32_t bits;
    std::memcpy (&bits, &x, sizeof (bits));
    // 指数位（0x7f800000）非零 → 是 normal 或 0/Inf/NaN → 原样返回
    // 指数位全零     → 是 denormal（或 ±0）→ 返回 0
    return (bits & 0x7f800000u) ? x : 0.0f;
}
```

> [!warning] 无分支版有代价，不一定更快
> 它需要**在浮点寄存器和整数寄存器之间搬数据**。ARM 上这个搬运有明确成本，
> 所以"无分支"在 ARM 上**可能比带分支的版本更慢**。
> **先写分支版本，测出来是瓶颈再换。** 而且音频代码里这个分支**几乎 100% 预测正确**
> （尾音期间一直走"是 denormal"分支），代价本来就很小。
>
> 另一个坑：`bits & 0x7f800000` 对 `-0.0f`（`0x80000000`）也返回 0，
> 这**恰好是想要的**，但你要知道这一点。

**优点**：不引入 DC、精确、可只作用于特定信号。
**缺点**：多一次比较；用错阈值（比如 `1e-8`）会把正常的小信号也清掉。

> [!tip] 阈值怎么选
> **不要用 `FLT_MIN` 当阈值**——那样只在**已经**进入 denormal 之后才清零，
> 而你要避免的是"进入 denormal 之后的那次运算"。
> 用比 `FLT_MIN` 大几个数量级的值（如 `1e-30`），留出安全余量。
> 音频信号里 `1e-30` 以下的东西**在任何位深下都不可闻、不可测**。

### 方案 3：编译选项（⚠️ 会破坏 IEEE 语义）

```bash
# GCC / Clang：把 denormal 当 0 处理
-ffast-math
```

**实测的加速效果**（文献示例：一个纯衰减循环，x86）：

| 编译方式 | 耗时 | 相对 |
|---|---|---|
| 默认 | 3.82 s | 1× |
| `-O3` | 3.46 s | 1.1× |
| **`-O3 -ffast-math`** | **0.02 s** | **约 190×** |

> [!danger] `-ffast-math` 会破坏 IEEE 语义 —— 不要用在 DSP 代码上
> 它打开的不只是 denormal 处理，而是一整套"假设浮点满足实数代数律"的优化：
>
> | 它允许编译器 | 后果 |
> |---|---|
> | 假设没有 NaN / Inf | NaN 检查可能被优化掉，**发散时你收不到信号** |
> | 重排浮点运算顺序 | 结果**不可复现**，null test 失效 |
> | 把 `a*b + a*c` 变成 `a*(b+c)` | **数值行为改变** |
> | 假设 `x != x` 为假 | `std::isnan()` 分支被删 |
>
> **最后一条尤其危险**：你写的"检测 NaN 并复位"的保护逻辑会**被静默删掉**。
>
> 本库的立场（与 [[实时音频线程契约]] 一致）：**用方案 1 或 2，保留 IEEE 语义。**

**更好的编译选项**（只关 denormal，不动其他语义）：

```bash
# Clang / GCC：denormal 结果直接刷成 0（只影响结果，不影响其他优化）
-ffp-contract=off -fno-fast-math
# 或更精确的：
-fdenormal-fp-math=positive-zero
```

> [!warning] 待验证
> 实测发现：**`-ffast-math` 在本机（arm64 clang 21）并不会修改 FPCR 的 FZ 位**——
> 编译后运行时读 FPCR 仍是 `0x0`。
> 也就是说 `-ffast-math` 的效果来自**编译期优化**，而不是"帮你打开了 FTZ"。
> 这与很多人的直觉（"`-ffast-math` = 自动开 FTZ"）不符。
> **这条只在本机验证过，未在其他编译器/平台上核实。**

### 方案 4：平台特定的 FTZ / DAZ（推荐）

这是**真正的解决方案**：告诉 CPU"denormal 一律当 0 处理"。

- **x86**：`MXCSR` 寄存器
  - `FTZ`（bit 15）：把 denormal **输出**刷成 0
  - `DAZ`（bit 6）：把 denormal **输入**当 0
- **ARM (AArch64)**：`FPCR` 寄存器
  - `FZ`（bit 24）：同时作用于 denormal 的**输入和输出**
  - `FZ16`（bit 19）：半精度版本（需要 `__ARM_FP & 0x2`）

> [!important] 跨平台的关键差异（这是本页最实用的一段）
> | | x86 | ARM (AArch64) |
> |---|---|---|
> | 寄存器 | `MXCSR` | `FPCR` |
> | 读 | `_mm_getcsr()` | `mrs x, FPCR` |
> | 写 | `_mm_setcsr()` | `msr FPCR, x` |
> | 输出刷零 | `FTZ` bit 15 | `FZ` bit 24 |
> | 输入刷零 | `DAZ` bit 6（**独立**位） | `FZ` bit 24（**同一个**位） |
> | 需要的 mask | `(1<<15) \| (1<<6)` | `(1<<24)` |
> | 范围 | **仅 SSE/AVX**（x87 不受影响） | 标量 + Advanced SIMD 都受控 |
>
> **最容易写错的地方**：ARM 上**只有一个 FZ 位**同时管输入和输出，
> 照抄 x86 的 `(1<<15)|(1<<6)` 到 ARM 上会设错位（bit 6 在 FPCR 里是别的含义）。
>
> 另注：ARMv8 后来加了 `FEAT_AFP`（alternate floating point behavior），
> 提供独立的 `FIZ`（bit 0）来对应 x86 的 DAZ。但它是**可选特性**，不要依赖。

**完整可编译的跨平台实现**：

```cpp
// ─────────────────────────────────────────────────────────────
//  denormal.h —— 跨平台 FTZ/DAZ 控制
//  用法：在 processBlock 开头放一个 ScopedNoDenormals
// ─────────────────────────────────────────────────────────────
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
  {
      FpControl v;
      __asm__ __volatile__ ("mrs %0, FPCR" : "=r" (v));
      return v;
  }
  inline void fpSet (FpControl v) noexcept
  {
      __asm__ __volatile__ ("msr FPCR, %0" :: "r" (v));
  }
  inline FpControl denormalMask() noexcept { return (1ull << 24); }            // FZ

#else
  // 其他架构：退化为空实现（编译通过，不做任何事）
  using FpControl = int;
  inline FpControl fpGet() noexcept { return 0; }
  inline void      fpSet (FpControl) noexcept {}
  inline FpControl denormalMask() noexcept { return 0; }
#endif

// RAII：进入作用域开启，离开时**恢复原值**（不是关掉）
class ScopedNoDenormals
{
public:
    ScopedNoDenormals() noexcept
        : saved (fpGet()) { fpSet (saved | denormalMask()); }

    ~ScopedNoDenormals() noexcept { fpSet (saved); }

    ScopedNoDenormals (const ScopedNoDenormals&) = delete;
    ScopedNoDenormals& operator= (const ScopedNoDenormals&) = delete;

private:
    FpControl saved;
};
```

用法：

```cpp
void processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) override
{
    const ScopedNoDenormals noDenormals;   // ← 第一行
    // ... 正常处理
}
```

> [!warning] 为什么必须"恢复原值"而不是"关掉"
> `MXCSR` / `FPCR` 是**每个线程**的寄存器状态。
> 但音频线程可能被宿主复用、也可能和其他插件共享（不同宿主策略不同）。
> **你改了不恢复，会影响同线程上跑的其他代码**（包括宿主自己的）。
> 用 RAII 保存/恢复是唯一安全的做法——JUCE 的 `juce::ScopedNoDenormals` 就是这么做的。
>
> **如果你用 JUCE，直接用它自带的 `juce::ScopedNoDenormals`**（在 `juce_core` 里），
> 不要自己再写一份。本页的代码是为了让你**看懂它在做什么**，以及在没有 JUCE 时能用。

---

## 五、跨平台注意

你的机器是 **Apple Silicon (arm64)**，但要兼容 **Windows (x86-64)**。这个组合有三个坑：

| # | 坑 | 说明 |
|---|---|---|
| 1 | **开发机上看不到问题** | ARM 的 denormal 惩罚远小于 x86。**你在 Mac 上测不出这个 bug** |
| 2 | **mask 位不同** | x86 是 `(1<<15)\|(1<<6)`，ARM 是 `(1<<24)`。抄错就静默失效 |
| 3 | **结果会不一致** | 开 FTZ 后，同一段 DSP 在 ARM 和 x86 上的**输出可能不同**（denormal 被刷成 0 的时机不同） |

> [!important] 第 1 条是你最大的风险
> 本机实测 arm64 的 denormal 惩罚约 **1.4×**，而 x86 的公开数据是 **10–100×**。
> **这意味着：你在 Mac 上跑 40 个混响实例可能毫无压力，用户在同一份代码的 Windows 机器上会爆音。**
>
> 对策：**不要依赖"我在本机测没问题"**。denormal 处理必须是**代码里的显式逻辑**，
> 而不是"等测出来再说"。

> [!note] 关于第 3 条：这是一个真实的取舍
> 开了 FTZ 之后，ARM 和 x86 的输出**理论上**应该一致（都刷成 0），
> 但**刷零的时机和范围**（输入/输出、标量/向量）在两边的定义不同，
> 所以**逐 bit 一致仍然没有保证**。
> 如果你的插件需要**跨平台 bit-exact**（比如做 null test 的 CI），
> 这会影响你——见 [[浮点确定性与可复现性]]。

**CI 检查清单**：

```bash
# 确认两个平台的 mask 都正确编译进去了
grep -rn "1ull << 24\|1u << 15" 30-Wiki/DSP/denormal\ 数处理.md   # 只是确认文档没抄错

# 真正的做法：写一个自检函数，在 prepareToPlay 里跑一次
```

```cpp
// 自检：开启后，一个已知的 denormal 运算应该返回 0
static bool verifyFlushToZeroWorks() noexcept
{
    ScopedNoDenormals guard;
    const volatile float tiny = 1.0e-40f;          // volatile 防止被常量折叠
    const float result = tiny * 1.0f;
    return result == 0.0f;                          // FTZ/DAZ 生效时应为 0
}
```

> [!warning] 这个自检**可能失败**，而且失败是正常的
> `1e-40f` 在编译期就可能被折叠成常量。加 `volatile` 能缓解，但不保证。
> 更可靠的做法是在**运行时**从一个不会被优化掉的来源产生 denormal
> （比如让一个真实的反馈环跑几千次）。
> **不要把自检失败当成"平台不支持"** —— 先排除常量折叠。

---

## 六、怎么检测

### 方法 1：CPU 剖析（发现"有这个问题"）

| 工具 | 看什么 |
|---|---|
| **Xcode Instruments**（Time Profiler） | 反馈处理函数的耗时**在信号停止后反而上升** |
| **perf**（Linux） | 找 `assist` / 微码相关的周期计数异常 |
| **Tracy / Superluminal** | 长时间录制，看"安静段落"的 CPU 曲线 |

> [!tip] 最有辨识度的特征
> **CPU 占用与信号电平反相关。**
> 正常情况：声音大 → CPU 高。denormal 情况：**声音没了 → CPU 反而更高**。
> 这个特征非常独特，一旦你见过就再也不会误判。

### 方法 2：在反馈路径加断言（定位"在哪"）

```cpp
#include <cassert>
#include <cstdio>
#include <cfloat>
#include <cmath>

// 调试期检查：如果反馈状态进入 denormal 区，报出来
inline float checkDenormal (float y, int sampleIndex)
{
   #ifndef NDEBUG
    if (y != 0.0f && std::abs (y) < FLT_MIN)
        std::fprintf (stderr, "⚠️ denormal at sample %d: %g\n",
                      sampleIndex, (double) y);
   #endif
    return y;
}

// 用法：只在反馈状态上调用，不要在每个输出上调用
delayLine.write (checkDenormal (input + y * feedback, n));
```

> [!warning] 这个断言会在真实混响里刷屏
> 按第三节的计算，RT60 = 2 s 的混响约 **25 秒后**就进入 denormal 区，
> 之后**每个样本**都会触发断言。
> **正确用法**：不是"断言不许出现"，而是"**统计出现次数**"。
> 把它改成计数器 + 每秒打印一次，或者只在"应该完全静音"时才断言。

### 方法 3：直接检查状态是否归零（最实用）

这是本库实测发现的现象（第三节第 3 条）给出的**免费检测器**：

```cpp
// 在"应该已经静音"的时候检查反馈 buffer
bool isTailTrulySilent (const float* buffer, int size) noexcept
{
    for (int i = 0; i < size; ++i)
        if (buffer[i] != 0.0f)
            return false;       // ← 有非零值 = 有 denormal 在循环
    return true;
}
```

> [!important] 为什么这个检查特别有价值
> 因为**正确的实现会让它返回 `true`，错误的实现返回 `false`**——
> 这是一个**布尔结果**，不是"看起来快不快"。
> 可以写成自动化测试：
>
> ```python
> # 在 Python 原型里先验证这个性质
> # 喂一个脉冲，跑 300 秒（虚拟时间），检查尾音是否精确为 0
> assert np.all(tail == 0.0), "尾音没有归零 → 反馈环里有 denormal"
> ```
>
> 这比"测 CPU 占用"可靠得多，而且**不需要真机器、不需要 profiler、可以进 CI**。

### 方法 4：用 Python 复现（推荐的学习路径）

```python
import numpy as np

# float32 的一阶反馈，看它是否卡在 denormal
def tail_never_reaches_zero(g=np.float32(0.9), n=100_000):
    y = np.float32(1.0)
    for _ in range(n):
        y = np.float32(y * g)
        if y == np.float32(0.0):
            return True, None
    return False, y

ok, stuck = tail_never_reaches_zero()
print("归零?", ok, " 卡住的值:", stuck)
# → 归零? False  卡住的值: 5.605194e-45   ← 这就是 denormal
```

> [!tip] 为什么要在 Python 里先做
> 因为 numpy 的 `np.float32` 和 C++ 的 `float` **是同一种 IEEE 754 binary32**，
> 行为完全一致。而 Python 里你可以**几秒钟跑 10 万步**、直接 print 中间值。
> 在 C++ 里做同样的事要先编译、要调试、要看反汇编。
> **这就是 [[Python 优先的 DSP 学习路径]] 的价值。**

---

## 七、AI 会怎么写错

> [!important] 这是本页最实用的一节
> AI **通常完全不知道 denormal 这回事**。
> 这不是它"写错了"，而是**它的训练数据里 99% 的 C++ 代码不是音频 DSP 代码**，
> 而 denormal 只在音频（和少数数值计算）里才是个问题。
>
> **所以 AI 一定会写出"干净的反馈路径"** —— 逻辑完全正确、数学完全正确、
> 在开发机上跑得完全正常，然后在用户的 Windows 机器上安静时卡死。

| # | AI 常写 | 为什么错 | 怎么查 |
|---|---|---|---|
| 1 | **反馈路径完全没有任何 denormal 处理** | 这是默认行为。AI 不会主动加，因为它不知道有这个需求 | grep 反馈写回的那一行：有没有 `+ 1e-20f` 或 flush 调用 |
| 2 | 加了 `if (y < 1e-30f) y = 0;` | **忘了负数**！denormal 有正有负 | 查有没有 `std::abs()` 或 `fabsf()` |
| 3 | 用 `1e-8f` 当偏置 | 偏置太大，反馈环里放大成 **-134 dBFS 的 DC** | 算一下 `bias / (1 - feedback)` 折合多少 dBFS |
| 4 | 在**输出**上清零而不是在**状态**上 | 输出清零会在尾音里产生可闻的**台阶** | 看清零作用在哪个变量上 |
| 5 | 只处理了 Biquad，忘了延迟线/混响 | 每个反馈结构都要单独处理 | 数一数有几个反馈环，检查是不是每个都有 |
| 6 | 用 `-ffast-math` 当"解决方案" | 破坏 IEEE 语义，可能删掉你的 NaN 检测 | 查 CMakeLists 里有没有 `-ffast-math` |
| 7 | 写了 `_mm_setcsr` 但**不恢复** | 污染同线程上其他代码的浮点状态 | 查是否用了 RAII 保存/恢复 |
| 8 | 把 x86 的 `(1<<15)\|(1<<6)` 抄到 ARM 分支 | ARM 只有一个 FZ 位（bit 24），bit 6 是别的含义 | 检查两个 `#if` 分支的 mask |
| 9 | 在 `processBlock` 里**每个样本**调 `_mm_getcsr()` | 读写控制寄存器有成本，而且没必要 | 查 ScopedNoDenormals 是不是在循环外 |
| 10 | 假设"尾音会自己衰减到 0" | 实测证明**不会**（非 2 的幂的 g 会卡住） | 见第三节第 3 条 |

> [!tip] 第 1 条和第 10 条是同一个认知缺口
> AI 的心智模型是"浮点能表示任意小的数，衰减就是趋向 0"。
> **真实情况是：浮点有个下限，而且衰减会卡在那个下限上。**
> 你只要在 prompt 里点出这一点，AI 就能写对——
> **但前提是你自己知道。这就是这一页存在的理由。**

**给 AI 的 prompt 模板**：

```
这段代码是一个反馈延迟/混响。请检查并修复 denormal 问题：
1. 反馈路径里的状态变量在无输入时会衰减到 1e-38 以下，进入 denormal 区
2. 在 x86 上这会让运算慢 10-100 倍，且只在安静时出现
3. 请用「跨平台 FTZ/DAZ（RAII 保存恢复）+ 反馈状态清零」组合解决
4. 注意：ARM 的 FPCR.FZ 是 bit 24（同时管输入输出），
   x86 的 MXCSR 是 FTZ bit 15 + DAZ bit 6（分开的）
5. 不要用 -ffast-math
6. 清零时不要忘记负数（用 std::abs）
```

---

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| **安静时 CPU 飙升** | 反馈尾音进入 denormal | FTZ/DAZ + 状态清零（第四节） |
| 加偏置后出现直流/低频嗡声 | 偏置太大（如 `1e-8`），被 $1/(1-g)$ 放大 | 用 `1e-20`；或改用检测清零 |
| 清零后尾音有"台阶"感 | 在**输出**上清零，而不是在状态上 | 只清反馈状态变量 |
| 在 Mac 上没问题，Windows 用户爆音 | ARM 惩罚小（实测 1.4×），x86 大（10–100×） | **代码里显式处理，不要靠测** |
| FTZ 设了但没效果 | mask 位写错（ARM 抄了 x86 的 mask） | 核对 `(1<<24)` vs `(1<<15)\|(1<<6)` |
| 宿主里其他插件行为异常 | 改了 MXCSR/FPCR 没恢复 | 用 RAII，恢复**原值** |
| `-ffast-math` 后 NaN 检测失效 | 编译器假设无 NaN，删掉了分支 | 去掉 `-ffast-math` |
| 尾音"永不消失"，CPU 一直高 | 实测现象：g 非 2 的幂时卡在最小 denormal | 同上，必须显式清零 |
| 单精度没问题，双精度也有 | double 的 denormal 阈值是 $2.2 \times 10^{-308}$ | 同样处理，但 `FLT_MIN` 要换成 `DBL_MIN` |
| 断言刷屏 | denormal 一旦出现就是每个样本都有 | 改成计数器，不要用 assert |

---

## 九、怎么验证

> [!important] 原则：数值验证优先于听感
> denormal **不产生声音**，所以"听"是完全无效的验证手段。
> 你必须用数值方法。

| # | 验证什么 | 方法 | 通过标准 |
|---|---|---|---|
| 1 | **尾音是否归零** | 喂脉冲，跑足够长时间，检查尾音 | `np.all(tail == 0.0)` |
| 2 | **需要跑多久** | $t \approx 12.6 \times \text{RT60}$（第三节） | RT60=2s → 跑 30 秒以上 |
| 3 | FTZ/DAZ 是否生效 | `verifyFlushToZeroWorks()` 自检 | 返回 `true` |
| 4 | 清零是否漏了负数 | 喂**负**脉冲，重复测试 1 | 同样归零 |
| 5 | 偏置是否引入 DC | 无输入跑 60 秒，测输出均值 | < -200 dBFS |
| 6 | CPU 是否与电平反相关 | profiler 长录，看安静段 | 安静段不高于响段 |
| 7 | 跨平台一致性 | 两平台跑同一个 null test | 差异 < -100 dB（见 [[音频测量基础]]） |

**用本库的工具做第 1 条**：

```python
import sys
sys.path.insert(0, '50-Playground/tools')
from audio_io import impulse, peak_db
import numpy as np

# 假设这是你的混响（Python 原型）
h = my_reverb.process(impulse(int(48000 * 60)))     # 60 秒虚拟时间

tail = h[int(48000 * 40):]                          # 最后 20 秒
print(f"尾音峰值: {peak_db(tail):.1f} dB")
print(f"尾音精确为 0? {np.all(tail == 0.0)}")        # ← 关键断言

# 用 float32 模拟插件里的精度（numpy 默认是 float64，行为不同！）
h32 = np.asarray(h, dtype=np.float32)
tail32 = h32[int(48000 * 40):]
print(f"float32 尾音精确为 0? {np.all(tail32 == 0.0)}")
```

> [!warning] 必须用 `float32` 测，不能用 numpy 默认的 `float64`
> **这是本页最容易犯的验证错误。**
> - `float64` 的 denormal 阈值是 $2.2 \times 10^{-308}$，**比 float32 低 270 个数量级**
> - 用 `float64` 跑，尾音会一路衰减到 $10^{-300}$，你**永远看不到"卡住"的现象**
> - 而插件里用的是 `float`（32-bit），**行为完全不同**
>
> ```python
> h = np.asarray(h, dtype=np.float32)   # ← 这一行是必须的
> ```
> 同理，`50-Playground/tools/audio_io.py` 内部统一用 `float64`
> （为了测量精度），**所以你不能直接用它测 denormal**——
> 要先把数组转成 `float32` 再做衰减运算。

---

## 十、给这个知识库的结论

> [!note] 我的判断
> 1. **denormal 处理是"必须有"，不是"优化项"。** 它和"反馈增益必须钳制"是同一级别的硬约束。
> 2. **写每个反馈结构时立刻加上，不要等测出问题。** 因为在 Mac 上你测不出来。
> 3. **优先用 `juce::ScopedNoDenormals`**（如果用 JUCE），它是久经考验的跨平台实现。
>    本页的代码用于理解原理和 JUCE-free 场景。
> 4. **把"尾音归零"写成自动化测试**，放进 CI。这是唯一能在开发机上抓到这个 bug 的方法。
> 5. 文献里"10–100 倍"的数字**在本库未能独立验证**（本机 arm64 只有 1.4×，
>    Rosetta 的数字不可信）。**但"必须处理"这个结论不受影响**——
>    因为即使只有 1.4×，你也绝不会想为了一个纯 bug 付这个代价。

---

## 相关

- [[实时音频线程契约]] — 本页是它那条 denormal 规则（禁止清单最后一行）的展开
- [[Biquad 滤波器]] — 常见坑表里的"静音时 CPU 飙升"
- [[混响的原理]] — 反馈路径是 denormal 的主要产地
- [[延迟与回声的原理]] · [[延迟线 delay line]] · [[反馈延迟网络 FDN]]
- [[参数平滑 parameter smoothing]] — 一阶平滑器的状态**也**会进入 denormal 区
- [[动态处理的原理]] — 检测器与平滑器同理
- [[浮点音频表示]] — float32 的位布局与动态范围
- [[浮点确定性与可复现性]] — FTZ 对跨平台一致性的影响
- [[浮点异常]] — NaN/Inf 的传播（和 denormal 是两类问题，别混）
- [[性能剖析]] — 怎么发现"安静时反而更慢"
- [[SIMD]] — 无分支清零在向量化时的取舍
- [[Python 优先的 DSP 学习路径]] — 为什么先在 numpy 里复现
- [[MOC - DSP]] · [[MOC - Realtime Engineering]]

> [!note] 待补充
> - **在真 x86 机器上实测 10–100 倍这个数字**（本库只有 Rosetta 数据，不可信）
> - 不同 x86 微架构（Nehalem / Sandy Bridge / Skylake / Zen）的惩罚差异
> - Apple Silicon 各代（M1/M2/M3/M4）的 denormal 行为是否一致
> - `-ffast-math` 在 MSVC 上的对应物（`/fp:fast`）是否也影响 FTZ
> - JUCE `ScopedNoDenormals` 的确切实现（需要读 JUCE 源码确认位掩码）
> - 向量化（SIMD）路径下 denormal 惩罚是否与标量相同
> - 是否应该在 `releaseResources` 里恢复浮点控制寄存器
