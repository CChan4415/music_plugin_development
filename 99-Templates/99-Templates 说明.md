---
title: 99-Templates 说明
type: meta
status: solid
updated: 2026-10-14
---

# 99-Templates

笔记模板。在 Obsidian 里用 **Templates 核心插件**调用（设置里已指向本目录）。

## 模板清单

| 模板 | 什么时候用 |
|---|---|
| [[tpl-wiki]] | 新建 `30-Wiki/` 知识页（含必备结构骨架） |
| [[tpl-source]] | 归档一份外部资料到 `10-Sources/` |
| [[tpl-note]] | 记录你自己的理解、判断、疑问 |
| [[tpl-gotcha]] | **踩坑记录**（最有价值的一类，打 `#gotcha` 标签） |
| [[tpl-decision]] | 技术选型决策（ADR 格式：背景/选项/决定/理由/后果） |
| [[tpl-project]] | 新建插件项目 |

## 怎么用

1. `Cmd+P` → `Templates: Insert template`
2. 选对应模板
3. 填 frontmatter（`domain`、`tags` 必填）

> [!tip] 最该多写的是 tpl-gotcha
> 官方文档不会写"我在 macOS 26 上遇到 X 报错怎么解决"。
> **踩坑记录是知识库里最不可替代的一类内容**——见 [[2026-10-14 测量工具会骗你 —— 十次踩坑记录]]。

## 相关

- [[Home]]
- [[AGENTS]] — frontmatter 规范
- [[_meta/taxonomy|标签与命名规范]]
