---
title: macOS 代码签名
type: wiki
domain: craft
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# macOS 代码签名

> [!important] 一句话
> **签名是用你的开发者证书给二进制"盖章"**，证明"这是我发布的，且没被篡改"。
> 它是**公证的前提**——不签名就没法公证，不公证用户就打不开。

> [!note] 本页的命令都是从本机实测的
> `codesign` 在 `/usr/bin/codesign`，是 macOS 自带的。
> 关键选项见下方（实测自 `codesign --help`）。

## 签名 vs 公证

| | 签名（codesign） | 公证（notarytool） |
|---|---|---|
| 做什么 | 本地盖章 | 提交苹果审核 |
| 联网 | ❌ 不需要 | ✅ 需要 |
| 耗时 | 秒级 | 分钟级 |
| 证明 | "我签的、没被改" | "苹果扫过、无恶意代码" |
| 必须吗 | 公证的前提 | Gatekeeper 放行的前提 |

> [!important] 三步流程
> ```
> ① codesign      签名（本地）
> ② notarytool    提交公证（联网，等几分钟）
> ③ stapler       把公证票据钉进包（本地）
> ```
> **漏掉 ③ 的话，用户离线时验证会失败。**
>
> 见 [[macOS 公证 (notarization)]]。

---

## 一、证书类型

| 证书 | 用途 | 需要付费账号 |
|---|---|---|
| **Developer ID Application** | **分发到 App Store 之外**（你要的） | ✅ |
| Apple Development | 本地开发调试 | ✅ |
| Mac App Store | 上架 App Store | ✅ |
| **ad-hoc（`-s -`）** | 只能本机用 | ❌ **不需要** |

> [!tip] 开发阶段用 ad-hoc 就够
> ```bash
> codesign -s - --deep MyPlugin.vst3      # ad-hoc 签名
> ```
> 只有**发布**才需要真证书 + 公证。
>
> ⚠️ 苹果开发者账号的**当前年费**需自行查官方页面（本页不写死）。

---

## 二、核心选项（实测自 `codesign --help`）

```bash
codesign --sign "Developer ID Application: Your Name (TEAMID)" \
         --options runtime \        # 开启 Hardened Runtime（公证必需）
         --timestamp \              # 加可信时间戳
         --deep \                   # 递归签内部所有组件
         --force \                  # 覆盖已有签名
         --verbose \                # 输出细节
         MyPlugin.vst3
```

| 选项 | 作用 | 不加会怎样 |
|---|---|---|
| `--options runtime` | 硬化运行时 | 公证**被拒** |
| `--timestamp` | 可信时间戳 | 证书过期后签名失效 |
| `--deep` | 递归签内部 | 内部组件未签 → 验证失败 |
| `--force` | 覆盖旧签名 | 重复签名报错 |

> [!danger] `--timestamp` 容易被漏
> 不加时间戳时，签名只在**证书有效期内**有效。
> 证书到期（通常 1 年，需续期）后，**所有旧版本的签名都会失效**——
> 用户会突然打不开你的插件。
>
> **加时间戳后，签名永久有效**（时间戳证明了"签名时刻证书有效"）。

---

## 三、签名要签"每一层"

> [!warning] 插件是 **bundle（目录）**，不是单个文件
> ```
> MyPlugin.vst3/
> └── Contents/
>     ├── Info.plist
>     ├── MacOS/MyPlugin           ← ① 可执行文件
>     ├── Frameworks/*.dylib       ← ② 动态库
>     └── Resources/               ← ③ 资源（被 seal 覆盖）
> ```

**两种做法**：

| 做法 | 命令 | 评价 |
|---|---|---|
| **`--deep`** | `codesign --deep ... MyPlugin.vst3` | 简单，但苹果文档曾建议发布时不要依赖它 |
| **从内到外逐层签** | 先签 `.dylib` 和可执行文件，再签整个 bundle | ✅ 更可靠 |

```bash
# 逐层签名（推荐用于发布）
PLUGIN="MyPlugin.vst3"
ID="Developer ID Application: Your Name (TEAMID)"

# ① 先签内部的动态库
find "$PLUGIN/Contents/Frameworks" -name "*.dylib" -exec \
    codesign --sign "$ID" --options runtime --timestamp --force {} \;

# ② 再签可执行文件
codesign --sign "$ID" --options runtime --timestamp --force \
    "$PLUGIN/Contents/MacOS/MyPlugin"

# ③ 最后签整个 bundle
codesign --sign "$ID" --options runtime --timestamp --force "$PLUGIN"
```

---

## 四、验证命令（实测输出）

**本机验证一个正常发布的 App**（Obsidian，作为参照）：

```bash
codesign -v --verbose=2 /Applications/Obsidian.app
#   → /Applications/Obsidian.app: valid on disk
#   → /Applications/Obsidian.app: satisfies its Designated Requirement
```

```bash
codesign -dv --verbose=2 /Applications/Obsidian.app
#   Executable=/Applications/Obsidian.app/Contents/MacOS/Obsidian
#   Identifier=md.obsidian
#   Format=app bundle with Mach-O universal (x86_64 arm64)
#   CodeDirectory v=20500 size=631 flags=0x10000(runtime)    ← runtime = Hardened Runtime
#   Authority=Developer ID Application: Dynalist Inc. (6JSW4SJWN9)
#   Authority=Developer ID Certification Authority
#   Authority=Apple Root CA                                  ← 证书链完整
#   Timestamp=Mar 23, 2026 at 23:22:17                       ← 有时间戳
#   Notarization Ticket=stapled                              ← 已 staple
#   TeamIdentifier=6JSW4SJWN9
```

