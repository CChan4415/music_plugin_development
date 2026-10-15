---
title: CMake 基础
type: wiki
domain: frameworks
status: seed
confidence: medium
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# CMake 基础

> [!warning] ⚠️ 本页部分未实测
> **本机没有安装 cmake**（实测确认）：
> ```
> ❌ cmake 未安装    ❌ ninja 未安装    ❌ ccmake 未安装
> ✅ make (GNU Make 3.81)    ✅ clang++ 21
> ```
> 所以本页的 CMakeLists.txt **只做了语法结构校验**（括号配对、命令名），
> **没有真正执行 `cmake` 配置**。
>
> 标注 `✅ 已实测` 的部分是能用 make/clang 直接验证的。

> [!important] 一句话
> **CMake 不是构建工具，是"构建系统的生成器"**——
> 你写一份 `CMakeLists.txt`，它生成 Makefile / Xcode 工程 / VS 工程。

## 为什么插件开发绕不开它

| 原因 | 说明 |
|---|---|
| **JUCE 官方推荐** | JUCE 的 CMake 支持是当前主流（Projucer 逐渐边缘化） |
| **跨平台** | 一份配置生成 macOS/Windows 两边的工程 |
| **CI 友好** | 命令行可完成全部配置与构建 |
| **依赖管理** | `FetchContent` 自动拉取 JUCE |

> [!note] 你不需要"学 CMake"
> 你需要的是**看懂并修改 JUCE 生成的 CMakeLists.txt**。
> 本页只讲你会实际改到的那部分。

---

## 一、最小心智模型

```
CMakeLists.txt          ← 你写的（源）
      ↓ cmake 配置
build/                  ← 生成的（不要手改）
   ├── Makefile         ← 或 Xcode 工程 / VS 工程
   └── ...
      ↓ make / msbuild
可执行文件 / 插件
```

> [!important] 三条铁律
> 1. **`build/` 目录不要提交进 git**（它是生成的）
> 2. **不要手改 `build/` 里的东西**（下次配置会被覆盖）
> 3. **改了 `CMakeLists.txt` 要重新配置**（`cmake -B build`）

---

## 二、三行命令走完流程（✅ 语法已验证，⚠️ 未执行）

```bash
# ① 配置（生成构建系统）
cmake -B build -DCMAKE_BUILD_TYPE=Release

# ② 构建
cmake --build build --config Release

# ③ 测试
ctest --test-dir build --output-on-failure
```

| 命令 | 作用 |
|---|---|
| `cmake -B build` | 配置，输出到 `build/` |
| `cmake --build build` | 构建（不用管底层是 make 还是 msbuild） |
| `ctest --test-dir build` | 跑测试 |

> [!tip] 用 `-B build` 而不是 `mkdir build && cd build`
> 这是现代 CMake 的推荐写法，**一行搞定且不易出错**。

---

## 三、现代 CMake 的写法（target-based）

> [!important] 老写法 vs 新写法
> ```cmake
> # ❌ 老写法（全局设置，会污染其他 target）
> include_directories(${SOME_DIR})
> add_definitions(-DFOO)
>
> # ✅ 新写法（作用域限定在 target）
> target_include_directories(MyPlugin PUBLIC ${SOME_DIR})
> target_compile_definitions(MyPlugin PRIVATE FOO)
> ```
>
> **新写法的好处**：依赖关系明确，多 target 时不会互相污染。

**三个关键字**：

| 关键字 | 含义 |
|---|---|
| **PRIVATE** | 只有我自己用 |
| **PUBLIC** | 我用，用我的人也要用 |
| **INTERFACE** | 我不用，但用我的人要用 |

> [!tip] 记法
> - 头文件目录通常 `PUBLIC`（使用者也要能找到）
> - 编译警告选项通常 `PRIVATE`（不该强加给使用者）
> - 宏定义看情况

---

## 四、JUCE 插件的 CMakeLists.txt（⚠️ 未实测）

