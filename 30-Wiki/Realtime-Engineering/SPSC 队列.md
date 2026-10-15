---
title: SPSC 队列
type: wiki
domain: realtime
status: solid
confidence: high
sources: ["[[Bencina - Real-time audio programming 101]]"]
tags: [cpp, gotcha, recipe]
created: 2026-10-15
updated: 2026-10-15
---

# SPSC 队列

> [!important] 一句话
> **SPSC = Single Producer, Single Consumer**（单生产者单消费者）。
> 一个线程只写、另一个线程只读，**不需要锁**——这是音频线程与其他线程通信的标准方式。

## 为什么音频线程必须用它

音频线程**不能加锁**（优先级反转）、**不能分配**（时间不可预测）。
但它又必须和 GUI 线程通信（传电平表数据、接收参数、报告事件）。

**SPSC 队列**正好满足：

| 需求 | SPSC 如何满足 |
|---|---|
| 不加锁 | 用原子索引，不用 mutex |
| 不分配 | 容量在 `prepare` 时固定 |
| 最坏情况可预测 | O(1) 的 push/pop |
| 线程安全 | 单生产单消费 → 无竞争 |

> [!note] 为什么"单"生产"单"消费很重要
> 多生产者需要 CAS 循环（可能重试、时间不可预测）。
> **音频线程只做单生产者**，就能保持 O(1) 无重试。

---

## 一、核心结构

```
        write index (原子)                read index (原子)
              ↓                                ↓
   ┌──────────────────────────────────────────────┐
   │  [0] [1] [2] [3] [4] [5] [6] [7] ... [N-1]   │  ← 环形缓冲
   └──────────────────────────────────────────────┘
              ↑                                ↑
         生产者只写这里                    消费者只读这里
```

**关键点**：
- 生产者**只修改** `writeIndex`
- 消费者**只修改** `readIndex`
- 两个索引都是 `std::atomic`

---

## 二、实现

```cpp
#include <atomic>
#include <vector>
#include <cstddef>

// 单生产者单消费者无锁环形队列
template <typename T, size_t Capacity>
class SpscQueue
{
public:
    static_assert ((Capacity & (Capacity - 1)) == 0, "容量必须是 2 的幂");

    // ⚠️ 只在非实时线程调用（构造函数可以分配）
    SpscQueue() { buffer.resize (Capacity); }

    // 生产者调用（音频线程可以安全调用：无分配、无锁、O(1)）
    bool push (const T& item) noexcept
    {
        const auto w = writeIndex.load (std::memory_order_relaxed);
        const auto r = readIndex.load (std::memory_order_acquire);

        if (w - r >= Capacity)      // 满了
            return false;           // ⚠️ 直接失败，绝不等待

        buffer[w & (Capacity - 1)] = item;
        writeIndex.store (w + 1, std::memory_order_release);
        return true;
    }

    // 消费者调用
    bool pop (T& out) noexcept
    {
        const auto r = readIndex.load (std::memory_order_relaxed);
        const auto w = writeIndex.load (std::memory_order_acquire);

        if (w == r)                 // 空了
            return false;

        out = buffer[r & (Capacity - 1)];
        readIndex.store (r + 1, std::memory_order_release);
        return true;
    }

private:
    std::vector<T> buffer;
    // ⚠️ 两个索引放在**不同的缓存行**，避免伪共享（false sharing）
    alignas(64) std::atomic<size_t> writeIndex { 0 };
    alignas(64) std::atomic<size_t> readIndex  { 0 };
};
```

> [!tip] 两个细节
> 1. **容量用 2 的幂** → `& (Capacity-1)` 代替取模（更快）
> 2. **`alignas(64)` 分开索引** → 避免伪共享

> [!important] 伪共享的代价是**实测的，不是理论**
> 两个索引各 2000 万次原子自增（Apple Silicon arm64，本库实测）：
>
> | 布局 | 耗时 |
> |---|---|
> | 相邻索引（Packed） | **240.0 ms** |
> | `alignas(64)`（Padded） | **31.9 ms** |
> | **比值** | **7.51×** |
>
> （另一次测量得到 208.7 / 33.3 ms = 6.27×；比值随机器状态波动，但量级稳定）
>
> **原因**：两个索引在同一缓存行 → 每个核心的写入都让对方的缓存行失效 →
> 缓存行在核心间"乒乓"。分开到不同缓存行就消除了这个冲突。
>
> **一行 `alignas(64)` 换来 7 倍性能**，这是音频代码里性价比最高的优化之一。

---

## 三、内存序：为什么不能全用 relaxed

这是本页最重要的部分。

| 操作 | 内存序 | 为什么 |
|---|---|---|
| 读自己的索引 | `relaxed` | 只有自己写，无需同步 |
| 读对方的索引 | **`acquire`** | 保证能看到对方写入的数据 |
| 写自己的索引 | **`release`** | 保证数据先于索引可见 |

