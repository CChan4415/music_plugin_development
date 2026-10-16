---
title: CMake 插件项目结构
type: wiki
domain: frameworks
status: seed
confidence: medium
sources: []
tags: [recipe]
created: 2026-10-16
updated: 2026-10-16
---

# CMake 插件项目结构

> [!warning] ⚠️ 本页置信度：medium
> 本机**没有 cmake 也没有 JUCE**。目录结构是通用工程实践，
> **具体文件内容需你在真实项目里验证**。
> CMake 片段做过括号/命令名结构校验。

> [!important] 一句话
> **插件项目 = 一个仓库、一份 CMakeLists、一个 Source/ 目录。**
> 关键决策只有三个：JUCE 怎么来、产物装到哪、跨平台怎么处理。

## 一、推荐目录结构

```
my-plugin/
├── CMakeLists.txt              ← 唯一的构建入口
├── .gitignore                  ← ⚠️ 必须忽略 build/
├── README.md
├── LICENSE
├── Source/
│   ├── PluginProcessor.h/.cpp  ← DSP + 参数 + 状态
│   ├── PluginEditor.h/.cpp     ← UI
│   └── dsp/                    ← 你自己的 DSP 代码（与 JUCE 解耦）
│       ├── Biquad.h
│       └── ...
├── tests/                      ← 测试（见 [[DSP 单元测试怎么写]]）
├── .github/workflows/          ← CI（见 [[音频回归测试]]）
└── build/                      ← ⚠️ 生成物，不提交
```

> [!tip] 为什么把 DSP 单独放 `Source/dsp/`
> | 好处 | 说明 |
> |---|---|
> | **可独立测试** | 不依赖 JUCE 就能编译测试（见下） |
> | 换框架容易 | DSP 代码与 JUCE 解耦 |
> | 编译更快 | 改 UI 不重编 DSP |
>
> **这是本库最推荐的一条结构建议。**

---

## 二、`.gitignore`（必须有）

```gitignore
# 构建产物
build/
cmake-build-*/
*.o
*.a
*.dylib
*.so
*.dll

# 插件产物
*.vst3/
*.component/
*.app/

# IDE
.vscode/
.idea/
*.xcodeproj/
*.xcworkspace/

# macOS
.DS_Store

# JUCE（如果用 submodule 或 FetchContent）
JUCE/
```

> [!danger] 不忽略 `build/` 的后果
> - 仓库迅速膨胀（几百 MB）
> - 每次改配置都产生大量无意义 diff
> - 换机器时旧产物干扰新构建

> [!note] `*.vst3/` 末尾的斜杠
> macOS 上 `.vst3` 是**目录**，加斜杠才能正确忽略。
> 但 Windows 上它是**文件**——所以两种写法都加上更保险。
> 见 [[插件安装路径规范]]。

---

## 三、JUCE 怎么来（三种方式）

| 方式 | 优点 | 缺点 |
|---|---|---|
| **`add_subdirectory(JUCE)`** | ✅ 简单、离线可用 | 需手动下载 JUCE |
| **`FetchContent`** | ✅ 全自动、版本可锁 | 首次配置要联网 |
| `find_package(JUCE)` | 系统级安装 | 版本难管理 |

**`FetchContent` 示例**（⚠️ 具体写法需核实）：

```cmake
include(FetchContent)
FetchContent_Declare(JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG        8.0.0        # ⚠️ 锁版本，不要用 master
    GIT_SHALLOW    TRUE)
FetchContent_MakeAvailable(JUCE)
```

> [!danger] 必须锁版本（`GIT_TAG`）
> 用 `master` 的话：
> - 今天能编，明天 JUCE 改了 API 就编不过
> - CI 和本地可能拉到不同版本
> - 出问题无法复现
>
> **锁一个具体版本号。** 升级时显式改。

> [!tip] 开发时的取舍
> - **CI**：用 `FetchContent`（干净、可复现）
> - **本地开发**：用 `add_subdirectory` + 本地 clone（配置快、可离线、能读源码）

---

## 四、让 DSP 可独立测试

> [!important] 这是"结构"能带来的最大实际收益

```cmake
# 主插件（需要 JUCE）
juce_add_plugin(MyPlugin ...)
target_sources(MyPlugin PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp
    Source/dsp/Biquad.cpp)

# ⭐ 独立的 DSP 测试（不需要 JUCE）
add_executable(dsp_tests
    tests/test_dsp.cpp
    Source/dsp/Biquad.cpp)          # 只编译 DSP 部分
target_include_directories(dsp_tests PRIVATE Source/dsp)

enable_testing()
add_test(NAME dsp COMMAND dsp_tests)
```

> [!tip] 为什么这很重要
> | | 依赖 JUCE 的测试 | 独立 DSP 测试 |
> |---|---|---|
> | 编译时间 | 慢（JUCE 很大） | **快** |
> | 能跑 sanitizer | 🟠 麻烦 | ✅ **容易** |
> | CI 配置 | 复杂 | **简单** |
>
> 见 [[DSP 单元测试怎么写]]、[[AddressSanitizer]]。

