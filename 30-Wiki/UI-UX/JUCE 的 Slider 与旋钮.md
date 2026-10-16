---
title: JUCE 的 Slider 与旋钮
type: wiki
domain: ui
status: seed
confidence: medium
sources: []
tags: [recipe, gotcha]
created: 2026-10-16
updated: 2026-10-16
---

# JUCE 的 Slider 与旋钮

> [!warning] ⚠️ 本页置信度：medium
> 本机**没有 JUCE**。代码用本库 JUCE stub 做过语法检查（**通过** ✅），
> 但**行为未验证**。API 细节需对照你的 JUCE 版本。

> [!important] 一句话
> **`Slider` 是插件 UI 里最重要的控件**——
> 但"旋钮看起来对"和"参数手感对"是两件事。

## 一、三种样式

| 样式 | 用途 |
|---|---|
| **`Rotary`** | 旋钮（**插件最常见**） |
| `LinearHorizontal` | 水平滑块 |
| `LinearVertical` | 垂直滑块（**混音器推子**） |
| `RotaryHorizontalVerticalDrag` | 旋钮但支持双向拖拽 |

```cpp
#include "juce_stub.h"

void demo()
{
    juce::Slider gain;
    gain.setSliderStyle (juce::Slider::Rotary);
    gain.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 60, 20);
    gain.setRange (0.0, 1.0, 0.01);      // min, max, interval
}
```

> [!note] 上面这段用 stub 验证过语法 ✅

---

## 二、⚠️ 手感比外观重要（这是本页的核心）

> [!important] 三个决定"手感"的设置

### 1. 范围与步进（`setRange`）

```cpp
void demo()
{
    juce::Slider gain, freq;
    gain.setRange (0.0, 1.0, 0.01);          // 增益：0–1，步进 0.01
    freq.setRange (20.0, 20000.0, 1.0);      // 频率：20–20k，步进 1
}
```

> [!danger] 频率类参数**必须**用对数刻度
> 人耳对频率的感知是**对数**的。
> 线性刻度下，20–20000 Hz 的旋钮**前半圈就跑到 10000 Hz**——
> 低频完全没法精细调。
>
> 见下一节。

### 2. 对数刻度（`setSkewFactorFromMidPoint`）

```cpp
void demo()
{
    juce::Slider freq;
    freq.setRange (20.0, 20000.0, 1.0);
    freq.setSkewFactorFromMidPoint (1000.0);   // ⭐ 中点 = 1000 Hz
}
```

> [!tip] `setSkewFactorFromMidPoint` 是最省事的做法
> 你只需要告诉它"中点应该是什么值"，它自动算出偏斜因子。
>
> **对比手算 skew factor**：容易算错，而且换范围就要重算。
>
> ⚠️ 方法名需对照你的 JUCE 版本核实。

### 3. 小数位显示

```cpp
void demo()
{
    juce::Slider gain, freq;
    gain.setNumDecimalPlacesToDisplay (2);    // 显示 0.50
    freq.setTextValueSuffix (" Hz");          // 显示 "1000 Hz"
}
```

> [!warning] 显示位数影响"专业感"
> - 增益显示 `0.50000000` → 业余
> - 显示 `0.50` → 专业
> - 频率显示 `1000.000000 Hz` → 业余
> - 显示 `1.00 kHz` → 更好（但需要自定义文本转换）

---

## 三、完整示例

```cpp
#include "juce_stub.h"

class MyEditor : public juce::AudioProcessorEditor
{
public:
    MyEditor() : juce::AudioProcessorEditor()
    {
        // ---- 增益旋钮 ----
        addAndMakeVisible (gainSlider);
        gainSlider.setSliderStyle (juce::Slider::Rotary);
        gainSlider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 60, 18);
        gainSlider.setRange (0.0, 1.0, 0.01);
        gainSlider.setNumDecimalPlacesToDisplay (2);
        gainSlider.setValue (0.5);

        // ---- 频率旋钮（对数刻度）----
        addAndMakeVisible (freqSlider);
        freqSlider.setSliderStyle (juce::Slider::Rotary);
        freqSlider.setTextBoxStyle (juce::Slider::TextBoxBelow, false, 70, 18);
        freqSlider.setRange (20.0, 20000.0, 1.0);
        freqSlider.setSkewFactorFromMidPoint (1000.0);   // ⭐ 对数手感
        freqSlider.setTextValueSuffix (" Hz");
        freqSlider.setValue (1000.0);

        setSize (300, 200);
    }

    void resized() override
    {
        auto area = getLocalBounds().reduced (10);
        gainSlider.setBounds (area.removeFromLeft (area.getWidth() / 2));
        freqSlider.setBounds (area);
    }

private:
    juce::Slider gainSlider, freqSlider;
};
```

> [!note] 上面这段用 stub 验证过语法 ✅
> （`setSkewFactorFromMidPoint` / `setNumDecimalPlacesToDisplay` /
> `setTextValueSuffix` 等签名都通过了）

---

## 四、参数绑定（关键）

> [!important] Slider 不会自动连到音频参数
> 你需要用 `ParameterAttachment`（或 `AudioProcessorValueTreeState` 的辅助方法）
> 把 UI 和参数连起来。

