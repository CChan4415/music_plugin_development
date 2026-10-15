---
title: tools 说明
type: meta
domain: realtime
status: solid
confidence: high
sources: []
tags: []
created: 2026-10-14
updated: 2026-10-15
---

# 工具脚本

跨实验复用的脚本。用 Python（numpy/scipy/matplotlib）。

| 脚本 | 用途 | 状态 |
|---|---|---|
| `audio_io.py` | 读写 WAV、测量、测试信号、null test、频响验证 | ✅ 已实现 |
| `vault_health.py` | 知识库健康检查（断链→待写队列、lint） | ✅ 已实现 |
| `check_crossplatform.sh` | 找"到 Windows/Linux 会炸"的代码 | ✅ 已实现 |
| `check_env.sh` | 环境依赖检查（在 `exp-000` 下） | ✅ 已实现 |
| （待添加）`sweep.py` | 生成对数扫频信号 | ⬜ |
| （待添加）`analyze.py` | 读 wav，算 THD / 频率响应，画图 | ⬜ |

> [!note] 让 Agent 写这些脚本
> 这是 AI 辅助开发**性价比最高**的用法：脚本逻辑明确、容易验证、省你大量时间。
> 但**DSP 本身你自己写**。

## 子目录

| 目录 | 说明 |
|---|---|
| `cpp/` | [[C++ 工具]] — 音频线程分配检测器、DSP 微基准 |
| `sanitizer/` | [[sanitizer 工具说明]] — ASan/UBSan 演示（实测抓到越界与五类 UB） |
| `verify/` | 验证脚本（TPT SVF、梳状、FIR、IIR、极零点、振荡器混叠） |

## 相关目录

| 目录 | 说明 |
|---|---|
| `50-Playground/tests/` | [[tests 说明]] — 可复用的 unittest 测试套件 |
| `50-Playground/ref-build/` | [[ref-build 说明]] — 最小构建示例（Makefile 已实测） |
| `50-Playground/exp-007-心理声学/` | [[exp-007 心理声学实测]] — ISO 226 / K 加权 / Bark（子代理产出，Lead 复核） |
| `50-Playground/exp-004-非线性实测/` | [[exp-004 非线性实测]] — 谐波结构实验 |
