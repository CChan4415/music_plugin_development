---
title: JUCE Component 体系
type: wiki
domain: ui
status: seed
confidence: high
sources: ["[[10-Sources/juce/JUCE 8.0.4 官方插件编辑器示例.cpp]]", "[[10-Sources/juce/JUCE 8.0.4 CMake API]]"]
tags: [recipe, gotcha]
created: 2026-10-16
updated: 2026-10-16
---

# JUCE Component 体系

> [!note] ✅ 已用 JUCE 8.0.4 官方示例核对（2026-10-16）
> - **权威来源**：`examples/CMake/AudioPlugin/PluginEditor.cpp`（官方最简编辑器）
> - **代码语法**：本库 JUCE stub 做过 `-fsyntax-only`（见 [[juce_stub 说明]]）
>
> ⚠️ **仍未实测**：本机缺 JUCE `modules/` 源码，**未真正编译过**。

> [!important] 一句话
> **JUCE 的 UI 只有一个基础类：`Component`。**
> 所有可见的东西（滑块、按钮、整个编辑器）都是它的子类。

## 一、Component 的核心概念

| 概念 | 说明 |
|---|---|
| **父子关系** | Component 可以包含子 Component；子组件坐标**相对于父** |
| **`paint(Graphics&)`** | 画自己（**只画自己的区域**） |
| **`resized()`** | 布局变化时调用（**在这里摆放子组件**） |
| **`setBounds(x,y,w,h)`** | 位置与大小 |
| **`addAndMakeVisible(child)`** | 添加子组件并让它可见 |

> [!important] 两条最容易搞错的规则
> 1. **坐标是相对于父组件的**（不是屏幕绝对坐标）
> 2. **`paint()` 里不要摆放子组件**——那是 `resized()` 的职责

---

## 二、最小编辑器

```cpp
#include "juce_stub.h"

class MyEditor : public juce::AudioProcessorEditor
{
public:
    MyEditor() : juce::AudioProcessorEditor()
    {
        // ① 创建并添加子组件
        addAndMakeVisible (gainSlider);
        gainSlider.setRange (0.0, 1.0, 0.01);
        gainSlider.setSliderStyle (juce::Slider::Rotary);
        gainSlider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 60, 20);

        addAndMakeVisible (gainLabel);
        gainLabel.setText ("Gain", 0);
        gainLabel.attachToComponent (&gainSlider, false);

        // ② 设置编辑器自身大小
        setSize (300, 200);
    }

    void paint (juce::Graphics& g) override
    {
        // ⚠️ 只画自己，不要在这里摆放子组件
        g.fillAll();
    }

    void resized() override
    {
        // ⚠️ 布局都在这里
        auto area = getLocalBounds();
        gainSlider.setBounds (area.reduced (20));
    }

private:
    juce::Slider gainSlider;
    juce::Label  gainLabel;
};
```

> [!note] 上面这段用 stub 验证过语法 ✅
> stub 只检查签名，不检查行为。

---

## 三、`resized()` 与布局

> [!important] `resized()` 是唯一的布局入口
> 窗口大小变化、父组件变化 → JUCE 自动调用 `resized()`。
> **你在这里决定每个子组件的位置。**

> [!important] ⭐ 官方示例的注释确认了这个职责划分
> JUCE 8.0.4 `PluginEditor.cpp` 原文：
> ```cpp
> void AudioPluginAudioProcessorEditor::resized()
> {
>     // This is generally where you'll want to lay out the positions of any
>     // subcomponents in your editor..
> }
> ```
>
> 而 `paint()` 的注释是：
> ```cpp
> // (Our component is opaque, so we must completely fill the background with a solid colour)
> ```
> → **`paint` 负责画背景，`resized` 负责摆位置。** 职责不重叠。

**常用的布局写法**（✅ 官方示例里就有这个模式）：

> [!important] ⭐ 官方真实用法（JUCE 8.0.4 `SurroundPluginDemo.h`）
> ```cpp
> void resized() override
> {
>     layoutName.setBounds (getLocalBounds().removeFromTop (20));
> }
> ```
> 以及：
> ```cpp
> void resized() override
> {
>     auto b = getLocalBounds();
>     layoutName.setBounds (b.removeFromBottom (20));
> }
> ```
> **`getLocalBounds().removeFromTop/Bottom(...)` 是官方惯用法**，
> 不是我的臆造。

```cpp
void resized() override
{
    auto area = getLocalBounds();

    // 顶部留一条给标题
    auto top = area.removeFromTop (40);
    titleLabel.setBounds (top);

    // 底部放按钮
    auto bottom = area.removeFromBottom (30);
    bypassButton.setBounds (bottom.removeFromLeft (80));

    // 剩下的区域平分给两个滑块
    auto left  = area.removeFromLeft (area.getWidth() / 2);
    gainSlider.setBounds (left.reduced (10));
    mixSlider .setBounds (area.reduced (10));
}
```

> [!tip] `removeFrom*` 是 JUCE 的布局惯用法
> 它**从区域里切一块出来**，剩下的继续用。
> 比手算坐标清晰得多，也不容易出错。
>
> ⚠️ `Rectangle` 的 `removeFromTop` 等方法需对照你的 JUCE 版本。

