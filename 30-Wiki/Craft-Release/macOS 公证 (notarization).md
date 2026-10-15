---
title: macOS 公证 (notarization)
type: wiki
domain: craft
status: solid
confidence: high
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# macOS 公证 (notarization)

> [!important] 一句话
> **公证是把签名后的包提交给苹果自动扫描**，通过后苹果给你一张"票据"。
> 有票据才能通过 Gatekeeper——**没有它用户双击只会看到"无法验证开发者"。**

> [!note] 本页的命令都是本机实测的
> `notarytool` 通过 `xcrun` 调用，本机路径：
> `/Library/Developer/CommandLineTools/usr/bin/notarytool`
> 参数列表实测自 `xcrun notarytool submit --help`。

## 为什么要公证

| 不公证 | 公证后 |
|---|---|
| 用户看到 **"无法打开，因为 Apple 无法检查其是否包含恶意软件"** | 正常打开 |
| 需要用户右键→打开，或去系统设置里放行 | 无需任何操作 |
| 大部分用户会**直接放弃** | — |

> [!warning] 你的用户是音乐人，不是开发者
> 看到那个警告他们**不会去查怎么绕过**——会认为你的插件有问题。

---

## 一、三步流程

```
① codesign    签名（本地，秒级）
② notarytool  提交公证（联网，几分钟）
③ stapler     把票据钉进包（本地）
```

> [!danger] 第 ③ 步不能省
> 公证结果存在**苹果服务器**上。`stapler` 把票据**存进你的包**。
>
> 不 staple 时：
> - 用户**联网** → Gatekeeper 会去查服务器（可能延迟）
> - 用户**离线** → **验证失败，打不开**
>
> **必须 staple。**

---

## 二、完整命令（实测自 notarytool 的参数）

### 步骤 1：签名

```bash
codesign --sign "Developer ID Application: Your Name (TEAMID)" \
         --options runtime --timestamp --deep --force \
         MyPlugin.vst3
```

见 [[macOS 代码签名]]。

### 步骤 2：打包成 zip

> [!important] `notarytool` 接受 **zip / dmg / pkg**
> **不能直接提交 `.vst3` 目录**（它是 bundle，不是归档）。

```bash
ditto -c -k --keepParent MyPlugin.vst3 MyPlugin.zip
```

> [!tip] 为什么用 `ditto` 而不是 `zip`
> `ditto` 会**保留 macOS 的扩展属性**（如资源分支、签名元数据）。
> 用 `zip` 可能丢失这些信息 → 公证失败或签名校验失败。

### 步骤 3：提交公证

**实测的 `notarytool submit` 参数**：

| 选项 | 说明 |
|---|---|
| `-k, --key <path>` | App Store Connect API 密钥文件路径 |
| `-d, --key-id <id>` | API Key ID（10+ 位字母数字） |
| `-i, --issuer <uuid>` | Issuer ID（**Team API Key 必需**，Individual 不填） |
| `--apple-id <id>` | 开发者 Apple ID |
| `--password <pw>` | **App 专用密码**（不是账号密码！） |
| `--team-id <id>` | 开发者 Team ID |
| **`-p, --keychain-profile <name>`** | 用 keychain 里存的凭据 ✅ **推荐** |
| `-f, --output-format` | 输出格式（如 json） |

**推荐做法（keychain profile）**：

```bash
# 先存凭据（只需做一次）
xcrun notarytool store-credentials "AC_PASSWORD" \
      --apple-id "you@example.com" \
      --team-id "TEAMID" \
      --password "app-specific-password"
```

```bash
# 之后提交时就不用写密码了
xcrun notarytool submit MyPlugin.zip \
      --keychain-profile "AC_PASSWORD" \
      --wait
```

> [!important] `--wait` 会阻塞直到出结果
> 不加 `--wait` 时立即返回一个 submission id，需要另外查状态。
>
> **脚本里必须加 `--wait`**，否则你不知道成功没有。

**用 API Key（CI 推荐）**：

```bash
xcrun notarytool submit MyPlugin.zip \
      --key "AuthKey_XXXXXX.p8" \
      --key-id "XXXXXXXXXX" \
      --issuer "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" \
      --wait
```