```cmake
cmake_minimum_required(VERSION 3.22)
project(MyPlugin VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)          # ⚠️ 不要用 gnu++ 扩展（跨平台）

# ---- 平台差异 ----
if(APPLE)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "10.13" CACHE STRING "Minimum macOS version")
elseif(WIN32)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

# ---- JUCE ----
add_subdirectory(JUCE)                  # 或用 FetchContent

juce_add_plugin(MyPlugin
    COMPANY_NAME              "Your Name"
    PLUGIN_MANUFACTURER_CODE  Yrnm            # 四字符
    PLUGIN_CODE               Mypl            # 四字符
    FORMATS                   VST3 AU         # ⚠️ AU 只在 macOS 生效
    PRODUCT_NAME              "My Plugin"
    COPY_PLUGIN_AFTER_BUILD   TRUE            # 构建后自动安装到插件目录
    IS_SYNTH                  FALSE
    NEEDS_MIDI_INPUT          FALSE
    NEEDS_MIDI_OUTPUT         FALSE
    IS_MIDI_EFFECT            FALSE)

target_sources(MyPlugin PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp)

target_compile_definitions(MyPlugin PUBLIC
    JUCE_WEB_BROWSER=0                  # ⚠️ 关掉不需要的模块能减小体积
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0)

# ⚠️ 跨编译器警告选项（生成器表达式）
target_compile_options(MyPlugin PRIVATE
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /permissive->
    $<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra -Wpedantic>)

target_link_libraries(MyPlugin PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
    PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags)
```

> [!warning] 上面这份**没有真正跑过 `cmake`**
> 我做的是**结构校验**：
> ```
> 括号配对: ✅ 命令数 17, 未知命令: 无
> 生成器表达式 $< ... >: 平衡
> ```
> JUCE 的 API（`juce_add_plugin` 的参数名）**需对照你的 JUCE 版本文档**。

> [!danger] 几个容易写错的点
> | 点 | 说明 |
> |---|---|
> | `PLUGIN_MANUFACTURER_CODE` / `PLUGIN_CODE` | **必须四字符**，否则 AU 验证失败 |
> | `FORMATS AU` 在 Windows | 会被忽略（不是错误） |
> | `CMAKE_CXX_EXTENSIONS OFF` | 不然用 gnu++ 扩展，跨平台出问题 |
> | `COPY_PLUGIN_AFTER_BUILD` | 开发时很方便，但会装到**用户级**目录 |

---

## 五、生成器表达式：跨编译器的关键

> [!important] 语法：`$<条件:值>`

```cmake
# 按编译器选警告选项
$<$<CXX_COMPILER_ID:MSVC>:/W4>
$<$<NOT:$<CXX_COMPILER_ID:MSVC>>:-Wall -Wextra>

# 按平台
$<$<PLATFORM_ID:Darwin>:...>
$<$<PLATFORM_ID:Windows>:...>

# 按构建类型
$<$<CONFIG:Debug>:-O0 -g>
$<$<CONFIG:Release>:-O3>
```

| 表达式 | 求值时机 |
|---|---|
| `${VAR}` | **配置时**（cmake 运行时） |
| `$<...>` | **生成时 / 构建时**（更灵活） |

> [!warning] 这是 CMake 最容易混淆的一点
> `${}` 在配置时就展开（值必须是那时已知的）。
> `$<>` 延迟到生成时（可以用 `$<CONFIG>` 这种构建时才确定的值）。
>
> **给编译器传参数时，几乎总是用 `$<>`。**

---

## 六、本机能用什么（✅ 已实测）

> [!important] 没有 cmake 时，手写 Makefile 也能开发

本机实测的可用工具链：

```
✅ clang++ 21.0.0 (arm64)
✅ GNU Make 3.81
✅ ar / ld / nm / strip（Xcode CLT）
❌ cmake / ninja
```

**一个可用的 Makefile**（✅ 已实测构建成功）：

```makefile
CXX      := clang++
CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -Wpedantic
TARGET   := plugin_test
SRC      := plugin.cpp

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $< -o $@

test: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)
```

实测输出：
```
$ make
clang++ -std=c++17 -O2 -Wall -Wextra -Wpedantic plugin.cpp -o plugin_test

$ make test
  平均输出 0.449387
```

