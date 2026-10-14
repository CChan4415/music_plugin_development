---
title: 参考实现：最小 WAV 读写（C）
type: experiment
domain: frameworks
status: solid
confidence: high
sources: []
tags: [recipe, verified, cpp]
created: 2026-10-14
updated: 2026-10-14
---

# 参考实现：最小 WAV 读写（C）

> [!warning] 先自己写，再看这个
> 这是 [[C++ 零基础到音频 DSP 路线]] 阶段 2 的核心练习。
> **自己写一遍才会真正理解音频数据是什么。**
> 写完之后再对照这份参考实现，看看哪里不一样。

## 编译运行

```bash
clang wav_minimal.c -o wavtest -lm && ./wavtest
```

## 它做什么

1. 生成 1 秒 440Hz 正弦，**手写 44 字节 RIFF 头**，写成 WAV
2. 读回来，解析头部，确认采样率
3. 每个样本 ×0.5（= -6dB），写出新文件

## 已验证（2026-10-14）

| 检查 | 结果 |
|---|---|
| `out.wav` 主频 | 440.00 Hz ✅ |
| `out.wav` 峰值 | -6.02 dBFS ✅ |
| `out-6db.wav` 峰值 | -12.04 dBFS ✅ |
| 差值 | **6.02 dB**（= 20·log₁₀(0.5)）✅ |

用 `50-Playground/tools/audio_io.py` 的 `report()` 验证的。

## 关键点

- **WAV 头是 44 字节**（标准 PCM）：`RIFF` + size + `WAVE` + `fmt ` 块 + `data` 块
- **`fmt ` 块最后 4 字节是 `bitsPerSample`**，然后才是 `data` 标签
- 音频数据就是 **`int16` 数组**，没有魔法
- **−6dB = ×0.5**（幅度），这是最该记住的换算

> [!tip] 为什么这个练习如此重要
> 因为它把「音频」从神秘的东西变成了**一个数组 + 一个头部**。
> 做完这个，你就理解了：所谓"处理音频"就是"处理数组"。
> 后面所有的 DSP 都是在这个认识上叠加。
