---
title: 插件合规性测试：pluginval
type: wiki
domain: craft
status: seed
confidence: medium
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# 插件合规性测试：pluginval

> [!warning] ⚠️ 本页部分未实测
> **本机没有安装 pluginval**（实测确认）。
> 本页的**命令与参数需你自行核实**——建议以 pluginval 的官方 README 为准。
>
> 标注 ✅ 的部分是从本机实测的（auval、目录结构等）。

> [!important] 一句话
> **pluginval 是跨平台的插件验证器**——它模拟宿主的各种恶劣调用，
> 用 10 个严格等级逐层加深，把"在你机器上能跑"变成"在哪都能跑"。

## 为什么要用

| 问题 | pluginval 怎么抓 |
|---|---|
| 插件在别的宿主里崩 | 模拟多种调用序列 |
| 参数没钳制 | 扫描参数极值 |
| `prepareToPlay` 不幂等 | 反复调用 |
| 状态保存不全 | 保存/恢复往返测试 |
| 音频线程里分配 | 严格模式下会报警 |
| 旁路不透明 | 有专门的旁路测试 |

> [!important] 和 auval 的分工
> | | auval ✅ 本机实测可用 | pluginval ⚠️ 未安装 |
> |---|---|---|
> | 来源 | Apple 自带 | Tracktion 开源 |
> | 格式 | **只测 AU** | VST3 / AU / VST2 |
> | 平台 | 只有 macOS | **跨平台** |
> | 严格等级 | `-strict` 系列 | **1–10 级** |
>
> **两个都跑**：auval 零成本，pluginval 覆盖更广。
> 见 [[auval 与 AU 验证]]。

---

## 一、严格等级（1–10）

> [!important] 等级越高，"越不讲道理"
> 低等级模拟正常使用；高等级模拟**恶意/极端**的宿主行为。

| 等级 | 大致强度 | 适合 |
|---|---|---|
| 1–3 | 基本加载、参数、状态 | 开发中快速检查 |
| 4–6 | 更多调用序列、边界 | 日常 |
| **7–8** | 多实例、并发、极端参数 | 发布前 |
| **9–10** | 最严格（含实时安全、长时间运行） | **发布前必过** |

> [!warning] ⚠️ 具体每级检查什么需核实
> 上面是**大致分类**。**确切的等级定义请查 pluginval 文档**——
> 本页不写死（因为我没有实测环境）。

---

## 二、基本用法（⚠️ 未实测）

```bash
# 最严格验证
pluginval --strictness-level 10 --validate MyPlugin.vst3

# 指定插件类型
pluginval --strictness-level 10 --validate-in-process MyPlugin.vst3

# 常见可选参数（⚠️ 名称需核实）
#   --skip-gui-tests          跳过 GUI 测试（CI 无显示器时用）
#   --randomise               随机化测试
#   --repeat N                重复 N 次
#   --output-dir <path>       输出日志目录
#   --timeout-ms <n>          超时设置
```

> [!danger] ⚠️ 上面这些参数我**没有核实**
> pluginval 的参数在不同版本间会变。
> **跑之前先 `pluginval --help`。**

**推荐的验证流程**：

```bash
# 1. 开发中：低等级快速检查
pluginval --strictness-level 5 --validate MyPlugin.vst3

# 2. 提交前：高等级
pluginval --strictness-level 8 --validate MyPlugin.vst3

# 3. 发布前：最高等级 + 重复
pluginval --strictness-level 10 --repeat 3 --validate MyPlugin.vst3
```

---

## 三、pluginval 会测什么

> [!note] 已知的测试类别（⚠️ 细节需核实）

| 类别 | 检查内容 |
|---|---|
| **加载/卸载** | 反复创建销毁，看是否泄漏 |
| **元数据** | 名称、版本、厂商代码格式 |
| **参数** | 数量、范围、默认值、极值、自动化 |
| **状态** | `getStateInformation` / `setStateInformation` 往返 |
| **音频处理** | 各种 block size、采样率、声道配置 |
| **旁路** | 旁路是否透明（见 [[旁路 bypass 的正确实现]]） |
| **边界** | 0 长度 buffer、极端参数 |
| **多实例** | 同时创建多个实例 |
| **实时安全** | 音频线程里的阻塞调用（高等级） |
| **长时间运行** | 内存是否持续增长 |

> [!tip] 最容易被抓到的三类问题
> 1. **`prepareToPlay` 不幂等**（反复调用出错）
> 2. **状态保存不全**（往返后参数不对）
> 3. **极端参数下崩溃**（用户能拧到的值没测过）

---

## 四、和 AU 验证的配合（✅ auval 本机实测）

**AU 侧用 auval**（本机有，立即可用）：

```bash
# 快速检查
auval -o -v aufx YourSubt YourManu

# 完整严格验证
auval -strict -v aufx YourSubt YourManu

# 重复测试（抓 open/init bug）
auval -strict -r 10 -v aufx YourSubt YourManu

# ⭐ 实时安全检查（需要 sudo，用 dtrace）
sudo auval -strict -real-time-safety -v aufx YourSubt YourManu

# 多线程压力测试
auval -strict -stress 60 -v aufx YourSubt YourManu
```

