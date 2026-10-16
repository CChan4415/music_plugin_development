---
title: juce_stub 说明
type: meta
domain: frameworks
status: solid
confidence: high
sources: ["[[JUCE 的 CMake API]]"]
tags: [recipe, verified]
created: 2026-10-16
updated: 2026-10-16
---

# JUCE stub：无 JUCE 环境的语法检查

**用途**：让 Wiki 里的 JUCE 代码片段能在**没有安装 JUCE** 的机器上做语法检查。

## 为什么需要

本机**没有 JUCE、没有 cmake**（实测确认）。
但 Wiki 里的 JUCE 代码如果完全没验证过，就可能带着拼写错误发给读者。

这个 stub 只声明**签名**（不含实现），足以让 `clang++ -fsyntax-only` 抓到：
- 方法名拼错
- 参数类型错误
- 漏掉的 `override`（纯虚函数未实现）
- 少写的成员

## 用法

```bash
clang++ -std=c++17 -fsyntax-only \
    -I 50-Playground/tools/juce_stub \
    your_snippet.cpp
```

代码片段开头加：
```cpp
#include "juce_stub.h"
```

## 自检

```bash
clang++ -std=c++17 -fsyntax-only -I 50-Playground/tools/juce_stub smoke.cpp
# 应无输出（通过）
```

## 覆盖的类（Lead 2026-10-16 补充过）

| 类别 | 类 |
|---|---|
| 核心 | `AudioProcessor`、`AudioProcessorEditor`、`AudioBuffer`、`MidiBuffer` |
| 参数 | `AudioParameterFloat/Bool/Choice`、`RangedAudioParameter`、`AudioProcessorParameter` |
| 状态 | `AudioProcessorValueTreeState`、`ParameterAttachment`、`ValueTree`、`XmlElement`、`var` |
| DSP | `Oversampling`、`DryWetMixer`、`SIMDRegister`、`SIMDFloat` |
| 工具 | `ScopedNoDenormals`、`AbstractFifo`、`SmoothedValue`、`AudioChannelSet` |
| 其他 | `BusesProperties`、`BusesLayout`、`AudioPlayHead`、`File`、`String`、`MemoryBlock` |

## ⚠️ 局限

| 能做 | 不能做 |
|---|---|
| 语法与签名检查 | ❌ 行为验证 |
| 抓拼写/类型错误 | ❌ 编译真插件 |
| 检查 `override` 完整性 | ❌ 替代真 JUCE |

> [!warning] 签名可能与你的 JUCE 版本不同
> stub 是按"常见版本"写的。如果真 JUCE 编译报错而 stub 通过，
> **以真 JUCE 为准**，并回来补 stub。

## 历史

- 初版由子代理创建（2026-10-14）
- Lead 补充（2026-10-16）：`AudioProcessorEditor` 提到命名空间级、
  补 `AudioChannelSet` / `SmoothedValue` / `addParameter`、
  修 `withInput/withOutput` 签名为 `AudioChannelSet`、加 `BusesProperties` 默认构造
