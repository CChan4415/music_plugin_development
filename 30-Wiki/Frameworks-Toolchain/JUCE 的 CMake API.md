---
title: JUCE 的 CMake API
type: wiki
domain: frameworks
status: solid
confidence: high
sources: ["[[10-Sources/juce/JUCE 8.0.4 CMake API]]", "[[10-Sources/juce/JUCE 8.0.4 官方插件示例 CMakeLists.txt]]"]
tags: [recipe, gotcha]
created: 2026-10-16
updated: 2026-10-16
---

# JUCE 的 CMake API

> [!important] 一句话
> **`juce_add_plugin()` 接收 84 个可选参数**——
> 但真正必须掌握的就那么十来个，其余都有合理默认值。

> [!note] ✅ 本页已用真实 JUCE 8.0.4 官方文档核对（2026-10-16）
> - **权威来源**：JUCE 8.0.4 的 `docs/CMake API.md`（867 行，官方文档）
> - **官方示例**：`examples/CMake/AudioPlugin/CMakeLists.txt`
> - **实测**：cmake 4.4.4 + ninja 1.13.2 在本机跑通了完整的
>   配置 → 构建 → ctest 流程
>
> ⚠️ **仍未实测的**：本机**没有 JUCE 的 `modules/` 源码**
> （下载被网络截断），所以 `juce_add_plugin` 本身**没有真正执行过**。
> 下面标注了哪些是文档确认、哪些是实测。

---

## 一、官方最小示例（逐字来自 JUCE 8.0.4）

```cmake
cmake_minimum_required(VERSION 3.22)
project(AUDIO_PLUGIN_EXAMPLE VERSION 0.0.1)

add_subdirectory(JUCE)                    # 或 find_package(JUCE CONFIG REQUIRED)

juce_add_plugin(AudioPluginExample
    PLUGIN_MANUFACTURER_CODE Juce          # 四字符，至少一个大写
    PLUGIN_CODE              Dem0          # 四字符，恰好一个大写
    FORMATS                  AU VST3 Standalone
    PRODUCT_NAME             "Audio Plugin Example")

target_sources(AudioPluginExample
    PRIVATE
        PluginEditor.cpp
        PluginProcessor.cpp)

target_compile_definitions(AudioPluginExample
    PUBLIC
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_VST3_CAN_REPLACE_VST2=0)

target_link_libraries(AudioPluginExample
    PRIVATE
        juce::juce_audio_utils
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)
```

> [!important] 这就是官方的骨架
> 我之前的版本**基本正确**，但漏了三个东西：
> 1. **`juce::juce_recommended_warning_flags`**（官方示例里有）
> 2. `PLUGIN_CODE` 的**大小写规则**（见下）
> 3. `NEEDS_WEB_BROWSER` / `NEEDS_CURL` 与 `target_compile_definitions` 的**联动**

---

## 二、⚠️ 两个四字符代码的规则（官方文档确认）

> [!danger] `PLUGIN_CODE` 有严格的大小写要求
> 官方注释原文：
> ```
> PLUGIN_MANUFACTURER_CODE Juce   # A four-character manufacturer id
>                                 # with at least one upper-case character
> PLUGIN_CODE Dem0                # A unique four-character plugin id
>                                 # with exactly one upper-case character
>                                 # GarageBand 10.3 requires the first letter
>                                 # to be upper-case, and the remaining letters
>                                 # to be lower-case
> ```

| 参数 | 规则 |
|---|---|
| **`PLUGIN_MANUFACTURER_CODE`** | 四字符，**至少一个大写** |
| **`PLUGIN_CODE`** | 四字符，**恰好一个大写** |
| `PLUGIN_CODE` 额外 | **GarageBand 要求：首字母大写，其余小写** |

> [!danger] `Dem0` 是官方示例的写法
> - `D` 大写（首位，满足 GarageBand）
> - `em0` 小写
> - 恰好一个大写字母 ✅
>
> **如果 AI 给你 `DEMO`（四个都大写）→ 违反"恰好一个大写"规则。**
> 如果给你 `demo`（没有大写）→ 也违反。

> [!warning] ⚠️ 这两个代码一旦发布就不能改
> 改了 → 宿主找不到旧工程里的插件。
> 见 [[版本号与更新分发]]。

---

## 三、`FORMATS` 的完整取值（官方文档）

```
AU  VST3  VST  AAX  Unity  AUv3  Standalone
```

| 值 | 说明 |
|---|---|
| `AU` | macOS 原生（⚠️ 只在 macOS 生效） |
| `AUv3` | App Extension（iOS/macOS） |
| `VST3` | 跨平台标准 |
| `VST` | ⚠️ VST2，需单独指定 SDK 路径 |
| `AAX` | ⚠️ Pro Tools，需 Avid 审批 |
| `Unity` | Unity 原生插件 |
| **`Standalone`** | ✅ **开发调试的最佳伙伴** |

> [!danger] 我之前的页面**漏了 `Unity`**
> 完整列表是 `AAX Unity VST AU AUv3`（官方文档原话）。
> 加上 `VST3` 和 `Standalone` 共 7 种。

