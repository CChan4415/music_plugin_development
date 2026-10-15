---
title: auval 与 AU 验证
type: wiki
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# auval 与 AU 验证

> [!important] 一句话
> **`auval` 是 macOS 自带的 Audio Unit 验证工具**——你唯一"零成本立即可用"的插件验证器。
> 它会模拟宿主的各种恶劣调用，提前发现你会在用户那里遇到的问题。

## 本机实测环境

```
AU Validation Tool
Version: 1.10.0
Copyright 2003-2019, Apple Inc.
路径: /usr/bin/auval
```

> [!note] 这是本机实测的输出（2026-10-15）
> `auval` 随 macOS 一起提供，**不需要安装任何东西**。
> 你现在的机器上就能跑。

---

## 一、四字符代码（AU 的身份）

AU 用 **TYPE / SUBT / MANU** 三个四字符代码标识：

```bash
auval -v aufx Gnsx Acme
#          │    │    └─ MANU：厂商代码
#          │    └────── SUBT：子类型（你自己定）
#          └─────────── TYPE：插件类别
```

**TYPE 的常见值**：

| TYPE | 含义 |
|---|---|
| `aufx` | **效果器（Effect）** ← 你要做的 |
| `aumu` | 乐器（Music Device） |
| `augx` | 生成器（Generator） |
| `aumf` | 格式转换 |
| `aumx` | 混音器 |

> [!warning] ⚠️ 完整清单需核实
> 我只确信 `aufx` / `aumu` / `augx` 三个常用值。
> 完整的四字符类型列表**需查 Apple 文档**。

**在 JUCE 里设置**：

```cmake
juce_add_plugin(MyPlugin
    PLUGIN_MANUFACTURER_CODE Acme    # MANU，四字符
    PLUGIN_CODE              Gnsx    # SUBT，四字符
    FORMATS                  AU VST3
    ...)
```

> [!danger] 两个必须注意的点
> 1. **必须是四字符**——多了少了都会失败
> 2. **MANU 最好唯一**（避免和其他厂商冲突）
>
> 具体字符集限制**需查 JUCE / Apple 文档确认**。

**也可以用十六进制**（实测确认可用）：

```bash
# 这两条完全等价
auval -v aufx bpas appl
auval -v 61756678 62706173 6170706C
```

---

## 二、常用命令（实测自 `auval -h`）

| 命令 | 作用 |
|---|---|
| `auval -a` | 列出所有 AU（⚠️ **可能很慢**，会实例化每个 AU） |
| `auval -l` | 列出所有 AU（**不实例化**，更快更安全） |
| `auval -al` | 列出所有 AU **及其位置** |
| `auval -s TYPE` | 列出某类别的 AU（如 `-s aufx`） |
| **`auval -v TYPE SUBT MANU`** | **验证指定的 AU** ← 最常用 |
| `auval -vt TYPE MANU` | 遍历某厂商的所有某类 AU |

> [!tip] 用 `-l` 而不是 `-a`
> `-a` 会**实例化**每个 AU——如果某个 AU 有问题，可能挂起或崩溃。
> `-l` 只列出不实例化。
>
> **我实测时 `auval -a` 挂起了 60 秒以上**（本机 AU 扫描慢），
> 所以本页推荐 `-l`。

---

## 三、严格选项与调试选项（这部分很有价值）

### 严格选项

| 选项 | 检查什么 |
|---|---|
| `-strict` | **启用所有严格检查**（应该默认使用） |
| `-strict_SP` | `AudioUnitScheduleParameter` 输出问题（**已是硬性失败条件**） |
| `-strict_DefP` | 参数默认值是否在 min/max 之间 |
| `-strict_CPUL` | `kAudioUnitProperty_CPULoad` 的实现是否合规 |

> [!important] `-strict` 应该总是加
> 官方说明：不加严格选项时，问题只发**警告**；
> 但"在多数情况下，未来版本的 AUValidation 会自动让这些错误的单元失败"。
>
> **现在就修，别等它变成硬性失败。**

### 调试选项

| 选项 | 作用 |
|---|---|
| `-de` | 遇到**第一个错误**就终止 |
| `-dw` | 遇到**第一个警告**就终止 |
| `-q` | 安静模式（只打印错误/警告） |
| `-r N` | **重复整个验证过程 N 次**（抓 open/init bug） |
| `-stress [N]` | **多线程压力测试**，模拟 N 秒音频 IO（抓竞态） |
| **`-real-time-safety`** | ⭐ **实时安全检查**（抓音频线程里的阻塞调用） |
| `-o` | 只做基本的 open + initialize 测试 |

> [!danger] `-real-time-safety` 是这一页最有价值的选项
> 官方说明：
> > "对音频 IO 运行额外的实时安全测试，**善于捕捉在 AU process 中调用的任何可能阻塞实时线程的函数**。"
> >
> > "（注意：这个测试底层用 **dtrace**，所以用这个选项时要 **sudo** 运行 auval。）"
>
> **它检查的正是本库 [[实时音频线程契约]] 讲的头号违规。**
> 你不需要自己重载 `operator new` 就能抓到音频线程里的分配/加锁。

**推荐命令**：

```bash
# 基础验证 + 严格检查
auval -strict -v aufx Gnsx Acme

# 抓 open/init bug（重复 10 次）
auval -strict -r 10 -v aufx Gnsx Acme

# 实时安全（需要 sudo，用 dtrace）
sudo auval -strict -real-time-safety -v aufx Gnsx Acme

# 多线程压力测试
auval -strict -stress 60 -v aufx Gnsx Acme
```

