#!/bin/bash
# 跨平台自检 —— 在 macOS 上找出"到 Windows/Linux 会炸"的代码。
#
# 用法: bash check_crossplatform.sh [源码目录]
#
# 为什么需要它: macOS 文件系统大小写不敏感，很多跨平台 bug 在本地**永远不会暴露**。
# 这个脚本把你本地看不见的问题找出来。

SRC="${1:-.}"
FOUND=0

echo "════════════════════════════════════════════════════"
echo "  跨平台自检: $SRC"
echo "════════════════════════════════════════════════════"

# ---- 1. 文件名大小写冲突（最致命）----
echo ""
echo "── 1. 只差大小写的重名文件（Linux 上会冲突）──"
# ⚠️ 为什么查 git index 而不是文件系统:
#    macOS 文件系统大小写不敏感 —— 你**根本无法在磁盘上创建** Filter.h 和 filter.h 两个文件。
#    但 **git 可以同时跟踪它们**（git 是大小写敏感的），
#    于是这个冲突会顺利进入仓库，然后在 Linux/CI 上炸掉。
#    → 所以必须查 git，不能查磁盘。
CONFLICT=""
if git -C "$SRC" rev-parse --git-dir >/dev/null 2>&1; then
  CONFLICT=$(git -C "$SRC" ls-files \
    | python3 -c "
import sys, os, collections
d = collections.defaultdict(list)
for line in sys.stdin:
    p = line.rstrip('\n')
    if not p: continue
    d[(os.path.dirname(p).lower(), os.path.basename(p).lower())].append(p)
for k, v in sorted(d.items()):
    if len(v) > 1:
        for x in v: print('  ⚠️  ' + x)
")
  NOTE="（来源: git index —— 磁盘上看不出来）"
else
  # 非 git 仓库时退回到文件系统扫描（能力有限，macOS 上抓不到）
  CONFLICT=$(find "$SRC" -type f \( -name '*.h' -o -name '*.hpp' -o -name '*.cpp' -o -name '*.c' \) \
    -not -path '*/build/*' -not -path '*/.git/*' 2>/dev/null \
    | python3 -c "
import sys, os, collections
d = collections.defaultdict(list)
for line in sys.stdin:
    p = line.rstrip('\n')
    if not p: continue
    d[(os.path.dirname(p).lower(), os.path.basename(p).lower())].append(p)
for k, v in sorted(d.items()):
    if len(v) > 1:
        for x in v: print('  ⚠️  ' + x)
")
  NOTE="（非 git 仓库，只能扫磁盘；macOS 上可能漏报）"
fi
if [ -n "$CONFLICT" ]; then
  echo "$CONFLICT"
  echo "      $NOTE"
  echo "      → Linux/CI 上这两个文件会冲突，必须重命名其中一个"
  FOUND=1
else
  echo "  ✅ 无"
fi

# ---- 2. #include 大小写不匹配 ----
echo ""
echo "── 2. #include 的文件名与实际大小写不符 ──"
# ⚠️ 关键: 不能用 [ -f "myfilter.h" ] 来判断 ——
#    macOS 文件系统大小写不敏感，这个测试**永远返回真**，正是我们要抓的 bug。
#    必须比较**字符串**，不能依赖文件系统。
MISMATCH=0
python3 - "$SRC" <<'PYEOF'
import sys, os, re
src = sys.argv[1]
# 收集所有头文件：{小写名: [实际名...]} 按目录分组
actual = {}
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d not in ('build', '.git', 'node_modules')]
    for f in files:
        if f.endswith(('.h', '.hpp')):
            actual.setdefault(root, {})[f] = True

bad = 0
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d not in ('build', '.git', 'node_modules')]
    for f in files:
        if not f.endswith(('.cpp', '.h', '.hpp', '.cc', '.c')):
            continue
        path = os.path.join(root, f)
        try:
            txt = open(path, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        for m in re.finditer(r'#include\s*"([^"]+)"', txt):
            inc = m.group(1)
            base = os.path.basename(inc)
            # 候选目录：当前文件所在目录（+ 可选的相对路径）
            cand_dir = os.path.normpath(os.path.join(root, os.path.dirname(inc))) if '/' in inc else root
            here = actual.get(cand_dir, {})
            if base in here:
                continue                       # 精确匹配 ✅
            # 找同目录下只差大小写的
            lower = {k.lower(): k for k in here}
            if base.lower() in lower:
                real = lower[base.lower()]
                line = txt[:m.start()].count('\n') + 1
                print(f"  ⚠️  {os.path.relpath(path, src)}:{line}: include \"{inc}\"  →  实际文件是 {real}")
                bad += 1
if bad == 0:
    print("  ✅ 无")
PYEOF
# ---- 3. long 类型（Windows 上是 4 字节）----
echo ""
echo "── 3. 使用了 long（Windows 上宽度不同）──"
LONG=$(grep -rn '\blong\b' "$SRC" --include='*.h' --include='*.hpp' --include='*.cpp' 2>/dev/null \
  | grep -v '/build/' | grep -v 'long long' | grep -v 'long double' | grep -v '//' | head -8)
if [ -n "$LONG" ]; then
  echo "$LONG" | sed 's/^/  ⚠️  /'
  echo "      → 改用 int32_t / int64_t / size_t"
  FOUND=1
else
  echo "  ✅ 无"
fi

# ---- 4. 平台相关 API 散落在业务代码 ----
echo ""
echo "── 4. 平台相关 API / 宏 ──"
PLAT=$(grep -rn '_WIN32\|__APPLE__\|windows\.h\|pthread\.h\|CoreFoundation\|__linux__' \
  "$SRC" --include='*.h' --include='*.hpp' --include='*.cpp' 2>/dev/null \
  | grep -v '/build/' | head -10)
if [ -n "$PLAT" ]; then
  echo "$PLAT" | sed 's/^/  ·  /'
  echo "      → 可以接受，但应该集中在极少数封装文件里"
else
  echo "  ✅ 无（很好）"
fi

# ---- 5. 手拼路径 ----
echo ""
echo "── 5. 手拼路径字符串 ──"
PATHS=$(grep -rnE '"\s*/\s*"|"/"|"\\\\\\\\"' "$SRC" --include='*.h' --include='*.cpp' 2>/dev/null \
  | grep -v '/build/' | grep -viE 'include|//|https?:' | head -6)
if [ -n "$PATHS" ]; then
  echo "$PATHS" | sed 's/^/  ⚠️  /'
  echo "      → 用 juce::File 或 std::filesystem::path"
  FOUND=1
else
  echo "  ✅ 无"
fi

# ---- 6. M_PI ----
echo ""
echo "── 6. 使用 M_PI（MSVC 默认不定义）──"
MPI=$(grep -rn 'M_PI' "$SRC" --include='*.h' --include='*.cpp' 2>/dev/null | grep -v '/build/' | head -5)
if [ -n "$MPI" ]; then
  echo "$MPI" | sed 's/^/  ⚠️  /'
  echo "      → 自己定义 constexpr double kPi，或加 _USE_MATH_DEFINES"
  FOUND=1
else
  echo "  ✅ 无"
fi

echo ""
echo "════════════════════════════════════════════════════"
if [ $FOUND -eq 0 ]; then
  echo "  ✅ 未发现跨平台问题"
else
  echo "  ⚠️  发现问题，见上。这些在 macOS 上大多不会报错。"
fi
echo "════════════════════════════════════════════════════"
echo ""
echo "  提示: 最可靠的验证是让 CI 在 Linux 上编译（ext4 大小写敏感）。"
echo "        见 30-Wiki/Frameworks-Toolchain/跨平台开发 macOS 与 Windows.md"
