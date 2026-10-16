---
title: JUCE 的架构与模块划分
type: wiki
domain: frameworks
status: seed
confidence: high
sources: ["[[10-Sources/juce/JUCE 8.0.4 Module Format]]", "[[10-Sources/juce/JUCE 8.0.4 CMake API]]"]
tags: [gotcha]
created: 2026-10-16
updated: 2026-10-16
---

# JUCE 的架构与模块划分

> [!note] ✅ 已用官方文档核对（2026-10-16）
> - **模块依赖**：`10-Sources/juce/JUCE 8.0.4 Module Format.md` 确认
>   "Each module may have dependencies on other modules"，
>   且 `dependencies` 字段可**自动解析**（原文：auto-resolve dependencies）
> - **CMake 写法**：`10-Sources/juce/JUCE 8.0.4 CMake API.md`（867 行官方文档）
> - **代码语法**：本库 JUCE stub 做过 `-fsyntax-only`（见 [[juce_stub 说明]]）
>
> ⚠️ **仍未实测**：本机缺 JUCE 的 `modules/` 源码，未真正编译过插件。

> [!important] 一句话
> **JUCE 是"按功能拆成模块"的**——
> 你只链接需要的模块，避免把整个框架塞进插件。

## 一、核心分层

```
┌─────────────────────────────────────────┐
│ 你的插件代码                              │
│   PluginProcessor / PluginEditor         │
└─────────────────────────────────────────┘
              ↓ 链接
┌─────────────────────────────────────────┐
│ juce_audio_utils   ← 常用工具（推荐）      │
│ juce_audio_processors ← AudioProcessor 基类 │
│ juce_dsp           ← DSP 工具（FFT/滤波）  │
│ juce_audio_basics  ← AudioBuffer 等基础    │
│ juce_gui_extra / juce_gui_basics ← UI    │
│ juce_core          ← 字符串/文件/线程      │
└─────────────────────────────────────────┘
              ↓ 底层
┌─────────────────────────────────────────┐
│ 平台 API（CoreAudio / WASAPI / VST3 SDK…）│
└─────────────────────────────────────────┘
```

> [!note] 依赖是**自下而上**的，且**自动解析**
> JUCE 官方 CMake API 文档原文：
> *"Inter-module dependencies are resolved automatically, so `juce_core`,
> `juce_events` and so on will also be linked automatically."*
>
> 每个模块在自己的 `BEGIN_JUCE_MODULE_DECLARATION` 块里用
> `dependencies:` 字段声明依赖（官方 Module Format 文档确认）。
>
> **你只需要链接最上层那个。**

---

## 二、常用模块速查

| 模块 | 提供什么 | 你需要吗 |
|---|---|---|
| `juce_core` | String / File / Thread / 容器 | ✅ 总是需要（间接） |
| `juce_audio_basics` | **`AudioBuffer`** / `MidiBuffer` / `MidiMessage` | ✅ |
| `juce_audio_processors` | **`AudioProcessor`** / 参数 / 状态 | ✅ **插件必需** |
| `juce_audio_utils` | 便捷工具（推荐起点） | ✅ 建议 |
| **`juce_dsp`** | **FFT / 滤波器 / 过采样 / SIMD** | ✅ **做 DSP 必需** |
| `juce_gui_basics` | Component / Slider / Label | ✅ 有 UI 就需要 |
| `juce_gui_extra` | WebBrowser / CodeEditor 等 | 🟠 视情况 |
| `juce_audio_devices` | 音频/MIDI 设备 IO | 🟠 **插件通常不需要** |
| `juce_audio_formats` | WAV/AIFF 读写 | 🟠 要读 IR/采样就需要 |

> [!tip] 一个实用的最小集合
> ```
> juce_audio_utils      ← 已经包含 processors + basics + gui_basics
> juce_dsp              ← DSP
> ```
> **先只用这两个**，需要时再加。

> [!warning] `juce_audio_devices` 在插件里通常不需要
> 它管的是"直接访问声卡"——那是 **Standalone** 程序才需要的事。
> 插件里由宿主负责音频 IO。
>
> 但如果你要构建 `Standalone` 格式，它会被需要（CMake 会处理）。

---

## 三、关掉不需要的功能（减小体积）

```cmake
target_compile_definitions(MyPlugin PUBLIC
    JUCE_WEB_BROWSER=0            # 不用 WebView → 省几 MB
    JUCE_USE_CURL=0               # 不用网络 → 省依赖
    JUCE_VST3_CAN_REPLACE_VST2=0  # 不用 VST2 兼容
    JUCE_DISPLAY_SPLASH_SCREEN=0  # 关启动画面（需商业授权，见下）
)
```

> [!danger] ⚠️ `JUCE_DISPLAY_SPLASH_SCREEN=0` 有授权前提
> JUCE 的免费档（AGPLv3）**要求显示启动画面**。
> 关掉它需要相应的商业授权。
>
> **不确定时不要关。** 见 [[开源与商业的许可证陷阱]]。

> [!note] 为什么关模块能省体积
> 每个模块都会链接进二进制。
> `JUCE_WEB_BROWSER` 会拉进整个 WebKit——**这是最值得关的一个**。

---

## 四、`AudioProcessor` 的生命周期（核心）

> [!important] 这是插件开发最重要的一张图

