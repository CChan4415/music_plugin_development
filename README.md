# Music Plugin Development — Personal Knowledge Base

一个用 **Obsidian 当界面、Agent 当维护者**的个人知识库，主题是：**音乐制作插件的开发**。

## 30 秒上手

1. Obsidian → `Open folder as vault` → 选择本目录 `/Users/cc/workspace/music_plugin_development`
2. 从 [[Home]] 开始
3. 有新材料 → 丢进 `00-Inbox/`
4. 让 Agent 整理 → 它会按 [[AGENTS]] 里的契约工作

## 三层结构（别打破它）

```
10-Sources/   原始资料。只读。论文、文档、视频、代码引用。Agent 永不改写。
20-Notes/     你自己的原子笔记。你的理解、疑问、实验记录。
30-Wiki/      Agent 维护的主题页。综合、对比、结论。每句话都要能溯源。
```

**为什么分三层**：LLM 维护 Wiki 最常见的失败是"AI 把自己的幻觉写进了知识库，三个月后你分不清哪句是论文说的、哪句是 AI 编的"。物理隔离是唯一可靠的解法。

## 其余目录

| 目录 | 用途 |
|---|---|
| `00-Inbox/` | 未整理的碎片。允许脏。定期清空。 |
| `40-Projects/` | 具体插件项目（一个项目一个文件，含决策记录） |
| `50-Playground/` | 可运行的代码实验、测量脚本、音频样本 |
| `90-Attachments/` | 图片、音频、PDF |
| `99-Templates/` | 笔记模板 |
| `_meta/` | 知识库自身的元信息：约定、标签体系、路线图、待确认问题 |

## 相关

- 维护契约：[[AGENTS]]
- 待你确认的问题：[[_meta/open-questions]]
- 学习/开发路线：[[_meta/roadmap]]
