---
title: tests 说明
type: meta
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe]
created: 2026-10-15
updated: 2026-10-15
---

# 测试目录

本目录存放可复用的测试示例。

## 运行方式

**本机没有 pytest**（实测确认），用 Python 内置的 `unittest`：

```bash
python3 -m unittest discover -s 50-Playground/tests -v
```

或运行单个文件：

```bash
python3 -m unittest 50-Playground/tests/test_dsp_example.py -v
```

## test_dsp_example.py

演示 DSP 单元测试的六类必测项（全部通过）：

| 测试 | 内容 |
|---|---|
| `test_dc_gain_is_unity` | 低通直流增益 = 1 |
| `test_nyquist_gain_is_zero` | 低通 Nyquist 增益 ≈ 0 |
| `test_minus3db_at_cutoff` | -3dB 点落在设计频率 |
| `test_stable` | 极点在单位圆内 |
| `test_impulse_decays` | 脉冲响应衰减到 0 |
| `test_edge_parameters` | 极端 fc/Q 下不发散（含 subTest） |

实测输出：
```
Ran 6 tests in 0.042s
OK
```

详见 [[DSP 单元测试怎么写]]。
