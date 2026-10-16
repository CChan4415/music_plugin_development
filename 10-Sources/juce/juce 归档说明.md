---
title: juce 归档说明
type: meta
domain: frameworks
status: solid
confidence: high
sources: []
tags: [meta]
created: 2026-10-16
updated: 2026-10-16
---

# 10-Sources/juce/ —— JUCE 官方资料归档

> [!important] 这里放的是**官方原文**，是本库关于 JUCE 的真相锚点
> AGENTS.md §1：`10-Sources/` 下的文件**不得修改**。

## 归档内容

| 文件 | 来源 | 用途 |
|---|---|---|
| [[JUCE 8.0.4 CMake API]] | `docs/CMake API.md`（867 行） | `juce_add_plugin` 全部 84 个参数的权威定义 |
| [[JUCE 8.0.4 官方插件示例 CMakeLists.txt]] | `examples/CMake/AudioPlugin/CMakeLists.txt` | 官方推荐的插件 CMake 骨架 |

## 获取方式（2026-10-16 实测）

```bash
# ⚠️ raw.githubusercontent.com 与 github.com 在本机不可达，
#    但 codeload.github.com 可达（下载 tarball）
curl -sSL -o JUCE-8.0.4.tar.gz \
  "https://codeload.github.com/juce-framework/JUCE/tar.gz/refs/tags/8.0.4"
tar -xzf JUCE-8.0.4.tar.gz
```

> [!warning] ⚠️ 下载未完成
> 本机实测：tarball 下载在 **11 MB / 约 40 MB** 处超时截断，
> 导致 **`modules/` 目录缺失**（tar 按字母序解压，modules 在 examples 之后）。
>
> **影响**：`docs/` 和 `examples/` 拿到了（够核对 CMake API），
> 但**无法真正编译 JUCE 插件**。
>
> 需要在网络更好的环境重新下载才能完成 `modules/` 部分的验证。

## 相关

- [[JUCE 的 CMake API]] — 引用这两份文档的页面
- [[MOC - Frameworks & Toolchain]]