**`release` / `acquire` 配对的作用**：

```
生产者：                         消费者：
  buffer[i] = data    ← ①         w = writeIndex.load(acquire)  ← ④
  writeIndex.store(release) ← ②   out = buffer[i]               ← ⑤
                                   r = readIndex.store(release)  ← ⑥

② 的 release 保证 ① 对 ④ 的 acquire 可见
→ 消费者看到新索引时，一定能看到对应的数据
```

> [!danger] 全用 `relaxed` 会发生什么（实测）
> **实测环境**：Apple Silicon (arm64)，1 生产者 + 1 消费者，200 万条消息。
>
> | 配置 | 撕裂/陈旧数据 |
> |---|---|
> | 索引全 `relaxed` + 32 字节多字段消息 | **509 / 6759 / 4391 次**（三次运行） |
> | 索引用 `release`/`acquire` + 同样消息 | **0 次** |
>
> **撕裂** = 消费者读到"索引说数据已就绪，但数据只写了一半"。
>
> 对音频的意义：不是"稍微不对"，而是**读到垃圾值** →
> 可能变成爆音、NaN、甚至让反馈回路发散。

> [!note] 为什么 64 位标量通常"侥幸正确"
> arm64 和 x86-64 上，对齐的 64 位 load/store **天然是单指令原子的**。
> 所以如果你的消息是单个 `uint64_t`，用 relaxed 也可能"跑起来没问题"。
>
> **但这是未定义行为**（C++ 内存模型不保证），
> 编译器优化、换架构、换编译器版本都可能让它崩。
> **不要依赖侥幸。**

---

## 四、⚠️ 内存序错误无法靠测试发现

> [!danger] 这是本页最反直觉、也最重要的一条

**实测结论**（本库 2026-10-15）：

| # | 结论 |
|---|---|
| ① | **`-fsanitize=thread` 不会把 relaxed 索引报成 data race** |
| ② | 64 位标量消息在 arm64 上通常侥幸正确（单指令 load/store 天然原子） |
| ③ | 换成 32 字节多字段消息后，relaxed 版本**真的会撕裂**（实测 509~6759 次 / 200 万） |

> [!important] 怎么理解第 ① 条
> **原子操作本身不是 data race**——TSan 不会因为两个线程访问同一个
> `std::atomic` 而报警（不管内存序是什么）。这是正确的行为。
>
> 但 TSan **会**报非原子访问的竞争：如果 payload 是普通数组，
> 生产者的写和消费者的读构成 data race → TSan 会报。
>
> **实测**（本库独立验证）：
> - 非原子 payload + relaxed 索引 → TSan 报 **8 条 data race** ✅
> - 原子 payload + relaxed 索引 → TSan 报 **0 条**，实际撕裂 **0 次**
>
> **所以 TSan 能抓到"非原子访问"这一半，抓不到"内存序不足"这一半。**
> 内存序不足只有在多字段 payload + 特定时序下才表现为撕裂，
> 而 TSan 不会把"时序问题"报成 race。

> [!warning] 实践结论
> **内存序错误只能靠"写对"来避免，不能靠测试发现。**
>
> - 单元测试可能通过（时序不对）
> - TSan 可能不报（原子操作不是 race）
> - 只在你换了架构/编译器/负载之后才崩
>
> **所以：照抄正确的模式，不要自己发明。**

---

## 五、满了怎么办：丢弃，绝不阻塞

> [!important] 音频线程的唯一选择
> **push 失败就丢弃，然后继续。**

**实测：丢弃率 vs 队列容量**（100 万条，消费者故意慢一点）：

| 容量（可存） | 丢弃数 | 丢弃率 |
|---|---|---|
| 16 (15) | 659794 | **65.98%** |
| 1024 (1023) | 16524 | 1.65% |
| 65536 (65535) | **0** | **0.00%** |

> [!tip] 怎么读
> - **容量越大丢弃越少**，但**丢弃永远可能发生**
> - 对**电平表数据**：丢几个无所谓（下一帧就更新了）
> - 对**参数变化**：不能丢（用 `std::atomic` 存最新值，不是队列）
> - 对**事件/命令**：不能丢 → 容量要足够大，或改用其他机制

> [!danger] 绝对不要做的事
> ```cpp
> // ❌ 绝不要"等队列有空位"
> while (!queue.push(x)) { std::this_thread::yield(); }
> ```
> 这在音频线程里 = **死等** = 必然爆音。
> 而且在单生产者单消费者场景下可能**永久死锁**（消费者也在等生产者）。

---

## 六、容量到底能存几个：两种设计，别混淆

