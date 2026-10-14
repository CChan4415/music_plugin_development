---
title: C++ 工具
type: meta
status: solid
updated: 2026-10-14
---

# C++ 工具

## `audio_thread_alloc_detector.cpp`

**用途**：抓住"在音频线程里分配内存"这个头号违规。

```bash
clang++ -std=c++17 audio_thread_alloc_detector.cpp -o detector && ./detector
```

**输出**（已验证）：
```
测试 1: 非音频线程分配
  ✅ 正常分配 42
测试 2: 音频线程里分配（应该被抓到）
  ❌ 检测到音频线程里分配内存！size=4
```

**怎么用到你的插件里**：把这个 `operator new` 重载复制进你的项目，
在 `processBlock` 开头/结尾设置 `inAudioThread` 标志。
Debug 构建时，任何违规分配都会立刻断在调试器里。

见 [[插件验证工具]] 第六节。

> [!warning] 只用于 Debug
> Release 构建里要关掉（有性能开销）。
