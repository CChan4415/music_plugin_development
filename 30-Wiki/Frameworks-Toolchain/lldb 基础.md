---
title: lldb 基础
type: wiki
domain: frameworks
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-16
updated: 2026-10-16
---

# lldb 基础

> [!important] 一句话
> **lldb 是 macOS 上的调试器**（相当于 Linux 的 gdb）。
> 但音频插件开发里，**它抓不到最常见的 bug**——那些 bug 不崩溃。

## 本机实测的工具状态

| 工具 | 状态 |
|---|---|
| **`lldb`** | ✅ `lldb-2100.0.17.203` |
| `dsymutil` | ✅ 可用 |
| `atos` | ✅ 可用（符号化地址） |
| `dwarfdump` | ✅ 可用 |
| `nm` | ✅ `llvm-nm` |
| `otool` | ✅ `llvm-otool` |
| `lldb-server` | ❌ 无（远程调试用不上） |

---

## 一、⚠️ 实测：lldb 抓不到"不崩溃的 bug"

> [!danger] 这是本页最重要的发现
> **测试**：故意越界写 12 个 float 到 `new float[8]` 的缓冲区。

| 运行方式 | 结果 |
|---|---|
| **裸跑（无 sanitizer）** | **`done, buf[0]=0.000`，退出码 0** ⚠️ |
| 大幅越界（10 万次） | **退出码 0**（也没崩） |
| **ASan** | **`heap-buffer-overflow`**，给出精确地址 ✅ |

> [!important] 为什么这对音频开发特别重要
> **音频插件里最常见的 bug 都不崩溃**：
> | Bug | 崩溃吗 |
> |---|---|
> | 越界写几个 float | ❌ 通常不崩 |
> | **音频线程分配内存** | ❌ 不崩（只是偶发爆音） |
> | **NaN 污染** | ❌ 不崩（静音或噪声） |
> | **数据竞争** | ❌ 通常不崩 |
> | 参数没钳制 | ❌ 不崩 |
>
> **lldb 只在"崩溃"或"你主动下断点"时有用。**

> [!tip] 所以正确的工具顺序
> ```
> ① ASan / UBSan / TSan  ← 抓不崩溃的 bug（见 插件验证工具）
> ② lldb                 ← 崩溃了 / 要理解执行流程
> ```
>
> **不要指望 lldb 发现音频线程的实时安全问题。**

---

## 二、批处理模式（本库实测有效）

> [!important] lldb 可以脚本化——这对"让 AI 帮你调试"很有用

```bash
# 把命令写进文件
cat > /tmp/cmds.txt <<'EOF'
breakpoint set --name main
run
next
frame variable buf
bt 5
quit
EOF

# 批处理执行
lldb -b -s /tmp/cmds.txt ./myprogram
```

**实测输出**（本机验证）：
```
(lldb) breakpoint set --name main
Breakpoint 1: where = lldb_demo`main + 20 at lldb_demo.cpp:8
(lldb) run
Process 2473 stopped
* thread #1, stop reason = breakpoint 1.1
    frame #0: lldb_demo`main at lldb_demo.cpp:8