```
构造函数              ← ⚠️ 只做轻量初始化（宿主扫描时会调用！）
    ↓
prepareToPlay()       ← ⚠️ 重活都在这里（分配缓冲、建 FFT）
    ↓
processBlock()        ← ⚠️ 实时线程！禁止分配/加锁/IO
    ↕ （反复调用）
releaseResources()
    ↓
析构函数
```

**对应的代码骨架**：

```cpp
class MyProcessor : public juce::AudioProcessor
{
public:
    MyProcessor()
        : AudioProcessor (BusesProperties()
              .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
              .withOutput ("Output", juce::AudioChannelSet::stereo(), true))
    {
        // ⚠️ 只做轻量初始化
        addParameter (gain = new juce::AudioParameterFloat (
            "gain", "Gain", 0.0f, 1.0f, 0.5f));
        // ❌ 不要：读文件、分配大缓冲、建 FFT
    }

    void prepareToPlay (double sampleRate, int samplesPerBlock) override
    {
        // ✅ 重活在这里
        smoothedGain.reset (sampleRate, 0.02);   // 20ms 平滑
    }

    void processBlock (juce::AudioBuffer<float>& buffer,
                       juce::MidiBuffer&) override
    {
        // ⚠️ 实时线程：无分配、无锁、无 IO
        juce::ScopedNoDenormals noDenormals;     // 见 [[denormal 数处理]]
        smoothedGain.setTargetValue (gain->get());
        // ... DSP ...
    }

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "MyPlugin"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return {}; }
    void changeProgramName (int, const juce::String&) override {}
    void getStateInformation (juce::MemoryBlock&) override {}
    void setStateInformation (const void*, int) override {}

private:
    juce::AudioParameterFloat* gain = nullptr;
    juce::SmoothedValue<float> smoothedGain;
};
```

> [!danger] 构造函数不能做重活——这条最容易被忽略
> **宿主扫描插件时会构造它**（见 [[插件扫描机制]]）。
> 构造慢 → 扫描超时 → **插件在宿主里根本不出现**。
>
> 而且症状是"不出现"，不是"崩溃"——**很难联想到构造函数**。

> [!note] 上面的代码用 stub 做过语法检查 ✅
> 但 stub 只验证签名，不验证行为。

---

## 五、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **构造函数里读文件/建 FFT** | 扫描超时，插件不出现 | 移到 `prepareToPlay` |
| 2 | **`processBlock` 里分配** | 爆音 | 重载 `operator new` 检测 |
| 3 | **链接了不需要的模块** | 体积大、依赖多 | 只留必要的 |
| 4 | **以为要链 `juce_audio_devices`** | 多余的依赖 | 插件通常不需要 |
| 5 | **关 splash screen 但不看授权** | 违反 AGPL | 见 [[开源与商业的许可证陷阱]] |
| 6 | **忘了 `ScopedNoDenormals`** | 安静时 CPU 飙升 | 加上 |
| 7 | **`processBlock` 里用 `std::mutex`** | 优先级反转 | 用原子 + 平滑 |
| 8 | **不给 `createEditor` 实现** | 链接错误 | 实现全部纯虚函数 |
| 9 | **参数用裸指针不管理生命周期** | 泄漏/悬空 | 交给 `addParameter` 管理 |

> [!danger] 第 1、2 条是实时音频的两条铁律
> 见 [[实时音频线程契约]]。AI 默认不知道这些约束。

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 宿主里找不到插件 | 构造函数做重活 | 移到 prepareToPlay |
| 偶发爆音 | processBlock 里分配 | 预分配 |
| 插件体积几十 MB | 链了 WebBrowser | `JUCE_WEB_BROWSER=0` |
| 安静时 CPU 高 | denormal | `ScopedNoDenormals` |
| 链接错误 | 缺模块 | 加 `juce::juce_dsp` 等 |
| 编译慢 | 全量编译 JUCE | 用预编译头或 LTO 配置 |

---

## 七、怎么验证

**本机可做**（用 stub）：

```bash
# 检查 AudioProcessor 派生类是否实现了所有纯虚函数
clang++ -std=c++17 -fsyntax-only \
    -I 50-Playground/tools/juce_stub snippet.cpp
```

> [!tip] stub 能抓什么
> - 漏掉的 `override`（纯虚函数未实现 → 编译错误）
> - 参数类型写错
> - 方法名拼错
>
> **这是"让 AI 写代码"时最低成本的一道防线。**

**装好 JUCE 后**：

```bash
cmake -B build && cmake --build build --config Release
# 然后用 Standalone 目标运行
```

**运行时的检查**（见 [[插件验证工具]]）：
- 重载 `operator new` 检测音频线程分配
- `auval -real-time-safety` 检查阻塞调用

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[JUCE 的 CMake API]] — 怎么链接这些模块
- [[CMake 插件项目结构]] — 目录组织
- [[JUCE Component 体系]] — UI 部分
- [[实时音频线程契约]] — 生命周期约束的原因
- [[插件扫描机制]] — 为什么构造函数不能做重活
- [[denormal 数处理]] — `ScopedNoDenormals`
- [[开源与商业的许可证陷阱]] — splash screen 的授权问题
- [[C++ 零基础到音频 DSP 路线]]

> [!note] 待补充（优先级高）
> - **装 JUCE 后实测本页代码**
> - 各模块的**准确**依赖关系（读 JUCE 的 CMakeLists）
> - 预编译头 / 编译加速的配置
> - `AudioProcessorValueTreeState` 的完整用法
> - 状态保存（`getStateInformation`）的正确实现
