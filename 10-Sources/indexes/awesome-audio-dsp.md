---
title: awesome-audio-dsp（领域资源索引）
type: source
domain: frameworks
status: solid
confidence: high
tags: []
source_type: index
url: https://codeberg.org/BillyDM/awesome-audio-dsp
author: Billy Messenger (BillyDM)
year: 2026
created: 2026-10-14
updated: 2026-10-14
---

# awesome-audio-dsp

> [!important] 这是整个音频 DSP 领域的**地图**
> 当你需要找某个方向的资料时，**先来这里查**，而不是直接搜。
> 它的分类方式本身就是一份领域知识结构。

## 元信息

| 项 | 值 |
|---|---|
| 类型 | 精选资源列表（curated list） |
| 作者 | Billy Messenger（BillyDM） |
| **主仓库** | <https://codeberg.org/BillyDM/awesome-audio-dsp> ← 已迁移到这里 |
| GitHub 镜像 | <https://github.com/BillyDM/awesome-audio-dsp>（只读） |
| 许可证 | CC0-1.0（公共领域） |
| 规模 | 1.4k+ star |

> [!note] 仓库已从 GitHub 迁到 Codeberg
> GitHub 上的是**只读镜像**。提交 issue/PR 要去 Codeberg。

## 分类结构（这就是领域地图）

| 分类 | 内容 |
|---|---|
| Code Libraries | 音频软件的实用库 |
| **DSP Cookbooks** | **算法与公式集**（RBJ Cookbook、musicdsp.org 都在这里） |
| DSP Playgrounds | 快速原型工具 |
| Electronics & Embedded | 模拟与嵌入式硬件 |
| Forums | 音频开发社区 |
| **Free Online Textbooks & Courses** | **免费在线教材**（本库收录的多份来自这里） |
| Graphic Design and UX | 插件 GUI 设计资源 |
| Non-Generative Machine Learning | 非生成式 ML（降噪、电路仿真、吉他音箱模拟） |
| Mathematics | 音频 DSP 的数学基础 |
| Open Source Plugins & Software | **可读的开源插件源码** |
| Paid Textbooks | 付费教材 |
| Plugin APIs | 插件 API 及其优劣 |
| Plugin Development Frameworks | 框架及其优劣 |
| Programming Languages | 音频编程语言及其优劣 |
| Publishing | 发布与分发 |
| **Software Optimization** | **音频软件优化技巧**（作者自己写的一份） |
| Sound Design & Music Production | 音色设计（非开发，但理解用途有价值） |
| System Tools | 开发工具 |
| Technical Reading | 文章、博客、论文 |

## 作者给新手的推荐（原文）

作者在 "If I'm a total noob, where should I start?" 里给了三个：

| 推荐 | 说明 | 是否已收录 |
|---|---|---|
| **Will Pirkle** 的两本书 | 常见的新手推荐。作者认为**合成器那本比效果器那本好** | ⬜ 付费 |
| **projet μ**（Yü Fang） | 免费在线课程，**用 C 语言从零讲 DSP**，作者的"首选推荐" | ⬜ 待评估 |
| **Think DSP** | 免费在线书，**用 Python 讲 DSP** | ✅ 已收录 |

> [!tip] 注意作者的判断
> 他认为 projet μ 是"个人首选推荐"，理由是
> **"很好地用代码解释概念，配有帮助性的图形"**，
> 但**需要一些复数和基础积分知识**——"学 DSP 真的绕不过这个"。
>
> 它偏 Linux，但可以在 Windows/macOS 上做。

## ⭐ 一条特别值得注意的规则

> [!warning] 这个列表**明确拒收 AI 生成的内容**
> 原文的 PR 规则里写着：
> > 如果链接的资源是"vibe coded"或大量使用了生成式 AI，**不予接受**。
> > 与 LLM 或其他生成式 AI 技术相关的资源也不接受。
>
> **为什么这对你有价值**：
> 这说明**这个列表里的资源质量有额外保证**——它们是人类专家写的。
>
> **对你的 AI 主导开发流程的意义**：
> 当你需要**验证 AI 输出**时，来这里找的参考资料是**独立于 AI 的**。
> 这正是"参照系"该有的性质——不能用 AI 去验证 AI。

## 怎么用它

| 场景 | 去哪个分类 |
|---|---|
| 需要某个算法公式 | **DSP Cookbooks** |
| 想读开源插件源码 | **Open Source Plugins & Software** |
| 插件跑太慢 | **Software Optimization** |
| 要选框架 | **Plugin Development Frameworks**（有优劣对比） |
| 想系统学 | **Free Online Textbooks & Courses** |
| 要做 ML 音频 | **Non-Generative Machine Learning** |

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[MOC - DSP]]
- [[10-Sources 说明]]
- [[_meta/roadmap|路线图]]

> [!note] 待补充
> - 逐个评估 "Free Online Textbooks" 分类里的免费教材，挑出最适合本库的
> - "Open Source Plugins & Software" 里值得读的代码库（尤其混响/压缩器）