**本机就能验证这一点**（无 JUCE / 无 cmake）：
```bash
# 用 clang++ 直接编译 DSP 部分 + 测试
clang++ -std=c++17 -O1 -g -fsanitize=address,undefined \
    tests/test_dsp.cpp Source/dsp/Biquad.cpp -o dsp_tests
./dsp_tests
```
> 本库的 `50-Playground/ref-build/` 就是这个模式的最小示例（Makefile 已实测）。

---

## 五、跨平台注意

| 项 | macOS | Windows |
|---|---|---|
| 产物形态 | `.vst3` 是**目录** | `.vst3` 是**文件**（DLL） |
| 安装位置 | `/Library/Audio/Plug-Ins/VST3/` | `C:\Program Files\Common Files\VST3\` |
| 运行时库 | — | 需设 `CMAKE_MSVC_RUNTIME_LIBRARY` |
| 大小写 | 不敏感 | **敏感** ⚠️ |

```cmake
if(APPLE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "")
elseif(WIN32)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()
```

> [!danger] 大小写敏感是"本地永远发现不了"的坑
> macOS 文件系统不区分大小写 → `#include "biquad.h"` 能找到 `Biquad.h`
> Windows 区分 → **编译失败**，而你本地测不出来。
>
> **本库有工具**：
> ```bash
> bash 50-Playground/tools/check_crossplatform.sh Source/
> ```
> 见 [[跨平台开发 macOS 与 Windows]]。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **不写 `.gitignore`** | `build/` 进仓库 | 检查 |
| 2 | **`GIT_TAG master`** | 版本漂移、不可复现 | 锁具体版本 |
| 3 | **DSP 与 JUCE 混在一起** | 无法独立测试 | 分开目录 |
| 4 | **硬编码绝对路径** | 换机器就坏 | 用 CMake 变量 |
| 5 | **不设 `CMAKE_CXX_EXTENSIONS OFF`** | Windows 编不过 | 检查 |
| 6 | **忘了 Windows 运行时库** | 运行时冲突 | 按平台设 |
| 7 | **测试也要链 JUCE** | 编译慢、CI 复杂 | 拆出 DSP |
| 8 | **把所有代码放一个 .cpp** | 编译慢、难维护 | 分文件 |
| 9 | **不给 `Standalone` 格式** | 调试不便 | 加上 |
| 10 | **`.vst3` 只写一种忽略规则** | 另一平台漏掉 | 两种都写 |

> [!danger] 第 3 条是最有价值的结构建议
> AI 会把所有代码写进 `PluginProcessor.cpp`——
> 看起来简单，但**你的 DSP 从此无法独立测试**。
>
> **判据**：`tests/` 里的测试能否**不链接 JUCE** 就编译通过？

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 仓库几百 MB | `build/` 提交了 | 加 `.gitignore` |
| CI 和本地行为不同 | JUCE 版本不一致 | 锁 `GIT_TAG` |
| Windows 编不过 | 大小写 / 运行时库 | 用检查脚本 |
| 测试很慢 | 链了 JUCE | 拆出 DSP |
| 换机器配置失败 | 硬编码路径 | 用变量 |
| 配置很慢 | 每次重新下载 JUCE | 本地 `add_subdirectory` |

---

## 八、怎么验证

**本机可做**：

```bash
# ① 检查 .gitignore 是否覆盖关键项
grep -E "^build/|^\*\.vst3|^\*\.component" .gitignore || echo "⚠️ 缺关键忽略项"

# ② 跨平台检查（大小写、类型宽度、平台 API）
bash 50-Playground/tools/check_crossplatform.sh Source/

# ③ DSP 独立测试（无需 JUCE）
clang++ -std=c++17 -O1 -g -fsanitize=address,undefined \
    tests/test_dsp.cpp Source/dsp/*.cpp -o /tmp/dsp_tests && /tmp/dsp_tests
```

**装好 cmake + JUCE 后**：

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
ctest --test-dir build --output-on-failure
```

> [!important] 最关键的一条自检
> **`tests/` 能不能不链接 JUCE 就编译通过？**
> 能 → 结构是对的（DSP 解耦了）。
> 不能 → DSP 和框架耦合了，后面会越来越难测。

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[CMake 基础]] — CMake 通用知识
- [[JUCE 的 CMake API]] — `juce_add_plugin` 参数
- [[JUCE 的架构与模块划分]] — 模块依赖
- [[跨平台开发 macOS 与 Windows]] — 大小写等陷阱
- [[DSP 单元测试怎么写]] — 独立测试的价值
- [[音频回归测试]] — CI 配置
- [[插件安装路径规范]] — 产物装到哪
- [[版本号与更新分发]]

> [!note] 待补充（优先级高）
> - **装 JUCE 后实测本页所有 CMake 片段**
> - `FetchContent` 的**当前**推荐写法
> - 多格式（VST3+AU+Standalone）的目标组织
> - 预编译头 / 编译加速
> - 安装规则（`install()`）与打包的衔接