> [!warning] `--issuer` 的坑（实测自帮助文本）
> > "Required for Team API Keys. **Do not provide for Individual API Keys.**"
>
> **Team Key 必须给 `--issuer`；Individual Key 必须不给。**
> 给错了会认证失败。

### 步骤 4：查状态（如果不加 --wait）

```bash
# 提交时记下 id，然后：
xcrun notarytool info <submission-id> --keychain-profile "AC_PASSWORD"
```

### 步骤 5：staple

```bash
xcrun stapler staple MyPlugin.vst3
```

**实测的 `stapler` 用法**：

```
stapler staple [-q] [-v] path      # 取票据并附加
stapler validate [-q] [-v] path    # 验证已有票据
```

> [!note] 支持的格式（实测自帮助文本）
> "UDIF disk images, code-signed executable ..."
>
> ⚠️ **`.vst3` bundle 能否直接 staple 需实测确认**——
> 如果不行，流程是"打包成 dmg/pkg → 公证 → staple 那个归档"。

---

## 三、验证（本机实测命令）

```bash
# ① 签名有效
codesign -v --verbose=2 /Applications/Obsidian.app
#   → valid on disk
#   → satisfies its Designated Requirement

# ② 公证票据已钉入
xcrun stapler validate /Applications/Obsidian.app
#   → Processing: /Applications/Obsidian.app
#   → The validate action worked!

# ③ Gatekeeper 放行
spctl -a -vv /Applications/Obsidian.app
#   → accepted
#   → source=Notarized Developer ID
#   → origin=Developer ID Application: Dynalist Inc. (6JSW4SJWN9)
```

> [!tip] 这三条就是发布前的"公证验收"
> 用本机一个正常发布的 App（Obsidian）实测，三条全过。
> **把路径换成你的插件，三条都通过才算合格。**

---

## 四、常见被拒原因

| # | 原因 | 排查 |
|---|---|---|
| 1 | **没开 Hardened Runtime** | `codesign -dv` 看有没有 `flags=...runtime` |
| 2 | **内部组件未签名** | 逐层验证 `codesign -v` |
| 3 | **包含了不允许的内容** | 看 `notarytool` 返回的详细日志 |
| 4 | **用了 `zip` 而不是 `ditto`** | 换 `ditto -c -k --keepParent` |
| 5 | **证书类型不对** | 必须 Developer ID Application |
| 6 | **缺 timestamp** | 签名时加 `--timestamp` |

> [!tip] 公证失败一定要**看日志**
> ```bash
> xcrun notarytool log <submission-id> --keychain-profile "AC_PASSWORD"
> ```
> 返回的 JSON 里有**具体是哪个文件、哪个问题**。
> 不看日志基本等于瞎猜。

---

## 五、CI 里怎么做（GitHub Actions）

```yaml
- name: Import certificate
  env:
    CERT_BASE64: ${{ secrets.MACOS_CERT_P12_BASE64 }}
    CERT_PASSWORD: ${{ secrets.MACOS_CERT_PASSWORD }}
  run: |
    echo "$CERT_BASE64" | base64 --decode > cert.p12
    security create-keychain -p "" build.keychain
    security default-keychain -s build.keychain
    security unlock-keychain -p "" build.keychain
    security import cert.p12 -k build.keychain -P "$CERT_PASSWORD" \
        -T /usr/bin/codesign
    security set-key-partition-list -S apple-tool:,apple: -s -k "" build.keychain

- name: Sign
  run: codesign --sign "${{ secrets.MACOS_SIGN_IDENTITY }}" \
        --options runtime --timestamp --deep --force MyPlugin.vst3

- name: Notarize
  run: |
    ditto -c -k --keepParent MyPlugin.vst3 MyPlugin.zip
    xcrun notarytool submit MyPlugin.zip \
        --key "${{ secrets.AC_KEY_PATH }}" \
        --key-id "${{ secrets.AC_KEY_ID }}" \
        --issuer "${{ secrets.AC_ISSUER }}" \
        --wait

- name: Staple
  run: xcrun stapler staple MyPlugin.vst3

- name: Verify
  run: |
    codesign -v --verbose=2 MyPlugin.vst3
    xcrun stapler validate MyPlugin.vst3
    spctl -a -vv MyPlugin.vst3
```

