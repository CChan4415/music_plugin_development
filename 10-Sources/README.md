---
title: Sources 说明
type: meta
status: solid
updated: 2026-10-14
---

# 10-Sources

原始资料的记录。**只读——Agent 永远不得修改这里的文件。**

## 子目录

| 目录 | 内容 |
|---|---|
| `papers/` | 论文（DSP、心理声学、AI 音频） |
| `books/` | 教材的章节笔记 |
| `talks/` | 视频、讲座、播客 |
| `code-refs/` | 值得读的开源代码库 |
| `standards/` | 规范文档（MIDI、VST3 SDK 文档、LUFS 标准） |

## 一页一篇

每篇资料一个 Markdown 文件，用 [[tpl-source]] 模板。

> [!warning] 关键规则
> **摘要是你的理解，原文引用要标注。**
> 不要把原文大段复制进来——那既侵权，又让你三个月后分不清哪句是谁说的。
> 用链接 + 你自己的话。

## 已经读过的

（待补充，用 Dataview 自动列出）

```dataview
TABLE source_type, author, year
FROM "10-Sources"
WHERE type = "source"
SORT year DESC
```
