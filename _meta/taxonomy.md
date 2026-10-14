---
title: 标签与命名规范
type: meta
status: solid
updated: 2026-10-14
---

# 标签与命名规范

## 文件命名

| 类型 | 格式 | 例子 |
|---|---|---|
| Wiki 页 | `概念名.md`（中文名，术语保留英文） | `Biquad 滤波器.md` |
| Source | `作者 年份 - 标题.md` | `Zölzer 2011 - DAFX.md` |
| Note | `YYYY-MM-DD 主题.md` | `2026-10-14 第一次测 THD.md` |
| 决策记录 | `ADR-NNN 标题.md` | `ADR-001 选择 JUCE.md` |
| 项目 | `项目名.md` | `我的第一个压缩器.md` |
| 实验 | `exp-主题/` 目录 | `exp-biquad-sweep/` |

> [!warning] 别用纯英文文件名
> `biquad-filter.md` 和 `Biquad 滤波器.md` 混用会让 `[[链接]]` 很难写。
> 约定：**文件名用人类会念出来的那个词**。

## `domain` 字段（单选）

`audio-fundamentals` · `dsp` · `realtime` · `formats` · `frameworks` · `ui` · `psychoacoustics` · `ai-audio` · `craft`

## `type` 字段（单选）

`wiki` · `note` · `source` · `decision` · `project` · `experiment` · `meta`

## `status` 字段

| 值 | 含义 | 该做什么 |
|---|---|---|
| `stub` | 只有标题和提纲 | 有空就填 |
| `seed` | 有内容，未验证 | 验证后升级 |
| `solid` | 已验证/有来源/实践过 | 定期复查是否 stale |
| `stale` | 可能过时 | 优先更新 |

## 标签（`tags`，可多选）

按**用途**打标，不按主题（主题已由目录 + domain 表达）：

- `#todo` — 待补完
- `#question` — 有疑问待解决
- `#verified` — 我亲手验证过
- `#gotcha` — 踩过的坑（最有价值的一类）
- `#recipe` — 可直接复用的操作步骤
- `#compare` — 对比/选型
- `#math` — 需要推导的内容
- `#cpp` `#python` `#cmake` — 技术栈
- `#juce` `#vst3` `#clap` `#au` — 平台/框架

## 链接规范

- 内部链接用 `[[文件名]]`，不用路径（除非重名）
- 指向未写页面的链接是**好的**——它构成了待写队列，Obsidian 会显示为未解析链接
- 引用外部资料用标准 Markdown 链接，并在 `10-Sources/` 留档
