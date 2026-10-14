#!/bin/bash
# 环境检查 —— 在开始之前跑一遍，知道你有什么、缺什么。
# 用法: bash check_env.sh

echo "════════════════════════════════════════════════════"
echo "  音乐插件开发环境检查"
echo "════════════════════════════════════════════════════"
echo ""

ok()   { printf "  ✅ %-28s %s\n" "$1" "$2"; }
miss() { printf "  ❌ %-28s %s\n" "$1" "$2"; }
warn() { printf "  ⚠️  %-28s %s\n" "$1" "$2"; }

echo "── 阶段 1 需要（Python DSP）──"
# 提示：DSH 内置的 python 已有 numpy，但你可能想用自己的环境
DSH_PY="/Users/cc/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3"
if [ -x "$DSH_PY" ] && "$DSH_PY" -c "import numpy" 2>/dev/null; then
  echo "  💡 DSH 内置 Python 已有 numpy:"
  printf "     %s\n" "$DSH_PY"
  echo "     可以直接用它跑实验，无需 pip install"
  echo ""
fi
if command -v python3 >/dev/null; then
  ok "python3" "$(python3 --version 2>&1 | cut -d' ' -f2)"
  for m in numpy matplotlib scipy; do
    if python3 -c "import $m" 2>/dev/null; then
      ok "  $m" "$(python3 -c "import $m;print(getattr($m,'__version__','?'))" 2>/dev/null)"
    else
      miss "  $m" "pip install $m"
    fi
  done
else
  miss "python3" "需要安装 Python"
fi
if command -v afplay >/dev/null; then ok "afplay（播放）" "macOS 自带"; else warn "afplay" "无法自动播放"; fi

echo ""
echo "── 阶段 2-3 需要（C++）──"
if command -v clang++ >/dev/null; then
  ok "clang++" "$(clang++ --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
else
  miss "clang++" "xcode-select --install"
fi
if xcode-select -p >/dev/null 2>&1; then
  ok "Xcode CLT" "$(xcode-select -p)"
else
  miss "Xcode CLT" "xcode-select --install"
fi

echo ""
echo "── 阶段 4 需要（JUCE 插件）──"
if command -v cmake >/dev/null; then
  ok "cmake" "$(cmake --version | head -1 | cut -d' ' -f3)"
else
  miss "cmake" "brew install cmake   ← 阶段 4 才需要，现在不用装"
fi
if command -v git >/dev/null; then ok "git" "$(git --version | cut -d' ' -f3)"; else miss "git" "xcode-select --install"; fi

echo ""
echo "── 测试插件需要（DAW）──"
found_daw=0
for app in "Ableton Live" "Logic Pro" "REAPER" "Bitwig Studio" "FL Studio" "Studio One" "Cubase" "GarageBand"; do
  if [ -d "/Applications/$app.app" ]; then ok "$app" "已安装"; found_daw=1; fi
done
if [ $found_daw -eq 0 ]; then
  miss "DAW" "装 REAPER（推荐）或用 GarageBand"
fi
for d in "/Library/Audio/Plug-Ins/VST3" "/Library/Audio/Plug-Ins/Components"; do
  if [ -d "$d" ]; then
    n=$(ls "$d" 2>/dev/null | wc -l | tr -d ' ')
    printf "  ·  %-28s %s 个插件\n" "$(basename "$d")" "$n"
  fi
done

echo ""
echo "════════════════════════════════════════════════════"
echo "  结论"
echo "════════════════════════════════════════════════════"
cat <<'MSG'
  阶段 1（Python DSP）：只需要 numpy。缺就 pip install numpy matplotlib
  阶段 2-3（C++）：    需要 Xcode CLT
  阶段 4（JUCE）：     需要 cmake（现在不用装）
  测试插件：           需要一个支持插件的 DAW（GarageBand 或 REAPER）

  → 现在只要 numpy 就够了。别提前装 cmake 和 JUCE。
MSG
