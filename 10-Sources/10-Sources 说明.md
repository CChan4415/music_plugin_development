---
title: 10-Sources 说明
type: meta
status: solid
updated: 2026-10-14
---

# 10-Sources

原始资料的记录。**只读——Agent 永远不得修改这里的文件。**

## 子目录

| 目录 | 内容 |
|---|---|
| `books/` | 教材 |
| `standards/` | 规范与权威公式集 |
| `articles/` | 技术文章 |
| `blogs/` | 博客系列 |
| `indexes/` | 资源索引（领域地图） |
| `papers/` | 论文 |
| `talks/` | 视频、讲座 |
| `code-refs/` | 值得读的开源代码库 |

## 已归档（2026-10-14）

| 资料 | 类型 | 为什么收录 |
|---|---|---|
| [[Downey - Think DSP]] | 书 | **用 Python 学 DSP**——正是本库的路径 |
| [[RBJ Audio EQ Cookbook]] | 规范 | **双二阶系数的权威版本**，核对 AI 输出的标准答案 |
| [[Bencina - Real-time audio programming 101]] | 文章 | 实时音频的经典文献，汇集三大平台官方规定 |
| [[Luff - Let's Write A Reverb]] | 文章 | **无魔法数字**的 FDN 混响设计 |
| [[Valhalla DSP - Getting Started With Reverb Design]] | 博客 | 商业混响作者的第一手经验 |
| [[awesome-audio-dsp]] | 索引 | 领域地图；**明确拒收 AI 生成内容** |

## 关键规则

> [!warning] 只存链接和我的理解，不存全文
> 两个原因：
> 1. **版权**（如 Think DSP 是 CC BY-NC，禁止商用）
> 2. **防止幻觉污染**——原文大段复制会让你三个月后分不清哪句是谁说的

> [!tip] 怎么用这些资料
> 它们的核心用途是**验证 AI 输出**。
> 每份资料的页面里都有「怎么用它验证 AI 输出」一节。
>
> **为什么必须用人类写的资料**：
> 你不能用 AI 去验证 AI。见 [[awesome-audio-dsp]] 里那条"拒收 AI 生成内容"的规则。

## 命名规范

`作者 - 标题.md`（如 `Downey - Think DSP.md`）

## 相关

- [[AGENTS]] — 维护契约（§1 禁令：不得修改 Sources）
- [[_meta/taxonomy|命名规范]]