-> 8   	int main(){
(lldb) frame variable buf
(float *) buf = 0x0000603000001f00
```

> [!tip] 批处理模式的价值
> - **可复现**（命令存成文件，能进 git）
> - **可交给 AI**（把命令和输出一起贴给它）
> - **可以进 CI**（自动跑崩溃分析）

---

## 三、最常用的命令

| 命令 | 简写 | 作用 |
|---|---|---|
| `breakpoint set --name X` | `b X` | 在函数 X 下断点 |
| `breakpoint set --file F --line N` | `b F:N` | 在文件行下断点 |
| `run` | `r` | 运行 |
| `next` | `n` | 下一行（不进入函数） |
| `step` | `s` | 下一步（进入函数） |
| `continue` | `c` | 继续 |
| **`frame variable`** | `fr v` | **看当前作用域的所有变量** |
| `expr X` | `p X` | 求值表达式 |
| **`bt`** | — | **回溯调用栈** |
| `thread backtrace all` | — | 所有线程的回溯 |
| `quit` | `q` | 退出 |

> [!important] 三个最常用的
> 1. **`bt`** —— 崩溃时第一件事
> 2. **`frame variable`** —— 看变量的实际值（比 `printf` 强）
> 3. **`expr`** —— 现场算表达式

---

## 四、音频插件的调试场景

### 场景 1：崩溃在 `processBlock`

```bash
lldb -b -s /tmp/cmds.txt ./Standalone
# cmds.txt:
#   run
#   bt 10
#   frame variable
#   quit
```

> [!tip] 用 `Standalone` 目标调试最方便
> 见 [[JUCE 的 CMake API]]——`Standalone` 格式生成一个**能直接运行的程序**，
> 不用开 DAW 就能在 lldb 里跑。

### 场景 2：某个参数的值不对

```bash
breakpoint set --file PluginProcessor.cpp --line 120
run
frame variable gain cutoff
expr gain->get()
```

### 场景 3：多线程问题

```bash
run
# 崩溃后
thread backtrace all        # ⭐ 看所有线程
thread list
```

> [!warning] 但多线程问题**用 lldb 效率低**
> 数据竞争是**概率性**的——你可能跑 100 次都不崩。
> **用 TSan**（见 [[ThreadSanitizer 与内存序]]）。

---

## 五、符号化（symbolication）

> [!note] 崩溃日志里只有地址时

```bash
# ① 看地址对应哪个函数（需 dSYM）
atos -o MyPlugin.dSYM/Contents/Resources/DWARF/MyPlugin -arch arm64 0x100002345

# ② 检查二进制里有没有调试信息
dwarfdump --debug-info MyPlugin | head

# ③ 看符号表
nm -C MyPlugin | grep processBlock

# ④ 看依赖和架构
otool -L MyPlugin
```

> [!danger] ⚠️ 本机实测的一个限制
> ASan 运行时报告：
> ```
> WARNING: failed to spawn external symbolizer (errno: 9)
> Failed to use and restart external symbolizer!
> ```
> 这是**沙箱限制**导致 ASan 无法调用符号化工具。
> **地址仍然准确**，只是没有函数名/行号。
>
> ⚠️ 正常环境下不应出现这个警告。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **以为 lldb 能发现所有 bug** | 漏掉不崩溃的问题 | 配合 sanitizer |
| 2 | **建议用 `printf` 调试** | 音频线程里 IO 会爆音 | 用断点 |
| 3 | **在音频线程下断点** | 时序完全改变 | 只调非实时路径 |
| 4 | **`-O2` 下调试** | 变量被优化掉 | 用 `-O0 -g` |
| 5 | **不生成调试信息** | 只有地址 | 加 `-g` |
| 6 | **用 gdb 的命令** | lldb 不认 | 用 lldb 语法 |
| 7 | **忘记 `bt`** | 不知道调用链 | 崩溃先 `bt` |
| 8 | **手动敲交互命令** | 无法复现/进 CI | 用批处理模式 |
| 9 | **以为"没崩就是没问题"** | ⚠️ **本页实测反例** | 用 sanitizer |
| 10 | **在生产构建里留 `-g`** | 二进制变大 | 发布版去掉 |

> [!danger] 第 3 条对音频很关键
> 在 `processBlock` 里下断点会让**音频线程暂停**——
> 宿主可能因此超时、断音、甚至崩溃。
>
> **调试实时代码时**：
> - 优先在**非实时路径**下断点（参数设置、状态保存）
> - 或用**日志 + 离线分析**
> - 或用 `Standalone` 目标（没有宿主的时间压力）

> [!danger] 第 9 条是本页的核心
> 实测：越界写 12 个 float、10 万次越界 —— **都不崩溃**。
> 如果你只靠 lldb（和"跑起来看看"），**永远发现不了**。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 看不到变量值 | `-O2` 优化掉了 | 用 `-O0 -g` |
| 只有地址没有函数名 | 没调试信息 | 加 `-g` |
| 断点不生效 | 优化/内联 | `-O0` |
| 崩溃日志看不懂 | 没符号化 | 用 `atos` |
| 调试时爆音 | 在音频线程断点 | 换地方 |
| 问题复现不了 | 时序相关 | 用 sanitizer |
| lldb 命令报错 | 用了 gdb 语法 | 查 lldb 语法 |

---

## 八、怎么验证

**本机可做的调试流程**：

```bash
# ① 带调试信息 + sanitizer 编译（⭐ 推荐组合）
clang++ -std=c++17 -O0 -g \
    -fsanitize=address,undefined -fno-sanitize-recover=all \
    mydsp.cpp -o mydsp_dbg

# ② 先跑 sanitizer（抓不崩溃的 bug）
./mydsp_dbg
# 期望：无输出（干净）或明确报错

# ③ 再上 lldb（如果需要理解流程）
cat > /tmp/cmds.txt <<'EOF'
breakpoint set --name main
run
next
frame variable
bt 5
quit
EOF
lldb -b -s /tmp/cmds.txt ./mydsp_dbg

# ④ 崩溃时符号化
atos -o mydsp_dbg.dSYM/Contents/Resources/DWARF/mydsp_dbg -arch arm64 0xADDRESS
```

> [!important] 第 ② 步必须在第 ③ 步之前
> **先让 sanitizer 把"不崩溃的 bug"抓出来**，
> 剩下的（真崩溃）才用 lldb 深入。

**本库的验证脚本**（见 [[插件验证工具]]）：

```bash
# 音频线程分配检测
clang++ -std=c++17 -O1 -g audio_thread_alloc_detector.cpp mytest.cpp -o t && ./t

# ASan / UBSan
clang++ -std=c++17 -O1 -g -fsanitize=address,undefined \
    -fno-sanitize-recover=all demo.cpp -o demo && ./demo
```

---

## 相关

- [[MOC - Frameworks & Toolchain]]
- [[AddressSanitizer]] — 抓不崩溃的 bug ⭐ 优先于 lldb
- [[UndefinedBehaviorSanitizer]]
- [[ThreadSanitizer 与内存序]] — 多线程问题用 TSan 不用 lldb
- [[插件验证工具]] — 完整的验证手段清单
- [[性能剖析]] — 性能问题用 profiler 不用 lldb
- [[实时音频线程契约]] — 为什么不能在音频线程断点
- [[JUCE 的 CMake API]] — 用 Standalone 目标调试
- [[C++ 零基础到音频 DSP 路线]]

> [!note] 待补充
> - **在真实插件 + 宿主里附加 lldb**（本机无 JUCE/宿主）
> - 崩溃日志（crash report）的符号化流程
> - `lldb` 的 Python 脚本扩展
> - 内存泄漏调试（leaks 工具）
> - 实测：ASan 符号化失败是否只在本沙箱出现