```cpp
// ⚠️ 伪代码：ParameterAttachment 的准确构造方式需对照你的 JUCE 版本
// 这里只示意"双向绑定 + 抑制通知"的模式，**不能直接编译**
juce::ParameterAttachment attachment {
    *myParameter,
    [this] (float v) { slider.setValue (v, juce::dontSendNotification); }
};
slider.onValueChange = [this] {
    attachment.setValueAsCompleteGesture (slider.getValue());
};
```

> [!danger] 两个必须注意的点
> | 点 | 说明 |
> |---|---|
> | **`dontSendNotification`** | 从参数更新 UI 时不要回调，否则**无限循环** |
> | **不能直接改音频参数** | UI 线程 ≠ 音频线程，见 [[参数自动化与线程安全]] |
>
> ⚠️ `ParameterAttachment` 的确切用法需对照你的 JUCE 版本。

> [!tip] 更省事的做法
> `AudioProcessorValueTreeState` 提供了便捷方法（如 `createSliderAttachment`），
> 自动处理双向绑定和通知抑制。
>
> ⚠️ 方法名需核实。**优先用它，而不是手写 attachment。**

---

## 五、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **频率用线性刻度** | 低频没法调（手感差） | 用 `setSkewFactorFromMidPoint` |
| 2 | **不设 `setRange`** | 默认 0–10，参数范围不对 | 检查 |
| 3 | **忘了 `setTextBoxStyle`** | 没有数值显示 | 设置 |
| 4 | **小数位不设** | 显示 `0.50000000` | `setNumDecimalPlacesToDisplay` |
| 5 | **UI 回调里没抑制通知** | 无限循环 | `dontSendNotification` |
| 6 | **直接改音频参数** | 数据竞争 | 用 attachment |
| 7 | **`setValue` 触发回调又改参数** | 循环/抖动 | 抑制通知 |
| 8 | **忘了 `addAndMakeVisible`** | 控件不可见 | 检查 |
| 9 | **`resized()` 里不设 bounds** | 位置全默认（重叠） | 实现 `resized()` |
| 10 | **步进设成 0** | 连续值但显示固定 | 按需设步进 |

> [!danger] 第 1 条是"手感差"的头号原因
> AI 会写 `freqSlider.setRange(20, 20000)` ——
> 看起来完全正确，但**低频段挤在前 0.1% 的行程里**。
>
> **判据**：旋钮转到中点时，频率应该是**几何中点**（约 630 Hz），
> 不是算术中点（约 10010 Hz）。

> [!danger] 第 5、7 条会导致**无限循环**
> ```
> 用户拖滑块 → onValueChange → 改参数
>                                  ↓
>             参数变化通知 → setValue → onValueChange → ...
> ```
> **必须用 `dontSendNotification` 打断这个环。**

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 低频调不动 | 线性刻度 | `setSkewFactorFromMidPoint` |
| 数值显示很难看 | 小数位太多 | `setNumDecimalPlacesToDisplay` |
| 旋钮拖一下参数就跳 | 通知循环 | 抑制通知 |
| 参数改了 UI 不动 | 没绑定 | 用 attachment |
| 控件不可见 | 忘了 `addAndMakeVisible` | 加上 |
| 控件重叠 | `resized()` 没设 bounds | 实现 `resized()` |
| 拖动时音频卡顿 | UI 线程直接改参数 | 用原子 + 平滑 |

---

## 七、怎么验证

**本机可做**（stub 语法检查）：

```bash
clang++ -std=c++17 -fsyntax-only \
    -I 50-Playground/tools/juce_stub \
    your_slider_snippet.cpp
```

**装好 JUCE 后**（手感验证 —— 这部分只能人工）：

| # | 检查 | 期望 |
|---|---|---|
| 1 | **旋钮中点** | 频率类应是几何中点（约 630 Hz 而非 10010 Hz） |
| 2 | **拖到两端** | 正好是 min/max，不超出 |
| 3 | **反复拖动** | 无卡顿、无参数抖动 |
| 4 | **宿主自动化** | 自动化曲线能驱动旋钮 |
| 5 | **保存/重开工程** | 旋钮位置恢复 |

> [!important] 第 1 条是唯一能"客观判断手感"的方法
> 你不用听声音——**看中点数值**就知道刻度对不对。

```python
# 计算几何中点（用于核对）
import math
lo, hi = 20.0, 20000.0
print(f"  算术中点: {(lo+hi)/2:.0f} Hz   ← 线性刻度会这样")
print(f"  几何中点: {math.sqrt(lo*hi):.0f} Hz  ← 对数刻度应该这样")
# 算术 10010 Hz / 几何 632 Hz
```

---

## 相关

- [[MOC - UI & UX]]
- [[JUCE Component 体系]] — 布局与生命周期
- [[参数自动化与线程安全]] — UI ↔ 音频的通信 ⭐
- [[参数平滑 parameter smoothing]] — 为什么参数要平滑
- [[JUCE 的架构与模块划分]]
- [[等响曲线与频率加权]] — 为什么频率要用对数刻度
- [[插件合规性测试：pluginval]] — GUI 测试

> [!note] 待补充（优先级高）
> - **装 JUCE 后实测本页代码**
> - `ParameterAttachment` / `createSliderAttachment` 的**准确**用法
> - 自定义 LookAndFeel（旋钮外观）
> - 鼠标滚轮 / 精细调整（fine-tune）修饰键
> - 双击复位到默认值
> - 高 DPI 下的旋钮绘制