> [!tip] `Standalone` 为什么重要
> 它生成一个**能直接运行的程序**——不用开 DAW 就能在
> lldb 里调试（见 [[lldb 基础]]）、遍历 block size（见 [[音频缓冲区与 block size]]）。

---

## 四、最常用的参数（从 84 个里挑）

> [!note] 完整清单见 `10-Sources/juce/JUCE 8.0.4 CMake API.md`
> 这里只列插件开发最常用的。

### 标识与命名

| 参数 | 作用 |
|---|---|
| `PRODUCT_NAME` | 输出名（默认 = target 名） |
| `PLUGIN_NAME` | 插件显示名（可与 PRODUCT_NAME 不同） |
| `VERSION` | 版本号（Apple 上是 `CFBundleShortVersionString`） |
| **`BUNDLE_ID`** | ⭐ macOS bundle id（**我之前漏了**） |
| `DESCRIPTION` | 描述 |
| `COMPANY_NAME` / `COMPANY_WEBSITE` / `COMPANY_EMAIL` / `COMPANY_COPYRIGHT` | 厂商信息 |

### 行为

| 参数 | 作用 |
|---|---|
| `IS_SYNTH` | 乐器还是效果器 |
| `NEEDS_MIDI_INPUT` / `NEEDS_MIDI_OUTPUT` | MIDI 需求 |
| `IS_MIDI_EFFECT` | MIDI 效果器 |
| `EDITOR_WANTS_KEYBOARD_FOCUS` | UI 要键盘焦点 |
| `COPY_PLUGIN_AFTER_BUILD` | 构建后自动装到插件目录 |

### 分类（宿主里显示在哪）

| 参数 | 作用 |
|---|---|
| `VST3_CATEGORIES` | VST3 分类 |
| `AU_MAIN_TYPE` | AU 主类型 |
| `VST2_CATEGORY` | VST2 分类 |

### 安全 / 公证

| 参数 | 作用 |
|---|---|
| **`HARDENED_RUNTIME_ENABLED`** | ⭐ macOS 强化运行时（**公证必需**，我之前漏了） |
| `APP_SANDBOX_ENABLED` | 沙箱（App Store 需要） |
| `MICROPHONE_PERMISSION_ENABLED` | 麦克风权限 |

> [!important] `HARDENED_RUNTIME_ENABLED` 与公证的关系
> macOS 公证要求二进制启用**强化运行时**。
> 见 [[macOS 代码签名]]、[[macOS 公证 (notarization)]]。
>
> ⚠️ 具体是否需要显式设置、默认值是什么，**需在真实 JUCE 项目里验证**。

### 依赖开关

| 参数 | 与 compile definition 的联动 |
|---|---|
| `NEEDS_CURL` | 若为 TRUE，则**不要**设 `JUCE_USE_CURL=0` |
| `NEEDS_WEB_BROWSER` | 若为 TRUE，则**不要**设 `JUCE_WEB_BROWSER=0` |
| `NEEDS_WEBVIEW2` | Windows WebView2 |

> [!danger] 官方示例里的注释说明了一个真实陷阱
> ```cmake
> JUCE_WEB_BROWSER=0  # If you remove this, add `NEEDS_WEB_BROWSER TRUE`
> JUCE_USE_CURL=0     # If you remove this, add `NEEDS_CURL TRUE`
> ```
>
> **关掉功能时要设 compile definition；打开时要设 `NEEDS_*`。**
> 两边不一致会导致链接错误或功能缺失。

---

## 五、代码语法验证（本库的做法）

> [!important] 没有 JUCE 也能检查代码语法
> 本库提供了一个 **JUCE stub 头文件**（604 行，45 个类），
> 用来对 Wiki 里的 C++ 片段做 `-fsyntax-only` 检查。

**位置**：`50-Playground/tools/juce_stub/juce_stub.h`

```bash
clang++ -std=c++17 -fsyntax-only \
    -I 50-Playground/tools/juce_stub \
    your_snippet.cpp
```

**覆盖的类**（45 个）：
```
AudioProcessor, AudioProcessorEditor, AudioBuffer, MidiBuffer,
AudioProcessorValueTreeState, AudioParameterFloat/Bool/Choice,
RangedAudioParameter, ParameterAttachment, Oversampling,
DryWetMixer, AbstractFifo, SIMDRegister, ScopedNoDenormals,
Component, Slider, Label, Button, ComboBox, Timer, Graphics,
Rect, AudioChannelSet, SmoothedValue, BusesProperties, ...
```

