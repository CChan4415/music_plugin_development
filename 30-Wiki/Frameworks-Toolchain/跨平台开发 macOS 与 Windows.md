---
title: 跨平台开发 macOS 与 Windows
type: wiki
domain: frameworks
status: seed
confidence: medium
sources: []
tags: [gotcha, cpp, todo]
created: 2026-10-14
updated: 2026-10-14
---

# 跨平台开发 macOS 与 Windows

> [!important] 你的决定
> 你的原话：**"可以从 mac 版本入手，但是以后肯定需要兼容 windows，也可以从第一天直接开始考虑兼容性。"**
>
> 这个判断是对的。**跨平台的成本几乎全在"第一天写的代码"上**——
> 后期再补的代价是重写，前期注意的代价几乎是零。
> 这一页就是"前期要注意什么"的清单。

## 核心原则

> [!tip] 一句话
> **用 JUCE 的抽象层，不要用平台原生 API；把"平台差异"集中在极少数几个地方。**

跨平台不是"写两遍"，而是"写一遍，但避开那些只在某个平台上成立的东西"。

---

## 一、最容易踩的坑：文件名大小写

**这是 Mac 优先开发的头号杀手**，因为它在你的机器上**永远不会报错**。

macOS 默认文件系统**大小写不敏感**，Windows 的 NTFS 也是，
但**编译器查找头文件时是大小写敏感的**（MSVC 和 Linux 都是）。

**实测演示**：

```
实际文件名: MyFilter.h
代码里写的: #include "myfilter.h"

macOS 上:  ✅ 编译成功 —— bug 被掩盖了
Windows:   ❌ 编译失败
Linux:     ❌ 编译失败
CI 上:     ❌ 编译失败（而你本地永远复现不了）
```

**规则**：

- ✅ `#include` 的路径**逐字符匹配**实际文件名
- ✅ 源文件名统一风格（推荐 `PascalCase.h` / `PascalCase.cpp`，和 JUCE 一致）
- ✅ 一个文件叫 `MyFilter.h`，就永远不要写 `myfilter.h` 或 `my_filter.h`

> [!warning] 还有个更隐蔽的版本
> **同一目录下有两个只差大小写的文件**（`Filter.h` 和 `filter.h`）。
> 在 macOS 上你可能只能看到一个，在 Linux 上它们是两个不同的文件。
> **永远不要这样做。** 这会让 git 仓库在不同平台上表现不一致。

---

## 二、类型宽度：`long` 在 Windows 上是 4 字节

| 类型 | macOS / Linux (LP64) | Windows (LLP64) |
|---|---|---|
| `int` | 4 | 4 |
| **`long`** | **8** | **4** ⚠️ |
| `long long` | 8 | 8 |
| `size_t` | 8 (64位) | 8 (64位) |
| 指针 | 8 | 8 |

**本机实测（macOS arm64）**：

```
sizeof(long)  = 8
sizeof(void*) = 8
sizeof(int)   = 4
```

**规则**：

- ❌ 不要用 `long` 存采样位置、缓冲区大小
- ✅ 用 `<cstdint>` 的**定宽类型**：`int32_t` / `int64_t` / `uint32_t`
- ✅ 计数用 `size_t` 或 `int`
- ✅ 音频样本用 `float` / `double`（这两个跨平台一致）

```cpp
// ❌ 在 Windows 上会截断
long samplePosition = 0;

// ✅ 明确宽度
int64_t samplePosition = 0;
```

> [!note] 为什么音频里特别要注意
> 一个 48kHz 的音频流，一小时就是 **172,800,000 个采样**——
> 超过了 32 位有符号整数的安全范围（约 21 亿）。
> 长时间录制/播放的位置计数必须用 64 位。

---

## 三、数学常量：`M_PI` 不是标准

```cpp
// ❌ macOS/Linux 能用，MSVC 默认不行
double x = M_PI;

// ✅ 两种做法
// 方案 1：MSVC 开关（在 CMake 里加）
//   target_compile_definitions(MyPlugin PRIVATE _USE_MATH_DEFINES)

// 方案 2（推荐）：自己定义，跨平台零依赖
constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = 2.0 * kPi;
```

**本机实测**：macOS 上 `M_PI` 默认可用（来自 `<math.h>`）。
**MSVC 需要 `#define _USE_MATH_DEFINES` 且必须在 `#include <cmath>` 之前。**

> [!tip] JUCE 已经处理了
> `juce::MathConstants<double>::twoPi` 等常量是跨平台的。
> 用了 JUCE 就用它的；写独立 DSP 代码时自己定义。

