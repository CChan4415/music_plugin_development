---
title: exp-000 环境检查
type: experiment
domain: frameworks
status: solid
confidence: high
sources: []
tags: [recipe]
created: 2026-10-14
updated: 2026-10-14
---

# exp-000: 环境检查

```bash
bash check_env.sh
```

## 你现在的情况（2026-10-14 实测）

| 项 | 状态 |
|---|---|
| Python 3.13 | ✅ |
| numpy（系统 Python） | ❌ 需要 `pip install numpy` |
| numpy（DSH 内置 Python） | ✅ 已有，可直接用 |
| clang++ 21 / Xcode CLT | ✅ |
| git | ✅ |
| cmake | ❌ **现在不用装**（阶段 4 才需要） |
| DAW | ⚠️ 只有 GarageBand |

> [!warning] 最重要的一条：**现在只要 numpy 就够了**
> 不要提前装 cmake、JUCE、JUCE 依赖。
> 那些是**几个月后**的事（见 [[_meta/roadmap|路线图]] 阶段 4）。
> 提前装只会让你陷入配置问题，而不是学 DSP。

> [!tip] 两个 Python 的选择
> - **DSH 内置 Python**：已有 numpy，开箱即用，但没有 matplotlib
> - **自己的环境**（推荐）：`conda create -n audiodsp python=3.12 numpy matplotlib scipy -y`
>   有 matplotlib 才能画频响图 —— 而画图是验证 DSP 的主要手段。