> [!danger] 这一节记录一个**本库自己犯过的错**（2026-10-15）
> 初版这里写的是"判满条件是 `w - r >= Capacity`，所以实际只能存 `Capacity - 1` 个"。
> **这句话和本节上面的代码自相矛盾，而且是错的。** 实测（逐字复制 §2 的代码，clang++ -O2）：
>
> ```
> 声明容量 8，连续 push 到满 → 成功 8 个（不是 7）
> 推入 0..7 后依次 pop       → 0 1 2 3 4 5 6 7（无覆盖、无损坏）
> ```
>
> **§2 的代码是对的，初版的解释是错的。**

### 为什么会搞混：这是两种不同的设计

| 设计 | 索引形态 | 判满条件 | 实际可存 | 能否区分满/空 |
|---|---|---|---|---|
| **A. 单调计数器**（§2 用的） | 64 位递增，**只在取数组下标时才掩码** | `w - r >= Capacity` | **Capacity** | ✅ 能（`w-r` 就是元素个数） |
| **B. 已掩码索引** | 存进索引时就已经 `& (Capacity-1)` | `w == r` 表示空 | **Capacity − 1** | ❌ 不能（满和空都是 `w == r`） |

**设计 A 不需要牺牲槽位**：`w` 和 `r` 永不回绕（要 2⁶⁴ 次操作才溢出，
48 kHz 下约 1200 万年），`w - r` 直接就是元素个数。
`w-r == 8`（满）和 `w-r == 0`（空）**完全可区分**——
因为比较用的是**未掩码**的值，而 `w & 7 == r & 7` 只是**数组下标**相同，
`buffer[w & 7]` 和 `buffer[r & 7]` 指向同一个物理槽位，但语义上一个是"下一个要写的"、
一个是"下一个要读的"，**不构成歧义**。

**设计 B 才需要牺牲一个槽位**，因为它把回绕后的值存了回去，丢掉了"绕了几圈"的信息。

> [!warning] 无符号回绕是这里的**特性**，不是 bug
> `w - r` 用 `size_t`（无符号）计算。即使 `w` 溢出回绕到 0，
> `w - r` 在模 2⁶⁴ 意义下**仍然是正确的元素个数**（只要队列里的元素数 < 2⁶⁴，必然成立）。
> **不要"为了安全"把它改成有符号或加判断**——那会引入真正的 bug。

> [!note] 那本库的测试脚本为什么打印"声明容量 8，实际可存 7"？
> 因为 `50-Playground/tools/cpp/spsc_queue_test.cpp` 用的是**设计 B**
> （`usableCapacity = Capacity - 1`，判满 `w - r >= usableCapacity`）。
> 那是**另一种合法设计**，不是本页 §2 的代码。
> **两处都对，但说的不是同一件事**——这正是初版混淆的根源。

> [!tip] 该选哪个
> | | 设计 A（单调计数器） | 设计 B（牺牲槽位） |
> |---|---|---|
> | 有效容量 | Capacity | Capacity − 1 |
> | 判满 | `w - r >= Capacity` | `w - r >= Capacity - 1` |
> | 溢出风险 | 2⁶⁴ 次操作后（可忽略） | 无 |
> | 常见度 | **现代实现的主流**（JUCE `AbstractFifo`、folly、rigtorp 都用这个思路） | 教科书常见 |
>
> **推荐设计 A**：多一个槽位，且 `w - r` 天然给出元素个数（可以直接用来做 UI 的"队列深度"显示）。

---

## 七、JUCE 的 `AbstractFifo`

JUCE 提供了现成的实现：

```cpp
juce::AbstractFifo fifo { 512 };

// 生产者
int start1, size1, start2, size2;
fifo.prepareToWrite (numToWrite, start1, size1, start2, size2);
// 写入 buffer[start1..start1+size1) 和 buffer[start2..start2+size2)
fifo.finishedWrite (size1 + size2);

// 消费者
fifo.prepareToRead (numToRead, start1, size1, start2, size2);
// 读取...
fifo.finishedRead (size1 + size2);
```

> [!note] `AbstractFifo` 的特点
> - **两个区段**（`start1/size1` + `start2/size2`）：因为环形缓冲的数据可能跨越回绕点
> - 内部用 `std::atomic<int>` 索引
> - ⚠️ **具体的内存序实现需查你锁定版本的源码确认**
>
> **建议**：先用 `AbstractFifo` 跑通，理解了两段式 API 之后再考虑自己写。

---