---

## 四、`#pragma once` vs 头文件卫士

| 方式 | MSVC | Clang | GCC | 说明 |
|---|---|---|---|---|
| `#pragma once` | ✅ | ✅ | ✅ | 更简洁，现代编译器都支持 |
| `#ifndef` 卫士 | ✅ | ✅ | ✅ | 标准，绝对可靠 |

**两个都可以用**，`#pragma once` 在实践中没问题。
但如果你要极致保守，用头文件卫士。**不要两个都不用**（会导致重复定义错误）。

---

## 五、构建系统：CMake 是唯一的现实选择

> [!important] 为什么必须用 CMake
> 因为你要在两个平台上构建。手写 `clang++ a.cpp b.cpp` 在 macOS 能用，
> 到 Windows 上要换成 MSVC 的命令行参数——**完全不同**。
> CMake 生成各平台原生的构建文件（Xcode / Visual Studio / Ninja）。

**JUCE 项目的最小 CMake 结构**：

```cmake
cmake_minimum_required(VERSION 3.22)
project(MyPlugin VERSION 1.0.0)

# 用 FetchContent 拉 JUCE，别手动下载（版本可控、跨平台一致）
include(FetchContent)
FetchContent_Declare(JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG        8.0.0)          # ⚠️ 锁定 tag，不要用 master
FetchContent_MakeAvailable(JUCE)

juce_add_plugin(MyPlugin
    FORMATS     VST3 AU              # AU 只在 macOS 构建，CMake 会自动跳过
    IS_SYNTH    FALSE
    NEEDS_MIDI_INPUT  FALSE
    COPY_PLUGIN_AFTER_BUILD TRUE)

target_sources(MyPlugin PRIVATE Source/PluginProcessor.cpp Source/PluginEditor.cpp)
target_compile_definitions(MyPlugin PRIVATE
    JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)   # 去掉不需要的依赖
target_link_libraries(MyPlugin PRIVATE
    juce::juce_audio_utils juce::juce_dsp
    PUBLIC juce::juce_recommended_config_flags
           juce::juce_recommended_lto_flags
           juce::juce_recommended_warning_flags)
```

> [!warning] `FORMATS VST3 AU` 里的 AU 在 Windows 上会被忽略
> 这是好事——一份 CMakeLists 两个平台都能用。
> **AAX 需要额外 SDK，两个平台都麻烦，先跳过。**

---

## 六、CI：让 Windows 帮你发现问题

**这是解决"Mac 上好好的"最有效的办法**：每次 push 都让 GitHub Actions 在两个平台上编译。

```yaml
# .github/workflows/build.yml
name: Build
on: [push, pull_request]
jobs:
  build:
    strategy:
      matrix:
        os: [macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Configure
        run: cmake -B build -DCMAKE_BUILD_TYPE=Release
      - name: Build
        run: cmake --build build --config Release
```

> [!warning] 现实约束（需要你自己核实）
> - macOS runner **对公开仓库免费**，私有仓库按分钟计费
> - macOS runner 比 Linux 贵（约 10 倍），Windows 约 2 倍
> - 具体价格和免费额度**会变**，去 GitHub 官方定价页确认
> - **建议**：仓库设为公开（如果你的代码不介意），CI 成本就是零

> [!tip] CI 的真正价值
> 不是"自动构建"，而是**让你在写代码的当天就知道它是否跨平台**。
> 没有 CI 的话，你会在几个月后第一次尝试 Windows 构建时，
> 面对 200 个错误，且不知道哪些是根本问题。

---

## 七、运行时差异（比编译期更隐蔽）

| 差异 | macOS | Windows | 影响 |
|---|---|---|---|
| **文件路径分隔符** | `/` | `\`（也接受 `/`） | 用 `juce::File` 或 `std::filesystem::path`，别手拼字符串 |
| **文本文件换行** | `\n` | `\r\n` | 读写配置文件时注意；`std::ios::binary` 可避免转换 |
| **默认字符编码** | UTF-8 | 历史上是本地代码页 | 路径含中文时用 `juce::String` / 宽字符 API |
| **动态库扩展名** | `.dylib` / `.vst3` | `.dll` / `.vst3` | CMake/JUCE 会处理 |
| **插件安装路径** | `/Library/Audio/Plug-Ins/` | `C:\Program Files\Common Files\VST3\` | 见 [[插件安装路径规范]] |
| **大小写敏感性** | 不敏感 | 不敏感（但编译器敏感） | 见第一节 |
| **`char` 是否有符号** | 有符号 | 有符号（MSVC 默认） | 用 `int8_t`/`uint8_t` 明确 |
| **线程优先级 API** | Mach / pthread | Windows 线程 API | **用 JUCE 的抽象，别自己调** |

> [!danger] 绝对不要做的事
> - ❌ 手拼路径字符串 `dir + "/" + name`
> - ❌ 用 `#ifdef _WIN32` 散落在业务代码里
> - ❌ 自己调平台线程/文件 API
>
> **平台差异应该集中在极少数几个文件里**（如 `PlatformUtils.h/.cpp`），
> 而不是散落在整个代码库。JUCE 已经帮你封装了 90%。

