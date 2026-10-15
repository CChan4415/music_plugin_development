---
title: AddressSanitizer
type: wiki
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# AddressSanitizer

> [!important] 一句话
> **ASan 在编译时插入检查，运行时抓内存错误**——越界、释放后使用、内存泄漏。
> 对音频插件尤其重要，因为**你的延迟线/缓冲区越界只在特定样本数下触发**。

## 为什么音频开发特别需要它

| 音频代码的特点 | 后果 |
|---|---|
| 大量环形缓冲 + 索引运算 | 越界很容易 |
| 缓冲区大小依赖 block size / 采样率 | **只在特定参数下越界** |
| 缓冲区大小依赖宿主 | 用户机器上才崩 |
| 释放后使用（换采样率时重建） | 偶发崩溃 |

> [!danger] 音频 bug 的典型形态
> **开发时跑得好好的，用户那边偶尔爆音/崩溃。**
> 因为你的 `prepareToPlay` 用了 512 的块大小测试，
> 而用户宿主给的是 1024 —— 某个索引就多走了一步。

---

## 一、实测：ASan 抓越界

```cpp
#include <vector>
#include <cstdio>
int main (int argc, char** argv)
{
    std::vector<float> buf (16, 0.0f);
    int idx = (argc > 1) ? 20 : 8;      // 故意越界
    printf ("写入 buf[%d]（容量 16）\n", idx);
    buf[(size_t) idx] = 1.0f;           // ← 越界
    printf ("值 = %.1f\n", buf[(size_t) idx]);
    return 0;
}
```

```bash
clang++ -std=c++17 -O1 -fsanitize=address -g asan_test.cpp -o asan_test

./asan_test              # 不越界
#   写入 buf[8]（容量 16）
#   值 = 1.0

./asan_test overflow     # 越界
#   =================================================================
#   ==17512==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6060000002b0
#   WRITE of size 4 at 0x6060000002b0 thread T0
#       #0 0x... in main+0x1d8 (asan_test:arm64+0x100000a40)
```

> [!important] 关键信息
> - **错误类型**：`heap-buffer-overflow`
> - **操作**：`WRITE of size 4`（写 4 字节 = 一个 float）
> - **地址**：`0x6060000002b0`
> - **调用栈**：精确到函数
>
> **这些信息足以立刻定位问题。** 没有 ASan 时你只会看到"崩溃"或"没崩"。

---

## 二、常用编译选项

```bash
# 基础用法
clang++ -std=c++17 -O1 -g -fsanitize=address myfile.cpp -o mytest

# 推荐组合（本库用这个）
clang++ -std=c++17 -O1 -g \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -fno-sanitize-recover=all \
    mytest.cpp -o mytest
```

| 选项 | 作用 |
|---|---|
| `-fsanitize=address` | 开启 ASan |
| `-fsanitize=address,undefined` | 同时开 ASan + UBSan |
| `-fno-omit-frame-pointer` | 保留栈帧 → **更清晰的调用栈** |
| `-fno-sanitize-recover=all` | 出错立即终止（不继续跑） |
| `-g` | 调试符号 |
| `-O1` | ⚠️ **不要用 -O2**（优化会掩盖部分错误） |

> [!warning] 为什么用 `-O1` 而不是 `-O2`
> 高优化等级会**内联、重排、消除**代码，
> 有些越界会被优化掉（因为编译器"证明"它不会发生）。
>
> **ASan 建议用 `-O1`**（既不太慢，又能保留足够结构）。

---

## 三、ASan 能抓什么

| 错误类型 | 说明 | 音频场景 |
|---|---|---|
| **heap-buffer-overflow** | 堆越界 | 延迟线索引超出 |
| **stack-buffer-overflow** | 栈越界 | 固定数组写越界 |
| **global-buffer-overflow** | 全局越界 | 查找表索引越界 |
| **use-after-free** | 释放后使用 | 换采样率后用了旧缓冲 |
| **double-free** | 重复释放 | 手动管理内存时的错 |
| **memory leak** | 内存泄漏 | 端点检测（退出时报告） |
| **use-after-return** | 返回后使用栈变量 | 返回了局部变量的指针 |

> [!tip] 音频里最常见的三种
> 1. **heap-buffer-overflow**（延迟线、FFT 缓冲）
> 2. **use-after-free**（`prepareToPlay` 重建对象）
> 3. **memory leak**（每次 prepare 都分配但没释放）

---

## 四、抓内存泄漏

```bash
# macOS 上 ASan 的 LeakSanitizer 支持有限
# 用 Apple 自带的 leaks 工具
leaks --atExit -- ./mytest
```

```bash
# Linux / CI 上
ASAN_OPTIONS=detect_leaks=1 ./mytest
```

> [!warning] ⚠️ macOS 的 LeakSanitizer 支持不完整
> Apple 的 clang **不包含**完整的 LSan。
> 在 macOS 上用 `leaks` 工具，或者**在 Linux CI 里跑泄漏检测**。
>
> ⚠️ 具体支持情况**需查你的工具链版本**。

---

## 五、在插件里怎么用

**问题**：ASan 需要重新编译**整个插件和宿主**（或至少插件）。

