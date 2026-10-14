---
title: "Real-time audio programming 101: time waits for nothing"
type: source
domain: realtime
status: solid
confidence: high
tags: [cpp, gotcha]
source_type: article
url: http://www.rossbencina.com/code/real-time-audio-programming-101-time-waits-for-nothing
author: Ross Bencina
year: 2011
created: 2026-10-14
updated: 2026-10-14
---

# Real-time audio programming 101: time waits for nothing

> [!important] 这是实时音频编程的**经典文献**
> 本库的 [[实时音频线程契约]] 就是基于它写的。
> 作者 Ross Bencina 是 AudioMulch 的作者，也是 PortAudio 的核心贡献者。

## 元信息

| 项 | 值 |
|---|---|
| 类型 | 技术文章（博客） |
| 作者 | Ross Bencina（AudioMulch、PortAudio） |
| 链接 | <http://www.rossbencina.com/code/real-time-audio-programming-101-time-waits-for-nothing> |
| 年份 | 2011（2011-08-13 最后更新） |

## 为什么这份资料权威

它**不是个人经验之谈**，而是汇集了平台厂商的官方规定。文章开头直接引用：

| 来源 | 原文要点 |
|---|---|
| **微软 XAudio2 文档** | "音频处理线程卡住，是因为客户端在回调里做了会阻塞的事，比如访问磁盘、与其他线程同步" |
| **Jeff Moore（Apple）** 在 CoreAudio 邮件列表 | "你的 IOProc 在调用 HAL 做阻塞调用，还调用 NSLog——那会分配内存并以有趣又意外的方式阻塞。你**绝对不能**在 IOProc 里做这些" |
| **JACK API 文档** | "函数内的代码必须适合实时执行。它不能调用可能长时间阻塞的函数，包括 `malloc`、`free`、`printf`、`pthread_mutex_lock`、`sleep`、`wait`、`poll`、`select`、`pthread_join`、`pthread_cond_wait` 等等" |

> [!tip] 这就是为什么"不能在音频线程分配/加锁"不是教条
> 三大平台的官方文档都这么要求。AI 写代码时**默认不会遵守**，
> 因为绝大多数 C++ 代码不是实时代码。

## 核心论点（我的理解）

### 1. 实时不等人

以 44100Hz、256 样本缓冲区为例，回调必须每 **5.8ms** 交付一个缓冲区。**每一次都是，没有例外。**

作者强调缓冲区大小在 1–5ms 是常态，低延迟场景（乐器、实时效果）要求更低。
端到端响应 < 8ms 是交互系统的合理目标。

### 2. 中心法则

> **"If you don't know how long it will take, don't do it."**
> （如果你不知道它要多久，就别做。）

这是全文最重要的一句。它不是"要快"，而是**要可预测**。

> [!important] 关键区分：最坏情况 vs 平均情况
> 作者特别指出：软件工程通常按**平均复杂度**评估算法，
> "99.9% 的时间很快、偶尔慢 1000 倍"往往还被认为是"最快的算法"。
> **但实时音频不能接受这个**——它只关心**最坏情况**。
>
> 他举的例子：用 `memset` 清零一个大延迟线"看起来很快"，
> 但如果延迟线很大，这个调用本身就会超出缓冲区时间 → 爆音。
> **正确做法是把负载分摊到多个采样/回调**，哪怕总共多花几个周期。

### 3. 不用锁的三个理由

| # | 理由 | 机制 |
|---|---|---|
| 1 | **优先级反转** | GUI 线程持锁时被抢占，高优先级的音频线程却要**等它** |
| 2 | **临界区里的代码也变成你的责任** | 音频线程实际要等整个临界区跑完，而临界区里可能有 `vector::push_back`（会分配+拷贝大量数据） |
| 3 | **调度器不可信** | 通用 OS 的调度器不保证实时行为，实现还会随版本变 |

> [!warning] 关于 trylock
> 作者指出 `pthread_mutex_trylock()` / `TryEnterCriticalSection()` 也**不能**用来保护"每次回调都必须访问"的数据——
> 因为你是在赌能拿到锁，最坏情况下可能**永远拿不到**。

### 4. 隐形杀手

即使你自己的代码守规矩，还有两个环境问题：

- **垃圾回收**：Java/C# 的 GC 在音频线程跑起来就完了（除非有确定性实时 GC）
- **缺页（page fault）**：OS 可能把音频回调引用的内存换出到磁盘 →
  线程停顿等待换入。缓解手段：`mlock()`（macOS/Linux）/ `VirtualLock()`（Windows）

### 5. "不要相信任何第三方代码"

> 作者建议：**假设所有系统 API 都可能分配内存、使用锁、或有糟糕的最坏情况性能。**

他甚至说，自己唯一敢用的 OS 函数是
`QueryPerformanceCounter()`（Windows）和 `mach_absolute_time()`（macOS）——
**而且对这两个的实时性也不是 100% 确定。**

## 八条规则（原文总结）

**不要做**：

1. 不要分配或释放内存
2. 不要加锁（mutex）
3. 不要读写文件系统或做任何 I/O（**包括 `printf` / `NSLog` / GUI API**）
4. 不要调用可能阻塞等待的 OS 函数
5. 不要执行任何时间不可预测或最坏情况很差的代码
6. 不要调用任何"做了或可能做"上述事情的代码
7. 不要调用你不信任它会遵守这些规则的代码
8. 在 Apple 系统上遵守 Apple 的指南

**应该做**：

- 用**最坏情况**复杂度好的算法（理想是 O(1) 最坏情况）
- **把计算分摊到多个采样**，让 CPU 占用平滑，而不是"突发式"
- 在非实时线程里**预分配 / 预计算**
- 用**不共享的、音频回调专属的数据结构**，这样根本不用考虑并发和锁

## 怎么用它验证 AI 输出

> [!tip] 这是检查 AI 代码的第一道关卡
> 让 AI 写完 `processBlock` 后，对着这八条逐条查。
> AI 最常犯的三个：
>
> | AI 常写 | 违反 | 改成 |
> |---|---|---|
> | `std::vector::push_back` | 规则 1 | `prepareToPlay` 里 `resize`，音频线程只写索引 |
> | `std::string` 拼接 / 日志 | 规则 1、3 | 预格式化，或无锁队列交给其他线程 |
> | `std::mutex` 保护参数 | 规则 2 | `std::atomic` + [[参数平滑 parameter smoothing]] |
>
> 更彻底的检查：重载全局 `operator new`，在音频线程里调用时直接 `assert`。

## 相关

- [[实时音频线程契约]] — 本库基于此文的中文整理
- [[SPSC 队列]] — 原文提到的无锁 FIFO 方案
- [[denormal 数处理]] — 另一个实时性能陷阱
- [[插件验证工具]] — pluginval 会检测这类问题
- [[MOC - Realtime Engineering]]

> [!note] 待补充
> - 原文提到的后续文章（无锁队列详解）是否已发布
> - Tim Blechmann 的 Supernova 硕士论文（原文推荐的多核音频引擎资料）