## 八、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **索引全用 `relaxed`** | 撕裂/陈旧数据（实测 509~6759/200万） | 检查 store 是否 `release`、load 是否 `acquire` |
| 2 | **用 `std::mutex` 保护队列** | 优先级反转 | grep `mutex` |
| 3 | **满了就 `while` 等** | 音频线程死等 → 爆音 | 检查 push 失败的处理 |
| 4 | **在音频线程 `resize` 队列** | 分配内存 | 容量必须是编译期常量或 prepare 时固定 |
| 5 | **两个索引相邻** | 伪共享，性能下降 | 检查 `alignas(64)` |
| 6 | **用取模而非位与** | 稍慢（非致命） | 容量用 2 的幂 + `&` |
| 7 | **多生产者共用** | 索引竞争 → 数据损坏 | 确认只有一个线程 push |
| 8 | **payload 是 `std::vector`/`std::string`** | 拷贝时分配 | payload 必须是 POD 或固定大小 |
| 9 | **以为"测试通过就没问题"** | 内存序错误测不出来 | 见第四节 |

> [!warning] 第 1 条和第 9 条是一对
> AI 写 relaxed 索引时**不会觉得有问题**，因为：
> - 代码看起来"用了原子，应该安全"
> - 测试很可能通过
> - TSan 也不会报（原子操作不是 race）
>
> **只有你明确知道"写索引用 release、读索引用 acquire"这个规则，才能写对。**

---

## 九、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 偶发爆音 / 垃圾数据 | 内存序不足（撕裂） | store 用 `release`，load 用 `acquire` |
| 音频线程卡住 | 满了在等待 | 改成丢弃 |
| CPU 占用异常高 | 伪共享（实测慢 **7.5×**） | `alignas(64)` 分开索引 |
| 数据偶尔丢失 | 队列太小 | 加大容量，或改用原子变量 |
| 崩溃在 push/pop | payload 含动态分配 | 改 POD |
| 测试全过但线上崩 | 内存序错误不可测 | 见第四节 |
| 容量比预期少 1 | 判满条件 | 正常（见第六节） |

---

## 十、怎么验证

```cpp
// 本库的测试脚本（已验证可运行）
// 50-Playground/tools/cpp/spsc_queue_test.cpp
```

**测试项与实测结果**（`spsc_queue_test.cpp`，用的是 §6 里的**设计 B**）：

| 测试 | 结果 |
|---|---|
| 基本正确性与容量边界 | ✅ 声明容量 8 → 实际可存 7（设计 B 的预期行为） |
| 真实并发（100 万条） | ✅ 收到 + 丢弃 = 1000000（守恒，无丢失） |
| 乱序 / 数据损坏 | ✅ 无 |
| 丢弃率 vs 容量 | 容量 16 → 0.76%；容量 65536 → 0% |
| **索引全 relaxed** | ⚠️ **本测试测不出这个 bug**（见第四节） |

> [!note] 实测数字会随机器负载浮动
> 上表"丢弃率"一行在不同运行间差异很大（实测容量 16 时见过 0.76% / 21% / 41% / 66%）。
> **原因**：生产者和消费者是竞争关系，谁快谁慢取决于调度和 CPU 负载。
> **可以稳定复现的结论只有定性方向**：容量越大丢弃越少，容量 65536 时通常为 0。
> 不要引用具体百分比。

> [!danger] 最后一行是重点
> **单靠功能测试无法验证内存序正确性。**
> 必须：
> 1. **代码审查**（检查每个 store/load 的内存序）
> 2. **压力测试 + 多架构**（arm64 和 x86-64 行为可能不同）
> 3. **TSan**（能抓非原子竞争，抓不到内存序不足）
>
> 三条都做，也不保证 100%——**所以照抄正确模式最重要**。

```bash
# 编译运行本库的测试
clang++ -std=c++17 -O2 50-Playground/tools/cpp/spsc_queue_test.cpp -o spsc && ./spsc

# 内存序反例（能看到撕裂）
clang++ -std=c++17 -O2 50-Playground/tools/cpp/memory_order_demo.cpp -o mo && ./mo

# TSan（能抓非原子竞争）
clang++ -std=c++17 -O1 -fsanitize=thread spsc_queue_test.cpp -o spsc_tsan && ./spsc_tsan
```

---

## 相关

- [[MOC - Realtime Engineering]]
- [[实时音频线程契约]] — 为什么不能加锁/分配
- [[参数平滑 parameter smoothing]] — 参数用原子变量而非队列
- [[延迟报告 latency reporting]]
- [[旁路 bypass 的正确实现]]
- [[AddressSanitizer]] / [[UndefinedBehaviorSanitizer]] — 其他 sanitizer
- [[性能剖析]] — 伪共享的影响
- [[Bencina - Real-time audio programming 101]] — 无锁队列的权威讨论

> [!note] 待补充
> - 多生产者版本的实现与代价（CAS 循环）
> - x86-64 上的撕裂复现（本页数据是 arm64）
> - `AbstractFifo` 的内存序（需查源码）
> - 用 `std::atomic<T>` 直接传小对象（无锁但可能非无等待）