---

## 八、开发环境的现实建议

| 事项 | 建议 |
|---|---|
| **主开发平台** | macOS（你在用，且 JUCE 在 Mac 上调试体验更好） |
| **怎么测 Windows** | **不要买 Windows 机器**。用 GitHub Actions 编译 + 找朋友帮测 |
| **虚拟机** | 可行但有坑：USB 音频设备透传、ASIO 驱动、性能都不理想 |
| **AU 格式** | 只在 macOS 有，Windows 用户不需要 |
| **VST3** | 两个平台都要，是主力格式 |
| **测试宿主** | macOS: Ableton / REAPER。Windows: REAPER（免费评估） |

> [!tip] 最小可行策略
> 1. **第一天就用 CMake**（不要用 Projucer 生成 Xcode 工程）
> 2. **第一天就配 GitHub Actions**，双平台编译
> 3. **代码里不出现平台相关 API**（除极少数封装点）
> 4. 发布前**找一个 Windows 用户帮你实测**
>
> 这四件事做完，跨平台就是"免费"的。

---

## 九、怎么验证你的代码是跨平台的

| 检查 | 怎么做 |
|---|---|
| 大小写 | CI 在 Linux 上编译（ext4 大小写敏感，最严格） |
| 类型宽度 | 编译时加 `-Wshorten-64-to-32`（Clang）/ `/W4`（MSVC） |
| 平台 API | 全库 grep：`_WIN32`、`__APPLE__`、`windows.h`、`pthread.h` |
| 路径拼接 | grep `"/"` 和 `"\\"` 出现在字符串里的地方 |
| 实际运行 | 必须有 Windows 用户实测（编译通过 ≠ 运行正确） |

**已经给你写好了自检脚本**：

```bash
bash 50-Playground/tools/check_crossplatform.sh Source/
```

它检查 6 类问题：

| # | 检查 | 为什么本地发现不了 |
|---|---|---|
| 1 | 只差大小写的重名文件 | macOS 磁盘上**根本创建不出来**，但 git 能跟踪 → 必须查 git index |
| 2 | `#include` 大小写不符 | macOS 文件系统不敏感，`[ -f ]` 测试永远返回真 |
| 3 | 使用 `long` | macOS 上是 8 字节，编译不报错 |
| 4 | 平台 API 散落 | 在 macOS 上能编译 |
| 5 | 手拼路径 | 在 macOS 上能跑 |
| 6 | `M_PI` | macOS 默认可用 |

> [!warning] 第 1 和第 2 项的坑最深
> 写这个脚本时我自己踩了两次：先用 `find` 扫磁盘（**macOS 上永远扫不到冲突**），
> 又用 `[ -f "myfilter.h" ]` 判断（**macOS 上永远返回真**）。
> 两次都是"用不敏感的文件系统去检测大小写问题"。
> **正确做法是查 git index 和比较字符串。**
>
> 这又是一次「测量工具错，而非被测对象错」——
> 见 [[2026-10-14 测量工具会骗你 —— 六次踩坑记录]]。

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[C++ 零基础到音频 DSP 路线]]
- [[插件格式对比]] — AU 只在 macOS，VST3 跨平台
- [[插件安装路径规范]]
- [[CMake 基础]]
- [[代码签名与公证]] — macOS 公证 / Windows 代码签名是两套流程
- [[macOS 公证 (notarization)]]
- [[Windows 代码签名]]

> [!note] 待补充
> - Windows 上 VST3 的安装路径与注册机制细节（需实测）
> - MSVC 特有的警告与 `/W4` 下的常见报错
> - ASIO vs WASAPI 对插件开发的影响
> - 两个平台的 SIMD intrinsics 差异（SSE/AVX vs NEON）——**用 JUCE 的 `juce::dsp::SIMDRegister` 可规避**
> - Windows 上插件的签名与 SmartScreen 提示
