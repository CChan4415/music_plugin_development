---
title: 为什么 AI 写不好实时音频代码
type: wiki
domain: ai-audio
status: solid
confidence: high
sources: ["[[Bencina - Real-time audio programming 101]]"]
tags: [gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# 为什么 AI 写不好实时音频代码

> [!important] 一句话
> **AI 的失败不是"写得差"，而是"训练数据里几乎没有实时代码"。**
> 它的默认行为是写"正常"的 C++——而实时音频恰恰要求你**反着来**。

## 核心原因：数据分布问题

绝大多数 C++ 代码不是实时代码。AI 从海量代码中学到的"好习惯"，在音频线程里全是错的：

| 编程常识 | 在音频线程里 |
|---|---|
| 用 `std::vector` 动态增长 | ❌ 会分配内存 |
| 用 `std::mutex` 保护共享数据 | ❌ 会优先级反转 |
| 用 `std::string` 拼日志 | ❌ 会分配 + 系统调用 |
| 用 `printf` 调试 | ❌ 会阻塞 |
| 在构造函数里初始化一切 | ❌ 宿主扫描插件时会构造它 |
| 异常处理错误 | ❌ 栈展开可能分配 |

> [!note] 这不是 AI 的"缺陷"，是它的"训练目标"
> AI 被训练成写**通用、可读、符合惯例**的代码。
> 实时音频的约束是**特定领域**的，而且**与通用惯例冲突**。
>
> 所以 AI 不知道这些约束是**正常的**——**你要在 prompt 里告诉它**。

---

## 五个失败模式（按危险程度）

### 1. 分配内存（头号违规）

```cpp
// ❌ AI 的默认写法
void processBlock (AudioBuffer<float>& buffer, MidiBuffer&) override
{
    std::vector<float> temp (buffer.getNumSamples());   // 分配！
    // ...
}

// ✅ 正确：在 prepareToPlay 里预分配，音频线程只读写
void prepareToPlay (double, int blockSize) override
{
    tempBuffer.resize (blockSize);      // 只在这里分配
}
void processBlock (AudioBuffer<float>& buffer, MidiBuffer&) override
{
    // 直接用 tempBuffer，不再分配
}
```

**为什么危险**：分配可能触发系统调用、可能阻塞在锁上、耗时不可预测。
**为什么 AI 不知道**：局部变量用 `std::vector` 是完全正常的 C++ 写法。

### 2. 加锁

```cpp
// ❌ AI 的默认写法
std::mutex paramMutex;
void setGain (float g) { std::lock_guard<std::mutex> l (paramMutex); gain = g; }
float process (float x) { std::lock_guard<std::mutex> l (paramMutex); return x * gain; }
```

**为什么危险**：优先级反转——GUI 线程持锁时被抢占，**高优先级的音频线程要等它**。
**正确做法**：`std::atomic` + 参数平滑（见 [[参数平滑 parameter smoothing]]）。

### 3. 在构造函数里做重活

```cpp
// ❌ AI 的默认写法
MyProcessor() {
    loadImpulseResponse ("/path/to/ir.wav");   // 读文件！
    fft = std::make_unique<juce::dsp::FFT> (11);  // 分配！
}
```

**为什么危险**：**宿主扫描插件时会构造它**。构造慢 → 扫描超时 → 插件"不出现"。
**正确做法**：构造函数只做轻量初始化，重活在 `prepareToPlay`。

### 4. 参数不钳制

```cpp
// ❌ AI 的默认写法
void setCutoff (float hz) { cutoff = hz; }   // 用户能给 100000 Hz
```

**为什么危险**：滤波器系数公式在 `f0 > fs/2` 时失效 → 发散 → 刺耳噪声。
**正确做法**：`cutoff = std::clamp (hz, 20.0f, sampleRate * 0.45f);`

### 5. 忘记 denormal

AI 通常**完全不知道 denormal 这回事**，会写出干净的反馈路径。
安静时 CPU 飙升 10–100 倍。见 [[denormal 数处理]]。

---

## 为什么音频领域的错误特别难发现

> [!danger] 这是音频相比其他领域最恶劣的地方

| 特征 | 后果 |
|---|---|
| **错误不可见** | 大多数情况下"听起来差不多"，不会崩 |
| **只在极端条件暴露** | 用户拧到极值、40 个轨道、老机器 |
| **"能跑" ≠ "对"** | 编译通过 + 出声，你就以为完成了 |
| **耳朵不可靠** | 6 dB 的幅度误差听起来"合理"（本库真实案例） |
| **延迟暴露** | 你测的时候没事，用户报告"偶尔爆音" |

> [!important] 一个真实例子
> 本库的全通滤波器实现曾经写错了（缓冲区存 `x+g*bufOut` 而非 `x+g*y`）。
> 后果：g=0.7 时增益 2.49 倍——**它不是全通了，而是个谐振滤波器**。
> 但它**能编译、能出声、混响扩散也有效果**。
>
> 抓住它的唯一方法是**"幅度恒为 1"这个解析断言**。
> 见 [[2026-10-14 测量工具会骗你 —— 九次踩坑记录]]。

---

## 怎么在 prompt 里预防

> [!tip] 明确告诉 AI 约束，比事后审查便宜得多

**模板**：

```
这是一个 JUCE 音频插件的 processBlock。请遵守以下硬性约束：

1. 音频线程内**绝对禁止**：内存分配、加锁、文件/网络 IO、printf、异常
2. 所有缓冲区和对象必须在 prepareToPlay 里预分配
3. 所有参数必须钳制到安全范围（滤波器 f0 < fs*0.45，反馈 < 0.999）
4. 参数变化必须平滑（用 SmoothedValue 或一阶低通）
5. 反馈路径必须处理 denormal（加 1e-20 偏置或 FTZ）
6. 不要假设固定的 block size 或声道数，处理 numSamples == 0
7. 如果引入延迟，必须调用 setLatencySamples

如果某个约束无法满足，**明确告诉我**，不要默默忽略。
```

> [!warning] 最后一句很重要
> 加上"如果无法满足请告诉我"能显著减少"AI 悄悄违反约束"的情况。
> 但仍然**必须自己核对**——见 [[AI 生成代码的审查清单]]。

---

## 哪些事 AI 反而做得好

> [!note] 诚实评估，避免因噎废食

| 任务 | 为什么适合 AI |
|---|---|
| **写测试脚本** | 逻辑明确、容易验证、省时间（见 [[AI 生成音频测试]]） |
| **解释编译错误** | C++ 报错信息密度极低，AI 翻译得很好 |
| **写样板代码** | CMake、插件骨架、状态序列化——没有学习价值 |
| **解释不熟悉的 API** | 比翻文档快（但要核对版本） |
| **生成边界测试用例** | "喂 0 长度缓冲区""喂 NaN"这类 |
| **重构 / 改名** | 机械性工作 |

**核心原则**：**让 AI 做"错了立刻能看出来"的事，自己做"错了看不出来"的事。**

DSP 核心属于后者——因为你需要**建立直觉**，否则无法调试。

---

## 九、AI 会怎么写错（元层面）

| # | 元错误 | 后果 |
|---|---|---|
| 1 | **声称已处理但实际没处理** | 你以为安全了 |
| 2 | **给过时版本的 API** | 编译失败或行为不对 |
| 3 | **注释说"不会分配"但代码分配了** | 注释骗人 |
| 4 | **测试脚本本身有 bug** | 你以为是实现错了 |
| 5 | **过度自信地编造 API** | 浪费时间 |

---

## 相关

- [[AI 生成代码的审查清单]] — 这一页的"怎么办"
- [[AI 生成音频测试]] — 让 AI 写测试的正确姿势
- [[实时音频线程契约]] — 实时安全的完整规则
- [[denormal 数处理]]
- [[参数平滑 parameter smoothing]]
- [[插件验证工具]] — 自动化检测
- [[Bencina - Real-time audio programming 101]] — 权威来源
- [[MOC - AI Audio]]

> [!note] 待补充
> - 实测：同一个 DSP 任务，不同 prompt 详细程度下的 AI 输出质量对比
> - 哪些 AI 模型在音频代码上表现更好（需要实际测试）
> - 用本库的历史 bug 做 AI 输出质量的回归测试