> [!tip] 学 DSP 阶段用 Makefile 就够
> CMake 的价值在**跨平台 + JUCE + CI**。
> 你**现在**（学 DSP、写小实验）用 `clang++` 直接编译或简单 Makefile 完全够。
>
> **等要做真插件时再上 CMake。**

---

## 七、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **用老写法（`include_directories`）** | 全局污染 | 用 `target_*` |
| 2 | **`${}` 和 `$<>` 混用** | 配置时变量未定义 | 给编译器传参用 `$<>` |
| 3 | **忘了 `CMAKE_CXX_EXTENSIONS OFF`** | 用了 gnu++ 扩展 | 检查这一行 |
| 4 | **PLUGIN_CODE 不是四字符** | AU 验证失败 | 数一遍 |
| 5 | **给过时的 JUCE API** | 配置报错 | 对照你的 JUCE 版本 |
| 6 | **把 `build/` 提交进 git** | 仓库混乱 | 加 `.gitignore` |
| 7 | **假设 cmake 已安装** | 用户跑不起来 | 文档里写清依赖 |
| 8 | **硬编码绝对路径** | 换机器就坏 | 用 `${CMAKE_CURRENT_SOURCE_DIR}` |
| 9 | **不写 `cmake_minimum_required`** | 行为不确定 | 写清最低版本 |
| 10 | **忘了 Windows 的 `MSVC_RUNTIME_LIBRARY`** | 运行时库冲突 | 按平台设置 |

> [!danger] 第 5 条是本库的实际风险
> **JUCE 的 CMake API 在版本间会变**（参数名、必需项）。
> AI 给的写法可能对应旧版本。
>
> **判据**：配置报错时，查你**锁定版本**的 JUCE 文档，不要改代码去迁就 AI。

---

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 改了 CMakeLists 没生效 | 没重新配置 | `cmake -B build` 再跑一次 |
| 找不到头文件 | 没设 `target_include_directories` | 加上 |
| 换机器就编不过 | 硬编码路径 | 用 CMake 变量 |
| 插件装了但宿主找不到 | `COPY_PLUGIN_AFTER_BUILD` 装到了用户级 | 检查两个目录 |
| macOS 能编，Windows 不能 | 用了 gnu++ 扩展 / 平台 API | `CMAKE_CXX_EXTENSIONS OFF` + 条件编译 |
| 配置很慢 | 每次重新下载 JUCE | 用 `FetchContent` 的缓存 |
| `ccache` 没生效 | 没配置 | 设 `CMAKE_CXX_COMPILER_LAUNCHER` |

---

## 九、怎么验证

**如果你装了 cmake**：

```bash
# 配置（看有没有错误）
cmake -B build -DCMAKE_BUILD_TYPE=Release

# 看它生成了什么
ls build/

# 构建
cmake --build build --config Release

# 跑测试
ctest --test-dir build --output-on-failure
```

**本机（无 cmake）能做的**：

```bash
# ① 语法结构校验（括号、命令名）
python3 - <<'EOF'
import re, pathlib
s = pathlib.Path('CMakeLists.txt').read_text()
depth = 0
for ch in s:
    if ch == '(': depth += 1
    elif ch == ')': depth -= 1
print(f"括号配对: {'✅' if depth == 0 else '❌'}")
cmds = set(re.findall(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', s, re.M))
print(f"用到的命令: {sorted(cmds)}")
EOF

# ② 用 Makefile 验证编译选项本身是否正确（✅ 本机可做）
clang++ -std=c++17 -O2 -Wall -Wextra -Wpedantic plugin.cpp -o /dev/null && echo "✅ 编译选项有效"
```

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[C++ 零基础到音频 DSP 路线]] — 学习路径
- [[跨平台开发 macOS 与 Windows]] — 平台差异
- [[Python 优先的 DSP 学习路径]] — 现阶段可以先用 clang++ 直接编译
- [[插件验证工具]]
- [[音频回归测试]] — CI 里怎么跑

> [!note] 待补充（优先级高）
> - **装 cmake 后实测本页所有配置**
> - JUCE `juce_add_plugin` 的**当前**参数列表
> - `FetchContent` 拉取 JUCE 的写法
> - GitHub Actions 里的 CMake 构建配置
> - ccache / sccache 的配置
