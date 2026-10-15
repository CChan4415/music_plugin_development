---
title: UndefinedBehaviorSanitizer
type: wiki
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# UndefinedBehaviorSanitizer

> [!important] 一句话
> **UBSan 抓"未定义行为"**——整数溢出、除零、越界转换、未对齐访问。
> 这些行为**在 C++ 标准里没有保证**，编译器可以任意处理。

## 为什么音频代码特别容易踩 UB

| UB 类型 | 音频里的典型场景 |
|---|---|
| 有符号整数溢出 | 累加器、计数器、索引相减 |
| 除零 | **采样率为 0**、Q 为 0、数量为 0 |
| 浮点转整数越界 | **NaN/Inf 转 int** → 未定义 |
| 移位越界 | 位运算优化、定点转换 |
| 未对齐访问 | 指针 reinterpret_cast 后访问 |

> [!danger] UB 最恶劣的特点
> **它可能"看起来正常工作"。**
> 编译器今天生成你想要的代码，明天换了优化等级/版本就不是了。
>
> **"在我机器上能跑"不能证明没有 UB。**

---

## 一、实测：五类 UB 全被抓到

**测试代码**（本库 `tools/sanitizer/ubsan_demo.cpp`）：

```bash
clang++ -std=c++17 -O1 -fsanitize=undefined -fno-sanitize-recover=all \
    ubsan_demo.cpp -o ubsan_demo
```

| case | 触发 | 实测输出 |
|---|---|---|
| **0** | 有符号整数溢出 | `runtime error: signed integer overflow: 2000000000 + 2000000000 cannot be represented in type 'int32_t'` |
| **1** | 除零 | `runtime error: division by zero` |
| **2** | 浮点转整数越界 | `runtime error: 1e+20 is outside the range of representable values of type 'int'` |
| **3** | 移位越界 | `runtime error: shift exponent 40 is too large for 32-bit type 'int32_t'` |
| **4** | 未对齐访问 | `runtime error: store to misaligned address 0x... for type 'double', which requires 8 byte alignment` |

> [!important] 每一类都**精确定位到源码行列号**
> ```
> ubsan_demo.cpp:9:27:  runtime error: signed integer overflow ...
> ubsan_demo.cpp:15:24: runtime error: division by zero
> ubsan_demo.cpp:21:26: runtime error: 1e+20 is outside the range ...
> ubsan_demo.cpp:27:27: runtime error: shift exponent 40 is too large ...
> ubsan_demo.cpp:34:13: runtime error: store to misaligned address ...
> ```
>
> **5/5 全部抓到。** 这就是 UBSan 的价值。

---

## 二、编译选项

```bash
clang++ -std=c++17 -O1 -g \
    -fsanitize=undefined \
    -fno-sanitize-recover=all \
    myfile.cpp -o mytest
```

| 选项 | 作用 |
|---|---|
| `-fsanitize=undefined` | 开启 UBSan |
| **`-fno-sanitize-recover=all`** | **出错立即终止**（否则只打印警告继续跑） |
| `-g` | 行号 |

> [!danger] `-fno-sanitize-recover=all` 非常关键
> **默认行为**：UBSan 打印警告然后**继续执行**（因为"恢复"了）。
> 结果：CI 里可能**跑成功**，你根本没注意到警告。
>
> 加上这个选项后，出错**立即非零退出** → CI 能抓到。

> [!tip] 一次开三个 sanitizer（本库推荐组合）
> ```bash
> clang++ -std=c++17 -O1 -g \
>     -fsanitize=address,undefined \
>     -fno-omit-frame-pointer \
>     -fno-sanitize-recover=all \
>     test.cpp -o test
> ```
> ⚠️ **不要**同时开 ASan 和 TSan（两者不兼容）。

---

## 三、音频代码的高危 UB 清单

### 1. 除零（最常见）

