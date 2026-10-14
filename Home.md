---
title: Home
type: meta
status: seed
updated: 2026-10-14
tags: [moc]
---

# 🎛️ Music Plugin Development

> 从"我做过音乐"到"我能造工具"的知识库。

## 我是谁（决定这个库长什么样）

- 前电子音乐制作人：加法/减法/粒子/模块合成器，压缩/EQ/混响/flanger
- 计算机专业：能写代码
- 目标：结合 AI 与 Agent 开发自己的音乐插件

> [!important] 这个库的核心假设
> 你的**听觉经验**是稀缺资产，**工程知识**是缺口。
> 所以这里不教"什么是混响"，而是教"混响的算法拓扑、实时约束、和怎么验证它没坏"。

---

## 领域地图（MOC）

| 领域 | 内容 | 入口 |
|---|---|---|
| 🎵 音频基础 | 采样、量化、分贝、相位、延迟 | [[MOC - Audio Fundamentals]] |
| 🧮 DSP | 滤波器、FFT、延迟线、非线性、混响 | [[MOC - DSP]] |
| ⚡ 实时工程 | 音频线程契约、无锁、SIMD、性能 | [[MOC - Realtime Engineering]] |
| 🔌 插件格式 | VST3 / AU / CLAP / AAX、宿主兼容 | [[MOC - Plugin Formats]] |
| 🏗️ 框架与工具链 | JUCE、CMake、构建、签名、CI | [[MOC - Frameworks & Toolchain]] |
| 🎨 界面与交互 | 参数设计、表头、缩放、音乐人思维 | [[MOC - UI & UX]] |
| 🎼 音乐声学 | 心理声学、乐器声学、混音惯例 | [[MOC - Music & Acoustics]] |
| 🤖 AI 音频 | 神经建模、可微 DSP、实时推理 | [[MOC - AI Audio]] |
| 📦 手艺与发布 | 授权、定价、分发、防破解、支持 | [[MOC - Craft & Release]] |

---

## 快速通道

- 🚀 **第一次来？** → [[_meta/START-HERE|从这里开始]]
- 🚦 **开发路线图** → [[_meta/roadmap|开发路线图]]
- ❓ **待确认的问题** → [[_meta/open-questions|待确认清单]]
- 📥 **有新材料** → 丢进 `00-Inbox/`，然后让 Agent 处理
- 🤖 **Agent 怎么工作** → [[AGENTS|维护契约]]
- 🧭 **知识库怎么用** → [[_meta/how-to-use|使用说明]]
- 🏷️ **标签体系** → [[_meta/taxonomy|标签与命名规范]]
- 🧩 **为什么这么设计** → [[_meta/kb-design|知识库设计方案]]
- 📖 **中英术语对照** → [[_meta/glossary|术语表]]

---

## 核心页面（已验证）

- [[从音乐制作人到插件开发者]] — 你的知识盘点与缺口地图
- [[实时音频线程契约]] — 初学者插件崩溃的第一大原因
- [[插件格式对比]] — VST3 / AU / CLAP / AAX 怎么选

---

## 状态看板

```dataview
TABLE status, domain, updated
FROM "30-Wiki"
WHERE status = "stub" OR status = "stale"
SORT updated ASC
```

> [!note] 需要 Dataview 插件
> 上面的看板需要安装 Dataview 社区插件。没装也不影响其他内容。