> [!tip] 这三条命令就是你的发布前检查清单
> ```bash
> codesign -v --verbose=2 MyPlugin.vst3          # ① 签名有效
> xcrun stapler validate MyPlugin.vst3           # ② 公证已钉入
> spctl -a -vv MyPlugin.vst3                     # ③ Gatekeeper 放行
> ```
> 三条全过才算合格（本机实测三条都能通过）。

---

## 五、Hardened Runtime 与 entitlements

**Hardened Runtime** 限制了一些操作，对你的插件可能有影响：

| 被限制的操作 | 症状 | 需要的 entitlement |
|---|---|---|
| JIT 编译 | 崩溃 | `com.apple.security.cs.allow-jit` |
| 加载未签名动态库 | 加载失败 | `com.apple.security.cs.disable-library-validation` |
| 调试器附加 | 无法调试 | `com.apple.security.cs.allow-unsigned-executable-memory` |

```xml
<!-- entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- 只在真的需要时才加！ -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

```bash
codesign --sign "$ID" --options runtime --timestamp \
         --entitlements entitlements.plist MyPlugin.vst3
```

> [!danger] 每个 entitlement 都是安全让步
> **只加真正需要的。**
> 具体需要哪些**必须实测**（本机无插件，无法验证）——
> 见 [[_meta/open-questions]]。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **忘了 `--options runtime`** | 公证被拒 | 检查命令 |
| 2 | **忘了 `--timestamp`** | 证书过期后签名失效 | 检查命令 |
| 3 | **只签了可执行文件** | bundle 未签 → 验证失败 | `codesign -v` 整个 bundle |
| 4 | **把插件当单个文件** | `--deep` 都用错 | VST3/AU 是**目录** |
| 5 | **编造证书价格/政策** | 决策错误 | 查官方页面 |
| 6 | **用 ad-hoc 签名去分发** | 用户打不开 | 发布必须用 Developer ID |
| 7 | **不验证就发布** | 用户才发现问题 | 跑三条验证命令 |
| 8 | **把证书提交进仓库** | 严重安全事故 | grep 仓库 |

> [!danger] 第 3 条很隐蔽
> AI 会写"签一下插件" → `codesign MyPlugin.vst3`。
> 这**看起来**签了整个 bundle，但 `--deep` 不加时，
> 内部的 `.dylib` 可能没被签 → `codesign -v` 会失败。
>
> **判据**：`codesign -v --verbose=2` 必须输出 `valid on disk`。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 公证被拒 | 没开 Hardened Runtime | `--options runtime` |
| 证书过期后打不开 | 没加时间戳 | `--timestamp` |
| 插件加载失败 | Hardened Runtime 限制 | 加对应 entitlement |
| `codesign -v` 失败 | 内部组件未签 | 逐层签，或 `--deep` |
| 重复签名报错 | 已有签名 | 加 `--force` |
| 换了机器签名失效 | 缺时间戳 | 加 `--timestamp` |
| CI 里签名失败 | 证书没导入 keychain | 检查 CI 的 keychain 设置 |

---

## 八、怎么验证

```bash
#!/bin/bash
# 发布前签名验证脚本（本机实测可用）
PLUGIN="$1"
ID="Developer ID Application: Your Name (TEAMID)"

echo "=== ① 签名有效性 ==="
if codesign -v --verbose=2 "$PLUGIN" 2>&1; then
    echo "✅ 签名有效"
else
    echo "❌ 签名无效"; exit 1
fi

echo "=== ② 签名详情 ==="
codesign -dv --verbose=2 "$PLUGIN" 2>&1 | grep -E \
    "Authority|Timestamp|flags|TeamIdentifier"

echo "=== ③ 是否开启 Hardened Runtime ==="
if codesign -dv --verbose=2 "$PLUGIN" 2>&1 | grep -q "flags=.*runtime"; then
    echo "✅ Hardened Runtime 已开启"
else
    echo "❌ 未开启 Hardened Runtime（公证会被拒）"; exit 1
fi

echo "=== ④ 是否有时间戳 ==="
if codesign -dv --verbose=2 "$PLUGIN" 2>&1 | grep -q "Timestamp="; then
    echo "✅ 有时间戳"
else
    echo "❌ 无时间戳（证书过期后签名会失效）"; exit 1
fi
```

---

## 相关

- [[MOC - Craft & Release]]
- [[macOS 公证 (notarization)]] — 签名的下一步
- [[代码签名与公证]] — 两平台的概览
- [[Windows 代码签名]] — Windows 侧
- [[插件安装路径规范]] — 装到哪
- [[插件扫描机制]] — 宿主怎么发现插件

> [!note] 待补充
> - **音频插件需要的 entitlement 清单**（需真实插件实测）
> - 公证被拒的具体错误码与排查
> - CI（GitHub Actions）里的完整签名流程
> - 证书导出/导入 keychain 的详细步骤