```cpp
// ❌ 用户可以把这些设成 0
float ratio = inSamples / outSamples;          // outSamples = 0 → UB
float q = freq / Q;                            // Q = 0 → UB
float norm = 1.0f / numChannels;               // 0 声道 → UB

// ✅ 钳制
const int outN = std::max (1, outSamples);
const float Qs = std::max (0.001f, Q);
```

> [!warning] 采样率相关的除零
> 宿主**不会**给你 0 采样率，但：
> ```cpp
> float period = sampleRate / freq;     // freq = 0 → inf → 后续 UB
> int idx = (int) (time * sampleRate);  // time = NaN → UB
> ```

### 2. 浮点转整数越界

```cpp
// ❌ NaN / Inf / 超范围 转 int 是 UB
int idx = (int) (someFloat * scale);          // someFloat 可能是 NaN

// ✅ 先检查
float v = someFloat * scale;
if (!std::isfinite (v)) v = 0.0f;
v = std::clamp (v, (float) INT32_MIN/2, (float) INT32_MAX/2);
int idx = (int) v;
```

> [!danger] 这是音频里最"阴"的一类 UB
> NaN **必然**会在音频链里出现（除以 0、Inf - Inf、0 × Inf）。
> 一旦 NaN 进了 `(int)` 转换 → **未定义行为** → 可能是任意值。
>
> **实测**（本库验证）：
> ```cpp
> float nan_v = std::numeric_limits<float>::quiet_NaN();
> int idx = (int)(nan_v * 100.0f);          // ← UB
> ```
> ```
> ubsan: runtime error: nan is outside the range of representable values of type 'int'
> ```
>
> UBSan 精确报出了 `nan` 这个词——**这就是它比"崩溃了"有用得多的地方**。
>
> 见 [[浮点音频表示]] 的 NaN 传播实测。

### 3. 有符号整数溢出

```cpp
// ❌ 有符号溢出是 UB（无符号是定义好的回绕）
int32_t a = x + y;                 // 可能溢出

// ✅ 用无符号做索引运算（定义好的回绕）
size_t idx = (size_t) w - (size_t) r;   // 回绕行为有定义
```

> [!tip] 音频里用 `size_t`/`uint64_t` 做索引是**故意**的
> [[SPSC 队列]] 里 `w - r` 就是靠**无符号回绕**的正确行为。
> 换成有符号反而会引入 UB。

### 4. 未对齐访问

```cpp
// ❌ 从字节流直接 reinterpret_cast 后访问
char* buf = ...;
double* p = (double*) (buf + 1);     // 可能未对齐 → UB
*p = 1.0;

// ✅ 用 memcpy（编译器会优化成合适的指令）
double v = 1.0;
std::memcpy (buf + 1, &v, sizeof (v));
```

> [!note] arm64 和 x86 的差异
> - **x86-64**：未对齐访问**通常**能工作（慢一点）
> - **arm64**：某些指令**真的会崩**（实测 UBSan 会报）
>
> **这就是为什么"在我 Intel Mac 上没事"不代表没问题。**

### 5. 移位越界

```cpp
// ❌ 移位量 >= 位宽 是 UB
uint32_t mask = 1u << n;          // n >= 32 → UB

// ✅ 检查
uint32_t mask = (n < 32) ? (1u << n) : 0u;
```

---

## 四、和 ASan 的分工

| | ASan | UBSan |
|---|---|---|
| 内存越界 | ✅ | ❌ |
| 释放后使用 | ✅ | ❌ |
| **整数溢出** | ❌ | ✅ |
| **除零** | ❌ | ✅ |
| **浮点转整数越界** | ❌ | ✅ |
| **未对齐访问** | 🟠 部分 | ✅ |
| 数据竞争 | ❌ | ❌（要 TSan） |

> [!important] 三个都要用
> | 工具 | 抓什么 | 能同时用吗 |
> |---|---|---|
> | **ASan** | 内存错误 | ✅ 可与 UBSan |
> | **UBSan** | 未定义行为 | ✅ 可与 ASan |
> | **TSan** | 数据竞争 | ❌ **不能**与 ASan 同时 |

---