> [!danger] 不要在 `paint()` 里布局
> `paint()` 可能被**频繁调用**（重绘），在里面改子组件位置会导致：
> - 性能问题
> - 递归重绘
> - 难以调试的布局抖动

---

## 四、编辑器与处理器的关系

> [!important] 三个必须知道的约束

| # | 约束 | 原因 |
|---|---|---|
| 1 | **编辑器可以被销毁重建** | 宿主随时关闭/重开 UI 窗口 |
| 2 | **编辑器不能持有处理器的所有权** | 处理器活得比编辑器久 |
| 3 | **UI 线程 ≠ 音频线程** | 见 [[参数自动化与线程安全]] |

```cpp
// ✅ 正确：用引用
class MyEditor : public juce::AudioProcessorEditor
{
public:
    explicit MyEditor (MyProcessor& p)
        : juce::AudioProcessorEditor (&p), processor (p) {}
private:
    MyProcessor& processor;      // ✅ 引用，不持有所有权
};

// ❌ 错误：假设编辑器生命周期 == 插件生命周期
```

> [!danger] 约束 1 的后果
> 用户关掉插件窗口再打开 → **新的编辑器实例**。
> 如果你在构造函数里做了重活（读文件、建大缓冲），**每次开窗都会卡一下**。
>
> **重活应该在 `prepareToPlay` 或处理器里做一次。**

---

## 五、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **在 `paint()` 里布局** | 性能问题、布局抖动 | 移到 `resized()` |
| 2 | **用绝对坐标** | 缩放/换尺寸就错位 | 用 `removeFrom*` |
| 3 | **忘了 `setSize()`** | 窗口大小是 0，什么都看不见 | 检查构造函数 |
| 4 | **编辑器持有处理器所有权** | 悬空指针崩溃 | 用引用 |
| 5 | **构造函数里做重活** | 每次开窗卡顿 | 移到处理器 |
| 6 | **UI 线程直接改音频参数** | 数据竞争 | 用 `std::atomic` + 平滑 |
| 7 | **`addAndMakeVisible` 之后才 `setBounds`** | 位置在 `resized()` 前是错的 | 都在 `resized()` 里设 |
| 8 | **忘了实现 `resized()`** | 子组件位置全是默认值 | 实现它 |
| 9 | **坐标用屏幕绝对位置** | 完全错位 | 记住是**相对父组件** |
| 10 | **在 `paint()` 里分配对象** | 频繁重绘 → 性能差 | 预创建 |

> [!danger] 第 3 条是最常见的"什么都看不见"
> `AudioProcessorEditor` 默认大小可能是 0×0。
> **不调 `setSize()` → 窗口是空的**，而没有任何报错。

> [!important] ⭐ 官方示例的注释直接确认了这一点
> JUCE 8.0.4 `examples/CMake/AudioPlugin/PluginEditor.cpp` 原文：
> ```cpp
> // Make sure that before the constructor has finished, you've set the
> // editor's size to whatever you need it to be.
> setSize (400, 300);
> ```
> **"before the constructor has finished"** —— 构造函数结束前必须设好大小。

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 窗口一片空白 | 没调 `setSize()` | 在构造函数里设 |
| 子组件位置不对 | 坐标算错/没实现 `resized()` | 用 `removeFrom*` |
| 缩放时布局乱 | 用了绝对坐标 | 相对布局 |
| 开窗卡顿 | 构造函数做重活 | 移到处理器 |
| 崩溃 | 编辑器持有处理器所有权 | 用引用 |
| 参数改了音频没反应 | UI 线程没同步 | 见 [[参数自动化与线程安全]] |
| 重绘闪烁 | 在 `paint()` 里改布局 | 移到 `resized()` |

---

## 七、怎么验证

**本机可做**（用 stub 做语法检查）：

```bash
clang++ -std=c++17 -fsyntax-only \
    -I 50-Playground/tools/juce_stub \
    your_editor_snippet.cpp
```

**stub 能抓什么**：
- 方法名拼错（`setSize` vs `setBounds`）
- 漏掉 `override`
- 参数类型错误

**装好 JUCE 后**（运行时验证）：

| # | 检查 | 期望 |
|---|---|---|
| 1 | 窗口能打开 | 有内容，大小正确 |
| 2 | **反复开关窗口** | 不崩溃、不泄漏、不卡顿 |
| 3 | 缩放窗口 | 布局正确重排 |
| 4 | 旋钮改参数 | 音频有反应 |

> [!important] 第 2 条最容易被忽略
> **反复关开插件窗口**——如果每次内存增长或越来越慢，
> 说明你在编辑器里做了本该只做一次的事。

---

## 相关

- [[MOC - UI & UX]]
- [[JUCE 的 Slider 与旋钮]] — 最常用的子组件
- [[JUCE 的架构与模块划分]] — 编辑器在处理器的位置
- [[参数自动化与线程安全]] — UI ↔ 音频的通信
- [[JUCE 的 CMake API]]
- [[插件合规性测试：pluginval]] — GUI 测试
- [[UI 设计原则]]（待写）

> [!note] 待补充（优先级高）
> - **装 JUCE 后实测本页代码**
> - `Rectangle::removeFrom*` 的准确 API
> - `Component::paint` 的裁剪规则
> - 自定义 LookAndFeel
> - 高分屏（Retina）处理
> - FlexBox / Grid 布局