```bash
# 用 CMake 加 sanitizer（示例）
cmake -B build-asan \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
    -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined"
cmake --build build-asan
```

> [!important] 两种测试方式
> | 方式 | 优点 | 缺点 |
> |---|---|---|
> | **独立测试程序** | 简单、快、可控 | 测不到宿主交互 |
> | **带 ASan 的插件 + 宿主** | 最真实 | 宿主也要能带 sanitizer 跑 |
>
> **推荐**：先用**独立测试程序**覆盖 DSP 逻辑（本库的做法），
> 再用带 ASan 的插件在宿主里跑关键路径。
>
> ⚠️ 宿主是已编译好的二进制，**不能**给宿主加 ASan。
> 但你可以在插件里用 `DYLD_INSERT_LIBRARIES` 加载 ASan 运行时
> （⚠️ 具体可行性需实测）。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **用 `-O2` 配 ASan** | 部分错误被优化掉 | 用 `-O1` |
| 2 | **忘了 `-g`** | 调用栈没有行号 | 加 `-g` |
| 3 | **以为 ASan 能抓所有内存错误** | 漏掉未初始化读取 | 那要 MSan |
| 4 | **在 macOS 上期待 LSan** | 无输出以为没泄漏 | 用 `leaks` 或 Linux CI |
| 5 | **只跑一次不越界的参数** | 测不到越界 | 用多种 block size 测 |
| 6 | **以为 ASan 很慢不能用** | 放弃使用 | 慢 2-3 倍，测试足够 |
| 7 | **忘了 `-fno-omit-frame-pointer`** | 调用栈难读 | 加上 |
| 8 | **测试完就删掉 ASan 配置** | 以后不再检测 | 保留一个 asan 构建目标 |

> [!danger] 第 5 条最实际
> ASan 只在**真的越界时**报告。
> 如果你的测试只用了 512 的 block size，而 bug 在 1024 时出现——
> **ASan 什么都不会说**。
>
> **正确做法**：用**多种** block size / 采样率 / 声道数测。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| ASan 没报错但程序崩 | 只跑了不触发的参数 | 换多种参数测 |
| 调用栈没有行号 | 缺 `-g` | 加 `-g` |
| 调用栈全是内联 | 缺 `-fno-omit-frame-pointer`，或用了 `-O2` | 用 `-O1` |
| macOS 上没看到泄漏报告 | LSan 支持不完整 | 用 `leaks` 工具 |
| ASan 太慢 | 正常（2-3 倍） | 只在测试构建用 |
| 链接报错找不到 ASan 运行时 | 链接选项没加 | 加 `-fsanitize=address`（编译+链接都要） |
| 误报 | 用了自定义内存池 | 加 ASan 的 annotation，或忽略 |

---

## 八、怎么验证（实用流程）

```bash
#!/bin/bash
# 用多种参数跑 ASan 测试（关键：覆盖不同 block size）
set -e

echo "=== 编译（带 ASan + UBSan）==="
clang++ -std=c++17 -O1 -g \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -fno-sanitize-recover=all \
    test_dsp.cpp -o test_dsp_asan

echo "=== 多种 block size 测试 ==="
for bs in 1 16 64 256 512 1024 2048 4096; do
    echo "--- blockSize=$bs ---"
    if ! ./test_dsp_asan "$bs"; then
        echo "❌ blockSize=$bs 失败"
        exit 1
    fi
done

echo "=== 多种采样率测试 ==="
for sr in 44100 48000 88200 96000 192000; do
    echo "--- sampleRate=$sr ---"
    if ! ./test_dsp_asan 512 "$sr"; then
        echo "❌ sampleRate=$sr 失败"
        exit 1
    fi
done

echo ""
echo "🎉 全部通过（无内存错误）"
```

> [!tip] 这个循环就是价值所在
> **单独跑一次 ASan 价值有限。**
> 真正抓 bug 的是**参数组合的覆盖**——
> 音频 bug 恰恰是"特定 block size / 采样率下才出现"的。

**边界参数清单**（建议全部覆盖）：

| 参数 | 测试值 |
|---|---|
| block size | **1**、16、64、512、1024、4096 |
| 采样率 | 44100、48000、**88200**、96000、**192000** |
| 声道数 | **1**、2、更多 |
| 缓冲区 | **0 长度**、1、奇数长度 |

---

## 相关

- [[MOC - Realtime Engineering]]
- [[UndefinedBehaviorSanitizer]] — 补 ASan 抓不到的 UB
- [[ThreadSanitizer 与内存序]] — 数据竞争
- [[插件验证工具]] — auval / pluginval 的定位
- [[实时音频线程契约]] — 为什么不能分配
- [[音频回归测试]] — CI 里怎么跑
- [[CMake 基础]] — 怎么加 sanitizer 构建目标

> [!note] 待补充
> - `DYLD_INSERT_LIBRARIES` 给插件加 ASan 的实际可行性（需实测）
> - ASan 的 annotation API（自定义内存池）
> - 在 CI（GitHub Actions）里跑 ASan 的配置
> - 与 Valgrind 的对比
