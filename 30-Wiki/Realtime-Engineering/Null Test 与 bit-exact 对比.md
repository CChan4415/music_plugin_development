---
title: Null Test 与 bit-exact 对比
type: wiki
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# Null Test 与 bit-exact 对比

> [!important] 一句话
> **Null test = 把两个信号相减，看差多少。**
> 它是"听起来一样"到"数值上一样"的桥梁——**位精确（bit-exact）是 null test 的极限结果**。

## 为什么这是最有力的测试

| 测试类型 | 能证明什么 |
|---|---|
| 听感测试 | "我觉得差不多" |
| 频响测试 | "在这个频率上一致" |
| **Null test** | **"在整个信号上，差异小于 X dB"** ✅ |

> [!tip] 一句话价值
> **Null test 把主观判断变成客观数字。**
> 而且它抓的是**任何**差异——包括你没想到要测的那些。

---

## 一、实测：不同误差对应多少 dB

**参考**：1kHz 正弦，幅度 0.5（-6.02 dBFS）。

| 误差幅度 | 相对 dB | 等价位深 | 判定 |
|---|---|---|---|
| 1e-2 | **-34.0 dB** | 5.6 bit | ❌ 明显可闻 |
| 1e-3 | **-54.0 dB** | 9.0 bit | 🟠 可能可闻 |
| 1e-4 | -74.0 dB | 12.3 bit | ✅ 基本不可闻 |
| 1e-5 | -94.0 dB | 15.6 bit | ✅ 完全不可闻 |
| 1e-6 | -114.0 dB | 18.9 bit | ✅ 完全不可闻 |
| 1e-7 | -134.0 dB | 22.3 bit | ✅ 浮点精度级 |
| 1e-9 | -174.0 dB | 28.9 bit | ✅ 浮点精度级 |

> [!important] 阈值约定（本库）
> | 差异 | 含义 |
> |---|---|
> | **< -100 dB** | ✅ **完全等价**（浮点误差级） |
> | < -60 dB | ✅ 听不出（但可能有相位差） |
> | > -40 dB | ❌ 肯定有问题 |

---

## 二、实测：几种"常见差异"的 null test 结果

| 场景 | 绝对差异 | **相对差异** | 解读 |
|---|---|---|---|
| 相同信号 | -400.0 dB | -394.0 dB | 数值零 |
| 加 1e-9 噪声 | -167.1 dB | -161.1 dB | 浮点噪声级 ✅ |
| **int16 截断 vs 四舍五入** | -90.3 dB | **-84.3 dB** | 1 LSB 差异 |
| **增益差 0.01 dB** | -64.8 dB | **-58.8 dB** | 可闻阈值边缘 |
| **延迟 1 采样** | -23.7 dB | **-17.7 dB** ⚠️ | **灾难性** |

> [!danger] 最后一行是最重要的发现
> **一个采样的延迟差 = -17.7 dB。**
>
> 这远高于"明显可闻"的阈值（-40 dB）。
> 这就是为什么：
> - **延迟报告错了会毁掉整个混音**（见 [[延迟报告 latency reporting]]）
> - **旁路时延迟不一致会造成相位错位**（见 [[旁路 bypass 的正确实现]]）
>
> **相位差对 null test 的影响远大于幅度差。**

> [!note] 为什么 1 个采样差这么多
> 对 1kHz @48kHz 的信号，1 个采样 = **7.5° 相位**。
> 相减后剩 `2·sin(3.75°) ≈ 0.13` 的相对幅度 ≈ -17.7 dB ≈ 理论值 $20\log_{10}(2\sin(\pi f/f_s))$。
>
> **频率越高，同样采样数的延迟造成的差异越大。**

---

## 三、Bit-exact 对比

> [!important] Bit-exact = 两个信号**逐位完全相同**
> 比 null test 更严格：null test 允许"差异很小"，bit-exact 要求**差异为零**。

**怎么测**：

```cpp
bool bitExact (const float* a, const float* b, size_t n)
{
    // ⚠️ 不能用 == 比较浮点（NaN != NaN，-0.0f == 0.0f）
    return std::memcmp (a, b, n * sizeof (float)) == 0;
}
```

> [!warning] 用 `memcmp` 而不是逐元素 `==`
> | 陷阱 | 说明 |
> |---|---|
> | `NaN != NaN` | 用 `==` 会判为不同，但位模式相同 |
> | `-0.0f == 0.0f` | 用 `==` 会判为相同，但位模式不同 |
> | denormal | 某些 CPU 模式下会被 flush 成 0（位模式变化） |
>
> **bit-exact 就是要看位模式**——所以必须 `memcmp`。

**什么时候需要 bit-exact**：

| 场景 | 需要吗 |
|---|---|
| 验证"优化没有改变行为" | ✅ 需要 |
| 验证"重构等价" | ✅ 需要 |
| 验证 C++ 实现 == Python 参考 | ❌ 不可能（浮点运算顺序不同） |
| 验证旁路透明 | 🟠 用 null test 更好（旁路可能纯延迟） |
| 跨平台一致性 | ❌ 通常做不到（见下） |

