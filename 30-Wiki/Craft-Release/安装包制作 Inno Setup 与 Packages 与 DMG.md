---
title: 安装包制作 Inno Setup 与 Packages 与 DMG
type: wiki
domain: craft
status: seed
confidence: medium
sources: []
tags: [recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# 安装包制作 Inno Setup 与 Packages 与 DMG

> [!warning] ⚠️ 本页置信度：medium（部分实测）
> **本机实测的工具状态**：
> | 工具 | 状态 |
> |---|---|
> | `pkgbuild` | ✅ **可用**（实测创建了一个 test.pkg） |
> | `productbuild` | ✅ 存在（取了真实用法） |
> | **`hdiutil`** | ⚠️ **存在但创建被沙箱拒绝**（"操作不被允许"） |
> | `codesign` / `stapler` | ✅ 可用（已在真实 App 上验证） |
> | **Inno Setup** | ❌ Windows 工具，本机无法测 |
>
> **所以：macOS 的 pkg 流程部分实测；DMG 流程和 Windows 流程未实测。**

> [!important] 一句话
> **安装包 = 让用户"双击 → 完成"的东西。**
> 它不只是打包文件，还要**处理权限、签名、公证、卸载**。

## 三种格式，三个平台

| 格式 | 平台 | 工具 | 用户看到 |
|---|---|---|---|
| **DMG** | macOS | `hdiutil` | 挂载一个磁盘镜像，拖拽安装 |
| **PKG** | macOS | `pkgbuild` + `productbuild` | 双击安装向导 |
| **EXE/MSI** | Windows | **Inno Setup** / WiX | 安装向导 |

> [!note] macOS 上怎么选 DMG vs PKG
> | | DMG | PKG |
> |---|---|---|
> | 用户体验 | ✅ 拖拽（Mac 用户习惯） | 🟠 向导（有点"Windows 味"） |
> | 权限处理 | ❌ 需要用户手动授权 | ✅ 可提权到系统目录 |
> | 卸载 | ✅ 用户自己删 | 🟠 需要卸载脚本 |
> | 装到系统目录 | ❌ 用户级 | ✅ **系统级** |
>
> **经验**：
> - 插件装**用户级**目录 → **DMG**（简单、用户熟悉）
> - 需要装**系统级**（`/Library/...`）→ **PKG**（能提权）
>
> 见 [[插件安装路径规范]]。

---

## 一、PKG（✅ 部分实测）

### 实测的用法（`pkgbuild` 三种模式）

```
Usage: pkgbuild [options] --root <root-path> [--component-plist <plist>] <output>
       从目录构建

Usage: pkgbuild --analyze --root <root-path> <plist-output>
       从目录生成 component plist 模板

Usage: pkgbuild [options] {--component <component-path>} <output>
       从**已构建的 bundle** 构建
```

> [!tip] 第三种模式最适合插件
> `--component MyPlugin.vst3` —— 直接从 bundle 构建，
> 不用手工搭目录结构。

### 实测：创建一个最小 PKG

```bash
mkdir -p payload
echo "test" > payload/file.txt

pkgbuild --root payload \
         --identifier com.yourname.myplugin \
         --version 1.0 \
         test.pkg
```

**实测输出**：
```
pkgbuild: Inferring bundle components from contents of payload
pkgbuild: Wrote package to test.pkg
→ ✅ 成功（1.9 KB）
```

**验证**：
```bash
pkgutil --check-signature test.pkg     # → Status: no signature
pkgutil --payload-files test.pkg       # → ./file.txt
```

> [!important] 两个实用命令
> | 命令 | 用途 |
> |---|---|
> | `pkgutil --check-signature` | 检查 pkg 是否已签名 |
> | `pkgutil --payload-files` | 列出 pkg 里有什么（**排查打包错误**） |
>
> `--payload-files` 特别有用：装完后文件去哪了，一目了然。

### 完整的插件 PKG 流程

```bash
# ① 构建 PKG（从 bundle）
pkgbuild --component "MyPlugin.vst3" \
         --install-location "/Library/Audio/Plug-Ins/VST3" \
         --identifier "com.yourname.myplugin.vst3" \
         --version "1.0.0" \
         MyPlugin-vst3.pkg

# ② 合成成"产品"（多组件时用）
productbuild --distribution distribution.xml \
             --package-path . \
             MyPlugin-Installer.pkg

# ③ 签名（见 [[macOS 代码签名]]）
productsign --sign "Developer ID Installer: Your Name (TEAMID)" \
            MyPlugin-Installer.pkg MyPlugin-Signed.pkg

# ④ 公证（见 [[macOS 公证 (notarization)]]）
xcrun notarytool submit MyPlugin-Signed.pkg --keychain-profile "AC_PASSWORD" --wait
xcrun stapler staple MyPlugin-Signed.pkg
```

> [!danger] PKG 需要**另一种**证书
> | 签名对象 | 证书类型 |
> |---|---|
> | app / 插件 bundle | `Developer ID Application` |
> | **PKG 安装包** | **`Developer ID Installer`** |
>
> **两个不同的证书。** 用错了会签名失败。
>
> ⚠️ 具体申请流程需查苹果开发者文档。

> [!note] `productbuild` 的三种模式（实测自帮助文本）
> ```
> --product <plist> --component <bundle> <install-path> <output>
> --content <content-path> <output>
> --root <root-path> <install-path> <output>
> ```
> ⚠️ 完整的 `distribution.xml` 写法需查苹果文档（本页未实测）。

---

## 二、DMG（⚠️ 本机无法实测）

> [!warning] `hdiutil` 在本机被沙箱拒绝
> 实测输出：
> ```
> hdiutil create -size 5m -fs HFS+ -volname "Empty" /tmp/empty.dmg
> → hdiutil: create failed - 操作不被允许
> ```
>
> 所以下面的命令**未在本机验证**。⚠️ 需你在正常环境里实测。

**标准命令**：

```bash
# ① 准备一个目录（放插件 + 说明 + 到 Applications 的符号链接）
mkdir -p dmg-staging
cp -R MyPlugin.vst3 dmg-staging/
ln -s /Library/Audio/Plug-Ins/VST3 dmg-staging/"装到这里"

# ② 创建 DMG
hdiutil create -volname "My Plugin" \
               -srcfolder dmg-staging \
               -ov -format UDZO \
               MyPlugin.dmg

# ③ 签名
codesign --sign "Developer ID Application: ..." MyPlugin.dmg

# ④ 公证 + staple
xcrun notarytool submit MyPlugin.dmg --keychain-profile "AC_PASSWORD" --wait
xcrun stapler staple MyPlugin.dmg

# ⑤ 验证
hdiutil verify MyPlugin.dmg
spctl -a -vv -t install MyPlugin.dmg
```

> [!tip] `-format UDZO` 是压缩格式
> | 格式 | 说明 |
> |---|---|
> | `UDZO` | ✅ 压缩（推荐发布） |
> | `UDBZ` | 更强压缩（更慢） |
> | `UDRO` | 只读未压缩（调试用） |
>
> ⚠️ 公证**要求** DMG 是签名的（`codesign` 那一步不能省）。

> [!warning] 一个常见做法：漂亮的 DMG 窗口
> 商业插件常用"自定义背景图 + 图标位置"的 DMG。
> 这需要用 AppleScript 设置窗口属性，
> 流程更复杂（挂载可写 DMG → 设置 → 转换）。
> ⚠️ 本页不展开（未实测）。

---

## 三、Inno Setup（Windows，⚠️ 完全未实测）

> [!warning] 本机是 macOS，**无法测 Inno Setup**
> 以下内容基于通用知识，**具体语法需你对照 Inno Setup 官方文档**。

**为什么选 Inno Setup**：

| | Inno Setup | WiX | NSIS |
|---|---|---|---|
| 学习曲线 | ✅ **平缓** | ❌ 陡（XML） | 🟠 中（脚本语言） |
| 免费 | ✅ | ✅ | ✅ |
| 脚本格式 | 类 INI | XML | 自定义 |
| 适合 | ✅ **独立开发者** | 企业 | 老项目 |

**基本结构**（⚠️ 语法需核实）：

```ini
[Setup]
AppName=My Plugin
AppVersion=1.0.0
DefaultDirName={commonpf}\Common Files\VST3\MyPlugin.vst3
ArchitecturesInstallIn64BitMode=x64
OutputBaseFilename=MyPlugin-Setup

[Files]
Source: "build\MyPlugin.vst3\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Uninstall My Plugin"; Filename: "{uninstallexe}"
```

> [!danger] ⚠️ 三个必须自行核实的点
> 1. **`DefaultDirName` 的写法**（Windows 的 VST3 标准路径）
> 2. **64 位模式的声明**（`ArchitecturesInstallIn64BitMode`）
> 3. **签名怎么做**（Inno Setup 有 SignTool 集成，但配置需要研究）
>
> 见 [[插件安装路径规范]] 的 Windows 部分。

> [!important] Windows 安装包要装到哪
> ```
> C:\Program Files\Common Files\VST3\     ← 标准位置（64 位）
> ```
> **VST3 有标准位置**（不像 VST2 各家不同）——
> 装对了宿主就能自动找到。
>
> 见 [[插件安装路径规范]] 和 [[插件扫描机制]]。

---

## 四、安装包必须做的事

> [!important] 不只是"复制文件"

| # | 事项 | 为什么 |
|---|---|---|
| 1 | **创建目录**（如果不存在） | 本机实测：`VST3/` 目录**不存在**（没装过 VST3 宿主） |
| 2 | **设置正确权限** | 系统级目录需要管理员权限 |
| 3 | **签名 + 公证**（macOS） | 否则 Gatekeeper 拦截 |
| 4 | **签名**（Windows） | 否则 SmartScreen 警告 |
| 5 | **提供卸载** | 用户期望能干净删除 |
| 6 | **不覆盖用户数据** | 预设、配置要保留 |
| 7 | **检查宿主是否在运行** | 插件文件被占用时替换会失败 |

> [!danger] 第 1 条特别重要（本机实测发现）
> ```
> /Library/Audio/Plug-Ins/VST3/   ← 本机不存在
> /Library/Audio/Plug-Ins/Components/  ← 存在（AU）
> ```
> **macOS 不会预建 VST3 目录。**
> 如果安装包假设它存在，安装会失败。
>
> **安装脚本必须先创建目录。**

> [!warning] 第 7 条容易被忽略
> 用户正开着 DAW 时安装，插件文件可能**被占用**：
> - Windows：文件锁 → 复制失败
> - macOS：能替换但**宿主仍用旧的**（已加载到内存）
>
> **好的安装包会检测并提示用户关闭宿主。**

---

## 五、卸载

| 平台 | 卸载方式 |
|---|---|
| **DMG**（用户级） | 用户自己删（这是优点） |
| **PKG**（系统级） | 需要卸载脚本或第三方工具 |
| **Inno Setup** | ✅ 自动生成卸载程序 |

> [!note] macOS 的 PKG 没有内置卸载
> 这是 macOS 的已知痛点——用户装了系统级 PKG 后**不知道怎么删**。
>
> **建议**：
> 1. 在文档里写明卸载步骤（删哪几个路径）
> 2. 或提供一个卸载脚本
> 3. 或者**优先用 DMG 装到用户级**（避免这个问题）

**残留位置**（卸载要检查）：

| 位置 | 内容 |
|---|---|
| `/Library/Audio/Plug-Ins/{VST3,Components}/` | 插件本体（系统级） |
| `~/Library/Audio/Plug-Ins/...` | 插件本体（用户级） |
| `~/Library/Application Support/<厂商>/` | 预设、配置 |
| `%APPDATA%\<厂商>\`（Windows） | 同上 |
| 宿主的插件缓存 | 需要重新扫描 |

见 [[插件安装路径规范]]。

---

## 六、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **假设 VST3 目录存在** | 安装失败 | 先创建目录 |
| 2 | **用 Application 证书签 PKG** | 签名失败 | PKG 要 **Installer** 证书 |
| 3 | **DMG 不签名就公证** | 公证被拒 | 先 `codesign` |
| 4 | **忘了公证后 staple** | 用户离线打不开 | `stapler staple` |
| 5 | **编造 Inno Setup 语法** | 编译失败 | 查官方文档 |
| 6 | **编造 Windows 路径** | 装错位置 | 用 `Program Files\Common Files\VST3` |
| 7 | **以为装到哪都行** | 宿主找不到 | 必须装标准路径 |
| 8 | **不提供卸载** | 用户骂人 | 提供卸载方式 |
| 9 | **覆盖用户预设** | 数据丢失 | 分开处理预设与程序 |
| 10 | **不检查宿主是否运行** | 文件被占用 | 检测并提示 |

> [!danger] 第 1、2 条是本页最实际的两个坑
> - **目录不存在**：本机实测确认（macOS 不预建 VST3 目录）
> - **证书类型**：`Developer ID Application` 和 `Developer ID Installer`
>   是**两个不同的证书**，用错直接失败
>
> 见 [[macOS 代码签名]]。

---

## 七、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 安装后宿主找不到 | 装错目录 | 用标准路径 |
| 安装失败 | 目标目录不存在 | 安装时创建 |
| PKG 签名失败 | 用了 Application 证书 | 用 Installer 证书 |
| 用户看到"无法验证开发者" | 没公证/staple | 见 [[macOS 公证 (notarization)]] |
| 安装后插件是旧版 | 宿主缓存 | 重新扫描 |
| 用户不知道怎么卸载 | PKG 没有卸载 | 提供文档/脚本 |
| 预设丢了 | 安装覆盖了用户数据 | 分开处理 |
| Windows 上装到 32 位目录 | 路径写错 | 用 `Program Files\Common Files\VST3` |

---

## 八、怎么验证

**本机可用的验证命令**：

```bash
# ① PKG：看里面有什么（✅ 本机实测可用）
pkgutil --payload-files MyPlugin.pkg

# ② PKG：检查签名（✅ 本机实测可用）
pkgutil --check-signature MyPlugin.pkg

# ③ DMG：验证完整性（⚠️ 需能创建 DMG 的环境）
hdiutil verify MyPlugin.dmg

# ④ Gatekeeper 评估（✅ 本机实测可用，需真实签名文件）
spctl -a -vv -t install MyPlugin.pkg

# ⑤ 公证票据（✅ 本机实测可用）
xcrun stapler validate MyPlugin.pkg
```

**最终的验证：找一台干净的机器**

> [!important] 这是唯一可靠的验证
> 你自己的机器装了证书、信任设置、旧版本插件——
> **测不出真实用户的体验**。
>
> **必须在从没装过你东西的机器上测：**
> - [ ] 双击能打开吗
> - [ ] 有警告吗
> - [ ] 装完后宿主能找到插件吗
> - [ ] 卸载干净吗
>
> 见 [[macOS 公证 (notarization)]] 的同类建议。

---

## 相关

- [[MOC - Craft & Release]]
- [[插件安装路径规范]] — 装到哪（本机实测了目录状态）
- [[插件扫描机制]] — 宿主怎么发现插件
- [[macOS 代码签名]] — 签名（含 Installer 证书的区别）
- [[macOS 公证 (notarization)]] — 公证流程
- [[Windows 代码签名]] — Windows 侧（⚠️ 未实测）
- [[代码签名与公证]] — 两平台概览
- [[版本号与更新分发]]

> [!note] 待补充（优先级高）
> - **在正常环境里实测 DMG 创建流程**（本机被沙箱拒绝）
> - **`distribution.xml` 的完整写法**（多组件 PKG）
> - **Inno Setup 的实测脚本**（需 Windows）
> - 漂亮 DMG 窗口的实现（背景图 + 图标位置）
> - `productsign` 的实测
> - 完整的多格式安装包（VST3 + AU + 独立程序）