## 五、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **忘了 `-fno-sanitize-recover=all`** | 警告被忽略，CI 通过 | 检查编译选项 |
| 2 | **NaN 直接转 int** | UB（实测会报） | `isfinite` + `clamp` |
| 3 | **除以可能为 0 的参数** | UB | 钳制分母 |
| 4 | **有符号做索引运算** | 溢出 UB | 用无符号 |
| 5 | **`reinterpret_cast` 后直接访问** | 未对齐 UB | 用 `memcpy` |
| 6 | **同时开 ASan + TSan** | 编译/运行错误 | 分开构建 |
| 7 | **以为 UBSan 只在 Debug 有效** | 不用 | `-O1` 也能用 |
| 8 | **用 `-O2` 掩盖 UB** | 测不到 | 用 `-O1` |
| 9 | **测完就删掉 sanitizer 配置** | 以后不再检测 | 保留独立构建目标 |

> [!danger] 第 2 条是音频专属的高危项
> AI 写 `int idx = (int)(phase * tableSize)` 看起来天经地义。
> 但 `phase` 一旦是 NaN（前面某处除了 0），这就是 UB。
>
> **而 NaN 在音频链里几乎必然出现。**
> 见 [[浮点音频表示]]。

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| CI 里 UBSan 有警告但通过 | 没加 `-fno-sanitize-recover` | 加上 |
| 本地没报错，CI 报错 | 优化等级/编译器不同 | 统一用 `-O1` |
| ASan 和 TSan 一起编译失败 | 不兼容 | 分开构建 |
| 报告的行号不对 | 缺 `-g` | 加 `-g` |
| x86 没问题、arm64 崩 | 未对齐访问 | 用 `memcpy` |
| 只在特定输入下报错 | 正常（UB 依赖具体值） | 覆盖边界参数 |

---

## 七、怎么验证（实用流程）

```bash
#!/bin/bash
# 完整 sanitizer 测试（本库推荐流程）
set -e

echo "=== 构建（ASan + UBSan）==="
clang++ -std=c++17 -O1 -g \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -fno-sanitize-recover=all \
    test_dsp.cpp -o test_dsp_san

echo "=== 覆盖多种参数（关键）==="
for bs in 1 16 64 256 512 1024 4096; do
    for sr in 44100 48000 96000 192000; do
        printf "  blockSize=%-5s sampleRate=%-7s " "$bs" "$sr"
        ./test_dsp_san "$bs" "$sr" > /dev/null 2>&1 && echo "✅" || { echo "❌"; exit 1; }
    done
done

echo ""
echo "🎉 无内存错误、无未定义行为"
```

**边界输入清单**（音频必须测的）：

| 输入 | 为什么危险 |
|---|---|
| **NaN** | 转 int 是 UB |
| **Inf** | 同上 |
| **0** | 除零 |
| **负数**（不该出现的地方） | 索引/移位 |
| **极大值** | 溢出、越界转换 |
| **0 长度缓冲** | 循环边界 |

```cpp
// 把这些喂进你的 processBlock
const float edgeCases[] = {
    std::numeric_limits<float>::quiet_NaN(),
    std::numeric_limits<float>::infinity(),
    -std::numeric_limits<float>::infinity(),
    0.0f, -0.0f,
    1e30f, -1e30f,
    std::numeric_limits<float>::denorm_min(),
};
```

---

## 相关

- [[MOC - Realtime Engineering]]
- [[AddressSanitizer]] — 内存错误（互补）
- [[ThreadSanitizer 与内存序]] — 数据竞争
- [[浮点音频表示]] — NaN/Inf 的传播
- [[插件验证工具]] — sanitizer 在验证体系里的位置
- [[实时音频线程契约]]
- [[音频回归测试]] — CI 里怎么跑

> [!note] 待补充
> - MSan（未初始化内存）在音频里的应用
> - UBSan 的 `-fsanitize=float-divide-by-zero` 等细分选项
> - 在 GitHub Actions 里跑 tri-sanitizer 的完整配置
> - UBSan 的性能开销实测