---

## 四、返回值（脚本里能判断成败）

实测自 `auval -h`：

| 返回值 | 含义 |
|---|---|
| **0** | ✅ OK |
| **-1** | AU failed |
| 4 | Unauthorised (open) |
| 5 | Unauthorised (init) |
| 1 | General Error |
| 2 | Fatal Error |

> [!tip] 可以直接在 CI 里用
> ```bash
> if auval -strict -v aufx Gnsx Acme > /tmp/auval.log 2>&1; then
>     echo "✅ AU 验证通过"
> else
>     echo "❌ AU 验证失败（exit $?）"
>     grep -iE "error|fail|warn" /tmp/auval.log | head -20
> fi
> ```

---

## 五、失败原因清单

> [!warning] 首次跑 auval 大概率会失败
> 这不是坏事——**它提前发现了宿主会发现的问题**。

| # | 原因 | 怎么修 |
|---|---|---|
| 1 | **参数范围不一致** | 检查 min/max/default 是否合理 |
| 2 | **没处理 0 长度缓冲区** | `processBlock` 开头 early return |
| 3 | **`prepareToPlay` 不幂等** | 反复调用不能泄漏或错乱 |
| 4 | **声道配置声明与实际不符** | 检查 `BusesProperties` |
| 5 | **四字符代码不匹配** | Info.plist 与代码要一致 |
| 6 | **参数默认值超范围** | `-strict_DefP` 检查的就是这个 |
| 7 | **音频线程里有阻塞调用** | `-real-time-safety` 会抓 |
| 8 | **open/init 有 bug** | `-r N` 重复测试会暴露 |

---

## 六、auval vs pluginval

| | auval | pluginval |
|---|---|---|
| **来源** | Apple 自带 | Tracktion 开源 |
| **安装** | ✅ 零成本 | 需下载 |
| **格式** | 只测 AU | VST3 / AU / VST2 |
| **平台** | 只有 macOS | 跨平台 |
| **实时安全检查** | ✅ 有（`-real-time-safety`，需 sudo） | ✅ 有 |
| **严格度等级** | 用 `-strict_*` 系列 | 1–10 等级 |
| **CI 友好** | ✅ 有明确返回值 | ✅ |

> [!tip] 两个都用
> - **开发时**：`auval` 零成本，随时跑
> - **发布前**：`pluginval --strictness-level 10` 覆盖更广
>
> 见 [[插件验证工具]]。

---

## 七、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **编造 auval 的参数** | 命令跑不通 | 用 `auval -h` 查真实参数 |
| 2 | **说"auval 能测 VST3"** | 概念错误 | auval 只测 AU |
| 3 | **四字符代码写成 3 或 5 个字符** | 验证失败 | 数一遍 |
| 4 | **建议用 `auval -a`** | 可能挂起 | 用 `-l` |
| 5 | **不知道 `-real-time-safety` 存在** | 漏掉最有价值的检查 | 见上文 |
| 6 | **忘记 `-strict`** | 问题只报警告，容易被忽略 | 总是加 `-strict` |
| 7 | **把 MANU 和 SUBT 搞反** | 找不到插件 | 顺序是 TYPE SUBT MANU |

> [!warning] 第 1 条特别常见
> AI 会**编造看起来合理的参数名**。
> 本页的所有选项都是我从本机 `auval -h` 实测抄下来的。
> **遇到不确定的命令行工具，先跑 `-h`。**

---

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| `auval -a` 卡住 | 会实例化所有 AU | 用 `-l` |
| 找不到 AU | 没装到正确目录 | 见 [[插件安装路径规范]] |
| 改了代码但结果没变 | AU 缓存 | 重启宿主 / 清缓存 |
| 验证通过但宿主里崩溃 | auval 覆盖不全 | 用 pluginval + 实机测试 |
| `-real-time-safety` 报权限错 | 需要 dtrace | 加 `sudo` |
| 每次 `-r N` 结果不同 | 有状态未重置 | 检查 `prepareToPlay` |

---

## 九、怎么验证（开发流程建议）

```bash
# 1. 快速迭代：只做基本 open/init
auval -o -v aufx Gnsx Acme

# 2. 每次改完代码：完整严格验证
auval -strict -v aufx Gnsx Acme

# 3. 里程碑：重复测试抓状态 bug
auval -strict -r 10 -v aufx Gnsx Acme

# 4. 发布前：实时安全 + 压力测试
sudo auval -strict -real-time-safety -v aufx Gnsx Acme
auval -strict -stress 60 -v aufx Gnsx Acme

# 5. 再跑 pluginval 10 级
pluginval --strictness-level 10 --validate MyPlugin.vst3
```

> [!note] 你现在还没有插件
> 所以这些命令暂时没有对象可测。
> **等阶段 4 做出第一个插件时，这一页就是你的验证流程。**

---

## 相关

- [[MOC - Realtime Engineering]]
- [[插件验证工具]] — auval / pluginval / ASan 总览
- [[实时音频线程契约]] — `-real-time-safety` 检查的就是这个
- [[插件安装路径规范]] — AU 装到哪
- [[插件扫描机制]] — 宿主怎么发现插件
- [[插件合规性测试：pluginval]]
- [[跨平台开发 macOS 与 Windows]] — AU 只有 macOS 有

> [!note] 待补充
> - AU 四字符类型与子类型的完整清单（需查 Apple 文档）
> - Info.plist 里 `AudioComponents` 段的正确写法
> - `-stress` 和 `-real-time-safety` 的实际输出样例（需要真实插件）
> - 在 CI 里跑 auval 的完整配置
