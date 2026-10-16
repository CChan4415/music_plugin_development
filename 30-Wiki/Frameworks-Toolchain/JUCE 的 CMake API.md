---
title: JUCE 的 CMake API
type: wiki
domain: frameworks
status: seed
confidence: medium
sources: []
tags: [recipe, gotcha]
created: 2026-10-16
updated: 2026-10-16
---

# JUCE 的 CMake API

> [!warning] ⚠️ 本页置信度：medium（部分未实测）
> **本机没有安装 JUCE**，也没有 `cmake`。所以：
> - `juce_add_plugin` 的**参数名**：来自 JUCE 文档与社区实践，**需对照你的 JUCE 版本核实**
> - 代码**语法**：用本库的 JUCE stub 头文件做过 `-fsyntax-only` 检查（见下方说明）
> - ⚠️ **实际构建流程未在本机跑过**

> [!important] 一句话
> **`juce_add_plugin()` 是你唯一必须掌握的命令**——
> 它接收一堆"四字符代码 + 元数据"，生成所有格式的插件目标。

## 一、最小可用配置

```cmake
cmake_minimum_required(VERSION 3.22)
project(MyPlugin VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)              # ⚠️ 不要用 gnu++ 扩展

add_subdirectory(JUCE)                     # 或 FetchContent

juce_add_plugin(MyPlugin
    COMPANY_NAME              "Your Name"
    PLUGIN_MANUFACTURER_CODE  Yrnm         # ⚠️ 四字符
    PLUGIN_CODE               Mypl         # ⚠️ 四字符
    FORMATS                   VST3 AU Standalone
    PRODUCT_NAME              "My Plugin"
    COPY_PLUGIN_AFTER_BUILD   TRUE
    IS_SYNTH                  FALSE
    NEEDS_MIDI_INPUT          FALSE
    NEEDS_MIDI_OUTPUT         FALSE
    IS_MIDI_EFFECT            FALSE)

target_sources(MyPlugin PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp)

target_compile_definitions(MyPlugin PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)

target_link_libraries(MyPlugin PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
    PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags)
```

> [!danger] 三个最容易写错的点
> | 点 | 错误后果 |
> |---|---|
> | **`PLUGIN_MANUFACTURER_CODE` / `PLUGIN_CODE` 必须四字符** | 不是四字符 → AU 验证失败、宿主识别异常 |
> | **`CMAKE_CXX_EXTENSIONS OFF`** | 不加 → 用 gnu++ 扩展 → Windows 编不过 |
> | **`FORMATS AU` 在 Windows** | 会被**忽略**（不是错误） |

> [!warning] ⚠️ `PLUGIN_CODE` 一旦发布就不能改
> 它是宿主识别插件的身份之一。改了 → 用户的旧工程找不到插件。
> 见 [[版本号与更新分发]]。

---

## 二、`FORMATS` 选项

| 值 | 说明 |
|---|---|
| `VST3` | 跨平台标准 |
| `AU` | macOS 原生（⚠️ 只在 macOS 生效） |
| `AUv3` | iOS/macOS App Extension |
| `Standalone` | 独立程序（**开发时最有用的调试方式**） |
| `VST` | VST2（⚠️ 已停止授权，见 [[开源与商业的许可证陷阱]]） |
| `AAX` | Pro Tools（⚠️ 需 Avid 审批） |

> [!tip] `Standalone` 是你最好的调试伙伴
> 它生成一个**能直接运行的程序**——不用开 DAW 就能测。
> 开发阶段强烈建议加上。

---

## 三、代码语法验证（本库的做法）

> [!important] 没有 JUCE 也能检查代码语法
> 本库提供了一个 **JUCE stub 头文件**（只声明签名，不含实现），
> 用来对 Wiki 里的代码片段做 `-fsyntax-only` 检查。

**位置**：`50-Playground/tools/juce_stub/juce_stub.h`

**用法**：
```bash
clang++ -std=c++17 -fsyntax-only \
    -I 50-Playground/tools/juce_stub \
    your_snippet.cpp
```

**覆盖的类**（30+）：
```
AudioProcessor, AudioProcessorEditor, AudioBuffer, MidiBuffer,
AudioProcessorValueTreeState, AudioParameterFloat/Bool/Choice,
RangedAudioParameter, ParameterAttachment, Oversampling,
DryWetMixer, AbstractFifo, SIMDRegister, ScopedNoDenormals,
BusesProperties, BusesLayout, AudioPlayHead, ValueTree, ...
```

> [!warning] ⚠️ stub 的局限
> - 它**只检查语法和签名**，不检查行为
> - 签名可能和你的 JUCE 版本有差异
> - **不能用来编译真正的插件**
>
> 用途：**抓拼写错误、参数类型错误、漏掉的 `override`**。
> 这是"让 AI 写代码"时的一道低成本防线。

---

## 四、`juce_add_plugin` 的常见参数（⚠️ 需核实）

