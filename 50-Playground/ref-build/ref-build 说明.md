---
title: ref-build 说明
type: experiment
domain: frameworks
status: solid
confidence: high
sources: ["[[CMake 基础]]"]
tags: [recipe, verified]
created: 2026-10-15
updated: 2026-10-15
---

# ref-build：最小构建示例

一个不含 JUCE 的最小 C++ 工程，用于验证**构建流程本身**。

## 为什么有这个目录

本机**没有安装 cmake**（实测），但有 `clang++` 和 `make`。
所以这里提供两条路径：

| 文件 | 状态 |
|---|---|
| `Makefile` | ✅ **已实测**（`make` + `make test` 都通过） |
| `CMakeLists.txt` | ⚠️ **仅语法结构校验**（无 cmake，未执行） |
| `plugin.cpp` | ✅ 可编译运行（一个 biquad 低通） |

## 实测输出

```bash
$ cd 50-Playground/ref-build
$ make
clang++ -std=c++17 -O2 -Wall -Wextra -Wpedantic plugin.cpp -o plugin_test

$ make test
  平均输出 0.449387
```

## 用途

- 学 DSP 阶段：**直接用 Makefile 就够**，不需要 CMake
- 要做真插件时：CMake 的价值在跨平台 + JUCE + CI

详见 [[CMake 基础]]。