---

## 四、⚠️ 跨平台不可能 bit-exact

> [!danger] 这是一个必须接受的现实
> 同样的源码，在不同平台上**通常不会**产生 bit-exact 的结果：
>
> | 原因 | 影响 |
> |---|---|
> | **FMA 指令**（融合乘加） | x86/ARM 的 FMA 与分离乘加结果不同 |
> | **x87 80 位中间精度**（旧 x86） | 中间结果精度不同 |
> | **编译器优化重排** | 浮点不满足结合律 |
> | **`-ffast-math`** | 完全放弃 IEEE 语义 |
> | **denormal 处理**（FTZ/DAZ） | 不同 CPU 模式不同 |
> | **向量化** | SIMD 的求和顺序不同 |
>
> **所以：不要跨平台要求 bit-exact。**
> 应该要求 **null test < -100 dB**。

> [!tip] 实用做法
> | 对比对象 | 判据 |
> |---|---|
> | 同一平台，优化前 vs 优化后 | **bit-exact** ✅ 可行 |
> | 同一平台，C++ vs 参考实现 | < -100 dB |
> | macOS vs Windows | < -100 dB（**不要要求 bit-exact**） |
> | 旁路 vs 干信号 | 纯延迟时应当**数值零** |

---

## 五、常见陷阱：让你"停在 -90 dB"

> [!danger] 取整方式不同
> Python 的 `astype(int16)` 是**截断**，C 的 `lround` 是**四舍五入**。
> 差 1 LSB ≈ **-90 dB**。
>
> **实测**：int16 截断 vs 四舍五入 = **-84.3 dB**（相对）。
>
> **症状**：你的 null test 永远停在 -90 dB 而不是 -inf，
> 你会花几小时找"为什么不是完全相等"，而代码完全正确。
>
> **解法**：
> 1. 比较**浮点数**（不经过 WAV 编解码）
> 2. 或确保两边用**同样的**取整方式

**其他"停住"的原因**：

| 停在 | 原因 |
|---|---|
| -90 dB | 1 LSB（取整方式不同） |
| -84 dB | 同上（相对基准不同） |
| -17 dB | 延迟差 1 采样 |
| -6 dB | 增益差一倍 / 单声道相加 |
| -3 dB | 差 √2（功率 vs 幅度） |
| 不收敛 | 有随机成分（未固定种子） |

---

## 六、实现

```python
import numpy as np

def null_test (a, b, label="null test", align=False):
    """
    比较两个信号。
    align=True 时自动找最佳对齐（用于有延迟差异的情况）。
    """
    a = np.asarray (a, float)
    b = np.asarray (b, float)

    if align:
        # 用互相关找最佳延迟
        n = min (len(a), len(b))
        corr = np.correlate (a[:n], b[:n], mode='full')
        lag = np.argmax (np.abs (corr)) - (n - 1)
        if lag > 0:   a = a[lag:]
        elif lag < 0: b = b[-lag:]
        print (f"  （对齐：延迟 {lag} 采样）")

    n = min (len(a), len(b))
    d = a[:n] - b[:n]

    peak = 20*np.log10 (np.max (np.abs (d)) + 1e-300)
    ref  = 20*np.log10 (np.max (np.abs (a[:n])) + 1e-300)
    rel  = peak - ref

    if   rel < -100: verdict = "✅ 完全等价（浮点精度级）"
    elif rel < -60:  verdict = "✅ 听不出"
    elif rel < -40:  verdict = "🟠 边缘（可能可闻）"
    else:            verdict = "❌ 有实际差异"

    print (f"{label}:")
    print (f"  绝对 {peak:>8.1f} dBFS | 相对 {rel:>8.1f} dB | {verdict}")
    return rel

def bit_exact (a, b):
    """逐位比较（注意 NaN 与 -0.0）"""
    a = np.asarray (a, np.float32)
    b = np.asarray (b, np.float32)
    n = min (len(a), len(b))
    # ⚠️ 用 view 比较位模式，而不是 ==
    return np.array_equal (a[:n].view(np.uint32),
                           b[:n].view(np.uint32))
```

> [!tip] `bit_exact` 的实现要点
> `a.view(np.uint32)` 把 float 的位模式重新解释为整数，
> 这样 `-0.0f` 和 `0.0f` 会被正确判为**不同**，
> `NaN` 会被正确判为**相同**（位模式一致）。

---

## 七、用在哪

| 场景 | 怎么用 |
|---|---|
| **旁路透明性** | 旁路输出（对齐后）− 干信号 → 应 ≈ 0 |
| **优化正确性** | 优化前 vs 优化后 → 应 bit-exact |
| **重构等价** | 同平台内应 bit-exact |
| **C++ vs Python 参考** | < -100 dB |
| **参数平滑** | 检查平滑是否引入可闻差异 |
| **过采样往返** | 升→降 后与原信号比 |

