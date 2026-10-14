---
title: 参考实现：最小 WAV 读写
type: experiment
domain: frameworks
status: solid
confidence: high
sources: []
tags: [recipe, verified, cpp, python]
created: 2026-10-14
updated: 2026-10-14
---

# 参考实现：最小 WAV 读写

> [!warning] 先自己写，再看这个
> 这是 [[C++ 零基础到音频 DSP 路线]] 阶段 2 的核心练习。
> **自己写一遍才会真正理解音频数据是什么。**

## 两个版本

| 文件 | 说明 |
|---|---|
| `wav_minimal.c` | 纯 C，最简版（写 44 字节头 + 读回 + 改增益） |
| `test_wav_edge.cpp` | 用 [[C++ 零基础到音频 DSP 路线]] 阶段 2 的 `loadWav` 读边界文件 |
| `make_testdata.py` | 生成三种边界测试文件 |

## 跑起来

```bash
# 1. 生成测试文件
python3 make_testdata.py

# 2. 编译并测试（把页面里的 loadWav 复制进 test_wav_edge.cpp 的顶部）
clang++ -std=c++17 -Wall -Wextra test_wav_edge.cpp -o test && ./test *.wav
```

## 已验证（2026-10-14）

**最简版 `wav_minimal.c`**：

| 检查 | 结果 |
|---|---|
| 生成文件主频 | 440.00 Hz ✅ |
| 峰值 | -6.02 dBFS ✅ |
| 减 6dB 后 | -12.04 dBFS（差 6.02 dB）✅ |

**页面的 `loadWav` 读三种边界文件**：

| 文件 | 边界 | 结果 |
|---|---|---|
| `stereo16.wav` | 16-bit 立体声交错 | rate=48000 ch=2 samples=96000 peak=0.5000 ✅ |
| `float32.wav` | 32-bit IEEE float | rate=48000 ch=1 samples=48000 peak=0.5000 ✅ |
| `listodd.wav` | **奇数长度 LIST chunk** | rate=48000 ch=1 samples=48000 peak=0.5000 ✅ |

> [!important] 第三个才是真正的考验
> WAV 规定**奇数长度的 chunk 后面要补一个字节**。
> 不处理它 → 后面所有数据错位一位 → 声音变成噪声。
> 页面的代码正确处理了：`f.seekg(chunkStart + size + (size & 1))`

> [!note] Python 的 `wave` 模块读不了 float32
> 它只支持 PCM 整数格式。要读 32-bit float 需要 `soundfile` 或自己解析。
> **页面的 C++ 版本两种都支持** —— 这是手写解析的好处。

## 关键点

- **WAV 头是 44 字节**（标准 PCM）：`RIFF` + size + `WAVE` + `fmt ` 块 + `data` 块
- **不要 `read` 进结构体** —— 编译器 padding 会让字段错位，必须逐字节读
- **WAV 一律小端**（little-endian）
- **逐个 chunk 遍历**，不要假设 `fmt ` 和 `data` 的顺序
- **`size & 1`** 是补齐字节的判断
- **−6dB = ×0.5**（幅度），最该记住的换算

> [!tip] 为什么这个练习如此重要
> 它把「音频」从神秘的东西变成了**一个数组 + 一个头部**。
> 做完这个，你就理解了：所谓"处理音频"就是"处理数组"。