> [!important] `auval -real-time-safety` 是本机**现在就能用**的最强检查
> 它用 dtrace 抓**音频线程里的阻塞调用**——
> 正是 [[实时音频线程契约]] 讲的头号违规。
>
> **你不需要等 pluginval，现在就能做这个检查。**
> 见 [[auval 与 AU 验证]]。

**返回值**（实测自 `auval -h`）：

| 值 | 含义 |
|---|---|
| **0** | ✅ OK |
| -1 | AU failed |
| 4 | Unauthorised (open) |
| 5 | Unauthorised (init) |

---

## 五、CI 里怎么跑

```yaml
# .github/workflows/validate.yml（示意，未实测）
- name: Download pluginval
  run: |
    # ⚠️ 具体下载地址需查官方 releases
    curl -L -o pluginval.zip <official-url>
    unzip pluginval.zip

- name: Validate
  run: |
    ./pluginval.app/Contents/MacOS/pluginval \
        --strictness-level 10 \
        --validate MyPlugin.vst3
```

> [!danger] ⚠️ 这段是**示意**，不要直接用
> 1. 下载地址我**没有核实**
> 2. 退出码约定我**没有核实**（CI 判断成败要用）
> 3. macOS 上的可执行文件路径需确认
>
> **先在本机跑通，再写进 CI。**

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **编造 pluginval 的参数名** | 命令跑不通 | 先 `--help` |
| 2 | **编造下载地址** | 404 | 查官方 releases |
| 3 | **说 pluginval 能替代 auval** | 概念错 | 两者互补 |
| 4 | **不说严格等级会影响什么** | 以为过 1 级就行 | 发布前用 10 级 |
| 5 | **CI 里不判断退出码** | 测试失败了 CI 还是绿 | 确认退出码约定 |
| 6 | **跳过 GUI 测试但不说明** | CI 里挂住 | 用 `--skip-gui-tests` |
| 7 | **以为"装了就自动跑"** | 没有集成到流程 | 手动/CI 里调用 |
| 8 | **不知道 `auval -real-time-safety`** | 漏掉最强的免费检查 | 见第四节 |

> [!danger] 第 1、2 条是这个领域的典型风险
> pluginval 是**第三方工具**，参数和下载地址会变。
> AI 训练数据里的版本可能过时。
>
> **规则**：命令行工具的参数——**先跑 `--help`**，不要相信 AI。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 命令报"未知参数" | 参数名过时 | 跑 `--help` |
| CI 里卡住 | GUI 测试需要显示器 | `--skip-gui-tests` |
| 验证通过但实际有问题 | 等级太低 | 用 10 级 |
| 下载失败 | 地址变了 | 查官方 releases |
| 本地过、CI 不过 | 环境差异 | 看日志 |
| 找不到插件 | 没装到标准目录 | 见 [[插件安装路径规范]] |

---

## 八、怎么验证

**发布前检查清单**：

```bash
#!/bin/bash
# 插件发布前验证（本机可跑的部分已标注）
PLUGIN="$1"

echo "=== ① AU 验证（✅ 本机可用）==="
if command -v auval >/dev/null; then
    auval -strict -v aufx YourSubt YourManu && echo "✅ auval 通过"
else
    echo "  （不是 macOS 或无 AU）"
fi

echo "=== ② 实时安全检查（✅ 本机可用，需 sudo）==="
echo "  运行：sudo auval -strict -real-time-safety -v aufx YourSubt YourManu"
echo "  ⚠️ 需要真实插件才能跑"

echo "=== ③ pluginval（⚠️ 需先安装）==="
if command -v pluginval >/dev/null; then
    pluginval --strictness-level 10 --validate "$PLUGIN" && echo "✅ pluginval 通过"
else
    echo "  ❌ pluginval 未安装"
    echo "  → 本机实测确认未安装，需从官方 releases 下载"
fi

echo "=== ④ 签名验证（✅ 本机可用）==="
codesign -v --verbose=2 "$PLUGIN" 2>&1 | head -2
spctl -a -vv "$PLUGIN" 2>&1 | head -2
```

> [!note] 本机现状（实测）
> | 工具 | 状态 |
> |---|---|
> | `auval` | ✅ 可用（1.10.0） |
> | `codesign` / `spctl` / `stapler` | ✅ 可用 |
> | `pluginval` | ❌ **未安装** |
>
> 所以在做出第一个插件之前，**你已经有 3 个验证工具可用**。
> pluginval 可以等有插件时再装。

---

## 相关

- [[MOC - Craft & Release]]
- [[auval 与 AU 验证]] — macOS 自带（✅ 已实测）
- [[插件验证工具]] — 所有验证工具总览
- [[插件扫描机制]] — 宿主怎么发现插件
- [[旁路 bypass 的正确实现]] — pluginval 会测旁路
- [[实时音频线程契约]] — 实时安全检查的目标
- [[音频回归测试]] — 自己的测试

> [!note] 待补充（优先级高）
> - **安装 pluginval 并实测本页所有命令**
> - 严格等级 1–10 的**确切**检查内容
> - 下载地址与退出码约定
> - GitHub Actions 的**可运行**配置
> - pluginval 与 auval 的实际覆盖差异（用真实插件对比）