| 参数 | 作用 | 注意 |
|---|---|---|
| `COMPANY_NAME` | 厂商名 | 显示用 |
| `PLUGIN_MANUFACTURER_CODE` | 四字符厂商码 | ⚠️ **不可改** |
| `PLUGIN_CODE` | 四字符插件码 | ⚠️ **不可改** |
| `FORMATS` | 生成哪些格式 | 见上表 |
| `PRODUCT_NAME` | 产品名 | 用户看到的名字 |
| `COPY_PLUGIN_AFTER_BUILD` | 构建后自动装到插件目录 | 开发时很方便 |
| `IS_SYNTH` | 是不是乐器 | 影响宿主分类 |
| `NEEDS_MIDI_INPUT` / `NEEDS_MIDI_OUTPUT` | MIDI 需求 | 声明错误会导致宿主行为异常 |
| `IS_MIDI_EFFECT` | 是不是 MIDI 效果器 | |

> [!warning] ⚠️ 参数名会随 JUCE 版本变化
> 上面这些**我没有在真实 JUCE 上验证**。
> 配置报错时，**查你锁定版本的 JUCE 文档**，不要改代码去迁就 AI 给的写法。

---

## 五、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **四字符代码给 3 或 5 个字符** | AU 验证失败 | 数一遍 |
| 2 | **忘了 `CMAKE_CXX_EXTENSIONS OFF`** | Windows 编不过 | 检查这一行 |
| 3 | **用 Projucer 时代的写法** | 配置报错 | 用 CMake API |
| 4 | **参数名过时** | 配置报错 | 对照你的 JUCE 版本 |
| 5 | **不给 `Standalone`** | 调试麻烦 | 加上 |
| 6 | **`target_link_libraries` 缺模块** | 链接错误 | 检查模块名 |
| 7 | **硬编码路径** | 换机器就坏 | 用 `${CMAKE_CURRENT_SOURCE_DIR}` |
| 8 | **不写 `cmake_minimum_required`** | 行为不确定 | 写清版本 |
| 9 | **把 `build/` 提交进 git** | 仓库混乱 | 加 `.gitignore` |
| 10 | **忘了 Windows 的运行时库设置** | 运行时冲突 | 按平台设置 |

> [!danger] 第 1 条是最隐蔽的
> 四字符代码写成 3 个字符时，**CMake 配置可能不报错**，
> 但 AU 验证会失败（见 [[auval 与 AU 验证]]），而且错误信息很难懂。

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 配置报"未知参数" | JUCE 版本不匹配 | 查锁定版本的文档 |
| AU 验证失败 | 四字符代码不对 | 检查长度 |
| Windows 编不过 | 用了 gnu++ 扩展 | `CMAKE_CXX_EXTENSIONS OFF` |
| 找不到头文件 | 缺 `target_include_directories` | 加上 |
| 宿主找不到插件 | `COPY_PLUGIN_AFTER_BUILD` 装到用户级 | 见 [[插件安装路径规范]] |
| 改了配置没生效 | 没重新配置 | `cmake -B build` 重跑 |

---

## 七、怎么验证

**本机可做**（无 cmake / 无 JUCE）：

```bash
# ① 语法检查（用本库的 stub）
clang++ -std=c++17 -fsyntax-only -I 50-Playground/tools/juce_stub snippet.cpp

# ② CMakeLists 结构校验（括号配对 + 命令名）
python3 - <<'EOF'
import re, pathlib
s = pathlib.Path('CMakeLists.txt').read_text()
d = 0
for ch in s:
    if ch == '(': d += 1
    elif ch == ')': d -= 1
print(f"括号配对: {'✅' if d == 0 else '❌'}")
print(f"命令: {sorted(set(re.findall(r'^\\s*([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(', s, re.M)))}")
EOF
```

**装好 cmake + JUCE 后**：

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

> [!important] 最终验证：用 `Standalone` 跑起来
> 配置成功后，先构建 **Standalone** 目标并运行——
> 不用 DAW 就能确认插件的基本功能。
> 见 [[CMake 基础]]。

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[CMake 基础]] — CMake 通用知识（含本机无 cmake 的替代方案）
- [[CMake 插件项目结构]] — 目录怎么组织
- [[JUCE 的架构与模块划分]] — 模块依赖
- [[版本号与更新分发]] — 四字符代码为什么不能改
- [[跨平台开发 macOS 与 Windows]]
- [[auval 与 AU 验证]] — AU 验证
- [[插件安装路径规范]]

> [!note] 待补充（优先级高）
> - **装 JUCE 后实测本页所有配置**
> - `juce_add_plugin` 的**当前**完整参数列表
> - `FetchContent` 拉取 JUCE 的写法
> - 各模块（`juce_audio_utils` / `juce_dsp` 等）的依赖关系
> - 本库 JUCE stub 的覆盖度提升（按实际报错补签名）