> [!warning] ⚠️ stub 的局限
> - 只检查**语法和签名**，不检查行为
> - 签名是按"常见版本"写的，可能与你的 JUCE 版本有差异
> - **不能用来编译真正的插件**
>
> 用途：抓拼写错误、参数类型错误、漏掉的 `override`。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **`PLUGIN_CODE` 四个大写** | 违反"恰好一个大写" | 检查大小写 |
| 2 | **四字符给 3 或 5 个字符** | AU 验证失败 | 数一遍 |
| 3 | **`FORMATS` 写错值** | 配置报错 | 用官方 7 个值 |
| 4 | **忘了 `CMAKE_CXX_EXTENSIONS OFF`** | Windows 编不过 | 检查 |
| 5 | **关掉 WEB_BROWSER 但没设 compile definition** | 链接错误 | 见第四节 |
| 6 | **参数名过时** | 配置报错 | 对照你的 JUCE 版本 |
| 7 | **不给 `Standalone`** | 调试麻烦 | 加上 |
| 8 | **忘了 `HARDENED_RUNTIME_ENABLED`** | 公证失败 | 见 [[macOS 公证 (notarization)]] |
| 9 | **`target_link_libraries` 缺 `juce_recommended_*`** | 警告/优化配置缺失 | 加三行 |
| 10 | **硬编码路径** | 换机器就坏 | 用 `${CMAKE_CURRENT_SOURCE_DIR}` |

> [!danger] 第 1 条是最隐蔽的
> `PLUGIN_CODE DEMO`（四个大写）在**配置阶段可能不报错**，
> 但 AU 验证会失败（见 [[auval 与 AU 验证]]），且错误信息难懂。
>
> **正确写法参考官方示例：`Dem0`**——恰好一个大写，首字母大写。

> [!danger] 第 9 条我之前的页面漏了
> 官方示例的 `target_link_libraries` 里有**三行** `juce_recommended_*`：
> `config_flags`、`lto_flags`、**`warning_flags`**。
> 漏掉它们不会报错，但你会失去 JUCE 推荐的编译配置。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 配置报"未知参数" | JUCE 版本不匹配 | 查锁定版本的文档 |
| AU 验证失败 | `PLUGIN_CODE` 大小写不对 | 用 `Dem0` 式写法 |
| Windows 编不过 | 用了 gnu++ 扩展 | `CMAKE_CXX_EXTENSIONS OFF` |
| 链接错误 | 缺模块 | 加 `juce::juce_dsp` 等 |
| 公证失败 | 没启用强化运行时 | `HARDENED_RUNTIME_ENABLED` |
| 宿主找不到插件 | `COPY_PLUGIN_AFTER_BUILD` 装到用户级 | 见 [[插件安装路径规范]] |
| 改了配置没生效 | 没重新配置 | 删 `build/` 重跑 |

---

## 八、怎么验证

### ✅ 本机已实测（cmake 4.4.4 + ninja 1.13.2）

```bash
# ① CMake 能正确解析标准设置
cmake -B build -G Ninja
# 实测输出：CXX standard: 17 / Extensions: OFF ✅

# ② 完整的配置 → 构建 → 测试流程（用真实 DSP 项目验证过）
cmake -B build -G Ninja
cmake --build build
cd build && ctest --output-on-failure
```

**实测记录**（本库，2026-10-16）：

| 检查 | 结果 |
|---|---|
| `cmake -B build -G Ninja` 配置 | ✅ 0.2 s |
| `cmake --build build` | ✅ 编译 + 链接成功 |
| `ctest` | ✅ 1/1 Passed |
| `CMAKE_CXX_EXTENSIONS OFF` | ✅ `__STRICT_ANSI__` 已定义（确认用 `-std=c++17`） |
| **`ctest` 失败时的退出码** | **8**（通过时 0） |

> [!danger] ⭐ 实测发现的一个 CI 陷阱
> ```bash
> ctest 2>&1 | tail -5      # ⚠️ 退出码永远是 0！
> ```
> **管道会把 `ctest` 的失败码掩盖掉**（`$?` 变成 `tail` 的）。
>
> **实测**：失败时 `ctest` 返回 **8**，但 `ctest | tail` 返回 **0**。
> **CI 里这会让你以为测试通过了。**
>
> **正确写法**：
> ```bash
> set -o pipefail      # 让管道传播失败
> ctest 2>&1 | tail -5
> # 或者不用管道：
> ctest --output-on-failure
> ```

### ⚠️ 需要 JUCE 才能验证的

```bash
# 装好 JUCE 后
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
# 然后运行 Standalone 目标
```

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[CMake 基础]] — CMake 通用知识
- [[CMake 插件项目结构]] — 目录怎么组织
- [[JUCE 的架构与模块划分]] — 模块依赖
- [[版本号与更新分发]] — 四字符代码为什么不能改
- [[跨平台开发 macOS 与 Windows]]
- [[auval 与 AU 验证]] — AU 验证
- [[macOS 公证 (notarization)]] — 强化运行时
- [[插件安装路径规范]]
- [[10-Sources/juce/JUCE 8.0.4 CMake API]] — ⭐ 官方权威文档

> [!note] 待补充
> - **拿到完整 JUCE 源码后实测 `juce_add_plugin`**（本机下载被截断，缺 modules/）
> - `HARDENED_RUNTIME_ENABLED` 的默认值与公证的实际关系
> - `find_package(JUCE CONFIG REQUIRED)` 的安装流程
> - 84 个参数里剩下的（iOS 权限、沙箱等）——本库用不到