```python
# 旁路测试（最重要）
bypassed = plugin.process_bypassed (impulse(8192))
active   = plugin.process_active (impulse(8192))

lat_b = int (np.argmax (np.abs(bypassed) > 1e-6))
lat_a = int (np.argmax (np.abs(active)   > 1e-6))
assert lat_b == lat_a, f"旁路延迟不一致！{lat_b} vs {lat_a}"

aligned = np.roll (bypassed, -lat_b)
null_test (aligned, impulse(8192), "旁路透明性")
# 期望：绝对差异 = 0（或 < -300 dB）
```

---

## 八、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **用 `==` 做 bit-exact 比较** | NaN/-0.0 判定错 | 用 `memcmp` / `view(uint32)` |
| 2 | **不检查延迟就 null test** | 得到 -17 dB 假差异 | 先对齐 |
| 3 | **期望跨平台 bit-exact** | 永远失败 | 改成 < -100 dB |
| 4 | **忘了取整方式差异** | 停在 -90 dB | 比浮点，或统一取整 |
| 5 | **用随机信号不固定种子** | 结果不可复现 | 固定种子 |
| 6 | **没归一化相对基准** | 数字无法解释 | 报"相对差异" |
| 7 | **以为 -60 dB 就"没问题"** | 相位差可能更大 | 看是否延迟问题 |
| 8 | **只测满幅信号** | 测不到小电平问题 | 加低电平测试 |
| 9 | **不用 `isfinite` 检查** | NaN 参与相减后全是 NaN | 先检查有限性 |

> [!danger] 第 2 条是"假阳性"的主要来源
> **不加对齐的 null test 通常会得到 -17 dB 左右**（因为实现总有微小延迟差）。
> 你会以为"我的实现有问题"，其实是**测试方法**问题。
>
> **要么先对齐，要么先测出延迟再补偿。**

---

## 九、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 结果 -17 dB | 延迟差 1 采样 | 先对齐 |
| 结果 -90 dB 不下降 | 1 LSB 取整差异 | 比浮点，或统一取整 |
| 结果全是 NaN | 输入有 NaN | `isfinite` 检查 |
| 结果每次不同 | 没固定随机种子 | 固定种子 |
| 跨平台永远不等 | 浮点实现差异 | 改判据为 < -100 dB |
| 相同信号却报差异 | 用了 `==` 且含 NaN | 用位模式比较 |
| 优化后差异很大 | 优化真的改了行为 | 查是不是用了 `-ffast-math` |

---

## 十、怎么验证

```python
import numpy as np

def null_test (a, b, label="null test", align=False):
    a, b = np.asarray(a,float), np.asarray(b,float)
    if align:
        n = min(len(a),len(b))
        corr = np.correlate(a[:n], b[:n], mode='full')
        lag = np.argmax(np.abs(corr)) - (n-1)
        if lag > 0: a = a[lag:]
        elif lag < 0: b = b[-lag:]
    n = min(len(a),len(b)); d = a[:n]-b[:n]
    peak = 20*np.log10(np.max(np.abs(d))+1e-300)
    ref  = 20*np.log10(np.max(np.abs(a[:n]))+1e-300)
    rel = peak-ref
    print(f"  {label}: 相对 {rel:>8.1f} dB")
    return rel

# 自检：这些结果应该符合预期
sr = 48000
t = np.arange(sr)/sr
x = 0.5*np.sin(2*np.pi*1000*t)

r1 = null_test(x, x.copy(), "相同信号")                    # → 数值零
r2 = null_test(x, np.roll(x,1), "延迟 1 采样")              # → 约 -17.7 dB ⚠️
r3 = null_test(x, np.roll(x,1), "延迟 1 采样（已对齐）", align=True)  # → 数值零

assert r1 < -200, "相同信号应该完全一致"
assert -25 < r2 < -10, f"1 采样延迟应约 -17.7 dB，实测 {r2:.1f}"
assert r3 < -200, "对齐后应该完全一致"
print("✅ null test 行为符合预期")
```

> [!important] 中间那个断言特别有价值
> `-25 < r2 < -10` 把"1 个采样延迟 = 约 -17.7 dB"这个知识**固化成了断言**。
> 以后任何人改动导致这个数字漂移，测试会失败。

---

## 相关

- [[MOC - Realtime Engineering]]
- [[音频回归测试]] — null test 在 CI 里的应用
- [[DSP 单元测试怎么写]]
- [[延迟报告 latency reporting]] — 为什么 1 采样延迟是灾难
- [[旁路 bypass 的正确实现]] — null test 的主要用途
- [[浮点音频表示]] — 为什么跨平台不能 bit-exact
- [[音频测量基础]] — 测量方法
- [[抖动 dither]] — 为什么降位深会停在 -90 dB

> [!note] 待补充
> - 自动对齐的更好算法（分数延迟对齐）
> - 在 CI 里做 null test 回归的门限设置
> - 实测：不同优化等级下的 bit-exact 情况
> - 频谱域的 null test（看差异集中在哪个频段）