> [!danger] CI 里的三个安全要点
> 1. **证书用 base64 存 secrets**，不要提交进仓库
> 2. **用 API Key 而不是 Apple ID 密码**（可随时吊销）
> 3. **每次构建后删除临时 keychain**
>
> ⚠️ 上面的 workflow 是**示意**，具体写法需按你的项目调整（未实测）。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **忘了 stapler** | 用户离线时打不开 | `stapler validate` |
| 2 | **直接提交 `.vst3` 目录** | 公证工具报错 | 先 `ditto` 打包 |
| 3 | **用 `zip` 而非 `ditto`** | 丢失元数据 → 失败 | 用 `ditto -c -k --keepParent` |
| 4 | **忘了 `--wait`** | 不知道成功没有 | 检查命令 |
| 5 | **Team Key 给了 `--issuer`，Individual 也给了** | 认证失败 | 见第二节警告 |
| 6 | **用账号密码而非 app 专用密码** | 认证失败 | 生成 app-specific password |
| 7 | **编造公证费用/政策** | 决策错误 | 查官方页面 |
| 8 | **不签名直接公证** | 必然失败 | 先 `codesign` |
| 9 | **公证失败不看日志** | 瞎猜原因 | `notarytool log` |

> [!danger] 第 5 条是实测发现的坑
> `notarytool` 帮助文本明确写了：
> - **Team API Key** → 必须提供 `--issuer`
> - **Individual API Key** → **不要**提供 `--issuer`
>
> AI 通常不知道这个区别，会一律加上或一律不加。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 用户看到"无法验证开发者" | 没公证或没 staple | 走完三步 |
| 公证通过但 Gatekeeper 仍拦 | 没 staple | `xcrun stapler staple` |
| `notarytool` 报认证失败 | 凭据类型不对 | 检查 issuer 规则 |
| 公证被拒 | Hardened Runtime 没开 | `--options runtime` |
| 提交报"不支持的格式" | 提交了 bundle 目录 | 用 `ditto` 打包成 zip |
| staple 失败 | 格式不支持或未公证 | 先确认公证成功 |
| CI 里签名失败 | keychain 未配置好 | 见第五节 |

---

## 八、怎么验证

```bash
#!/bin/bash
# 公证验收脚本（本机实测通过）
PLUGIN="$1"

echo "=== ① 签名有效性 ==="
codesign -v --verbose=2 "$PLUGIN" 2>&1 || { echo "❌ 签名无效"; exit 1; }
echo "✅ 签名有效"

echo "=== ② 公证票据 ==="
if xcrun stapler validate "$PLUGIN" 2>&1 | grep -q "worked"; then
    echo "✅ 票据已钉入"
else
    echo "❌ 无票据（用户离线时打不开）"; exit 1
fi

echo "=== ③ Gatekeeper ==="
if spctl -a -vv "$PLUGIN" 2>&1 | grep -q "accepted"; then
    echo "✅ Gatekeeper 放行"
    spctl -a -vv "$PLUGIN" 2>&1 | grep -E "source|origin"
else
    echo "❌ Gatekeeper 拦截"; exit 1
fi

echo ""
echo "🎉 公证验收通过"
```

> [!tip] 最终测试：找一台**干净的 Mac**
> 你自己的机器装了证书和信任设置，**测不出真实用户的体验**。
> 理想情况是在一台**从没装过你开发环境**的 Mac 上测。

---

## 相关

- [[MOC - Craft & Release]]
- [[macOS 代码签名]] — 公证的前提
- [[代码签名与公证]] — 两平台概览
- [[Windows 代码签名]] — Windows 侧
- [[插件安装路径规范]]
- [[插件扫描机制]]

> [!note] 待补充
> - **`.vst3` bundle 能否直接 staple**（需真实插件实测）
> - GitHub Actions 的完整可运行 workflow
> - 公证被拒的具体 error code 与对应解法
> - dmg / pkg 的制作与公证流程
> - 是否需要对 VST3/AU 分别公证（还是公证安装包即可）
