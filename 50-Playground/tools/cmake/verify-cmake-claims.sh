#!/usr/bin/env bash
# 验证 CMake 相关页面的技术断言（本库 2026-10-16 实测）
# 用法: bash 50-Playground/tools/cmake/verify-cmake-claims.sh
set -u

# 自动找到 cmake：
#   ① 环境变量 $CMAKE
#   ② 本库的 .venv-tools（pip 装的）
#   ③ PATH 里的 cmake
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
if [ -n "${CMAKE:-}" ]; then
    :
elif [ -x "$ROOT/.venv-tools/bin/cmake" ]; then
    CMAKE="$ROOT/.venv-tools/bin/cmake"
    export PATH="$ROOT/.venv-tools/bin:$PATH"   # 让 ctest/ninja 也可用
elif command -v cmake >/dev/null 2>&1; then
    CMAKE=$(command -v cmake)
else
    echo "❌ 找不到 cmake。安装方式：" >&2
    echo "   python3 -m venv .venv-tools && .venv-tools/bin/pip install cmake ninja" >&2
    exit 1
fi
echo "════ CMake 断言验证 ════"
echo "cmake: $($CMAKE --version | head -1)"
echo ""
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; cd "$T"

echo "① cmake_minimum_required 的版本接受范围"
for v in 3.0 3.5 3.10 3.22 3.30; do
  printf 'cmake_minimum_required(VERSION %s)\nproject(T LANGUAGES CXX)\n' "$v" > CMakeLists.txt
  rm -rf b
  out=$($CMAKE -B b -G Ninja 2>&1)
  if echo "$out" | grep -q 'Configuring done'; then
    if echo "$out" | grep -qi 'deprecated'; then
      printf "   VERSION %-5s ⚠️ 通过但有弃用警告\n" "$v"
    else
      printf "   VERSION %-5s ✅ 通过\n" "$v"
    fi
  else
    printf "   VERSION %-5s ❌ 失败（已被移除）\n" "$v"
  fi
done

echo ""
echo "② CMAKE_CXX_EXTENSIONS 的默认值"
cat > m.cpp <<'CPP'
#include <cstdio>
int main(){
#ifdef __STRICT_ANSI__
    printf("c++17 (严格)\n");
#else
    printf("gnu++17 (有扩展)\n");
#endif
    return 0; }
CPP
for mode in default off; do
  if [ "$mode" = off ]; then extra="set(CMAKE_CXX_EXTENSIONS OFF)"; else extra=""; fi
  printf 'cmake_minimum_required(VERSION 3.22)\nproject(T LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 17)\n%s\nadd_executable(t m.cpp)\n' "$extra" > CMakeLists.txt
  rm -rf "b_$mode"
  $CMAKE -B "b_$mode" -G Ninja >/dev/null 2>&1
  std=$($CMAKE --build "b_$mode" --verbose 2>&1 | grep -o '\-std=[a-z+0-9]*' | head -1)
  printf "   %-8s → %-10s %s\n" "$mode" "${std:-（未显式指定）}" "$(./b_$mode/t 2>/dev/null)"
done

echo ""
echo "③ ctest 的退出码（含管道陷阱）"
printf 'cmake_minimum_required(VERSION 3.22)\nproject(T LANGUAGES CXX)\nadd_executable(ft f.cpp)\nenable_testing()\nadd_test(NAME failing COMMAND ft)\n' > CMakeLists.txt
echo 'int main(){return 1;}' > f.cpp
rm -rf b3; $CMAKE -B b3 -G Ninja >/dev/null 2>&1; $CMAKE --build b3 >/dev/null 2>&1
cd b3
ctest >/dev/null 2>&1; printf "   直接 ctest         → 退出码 %s\n" "$?"
(ctest 2>&1 | tail -1 >/dev/null); printf "   ctest | tail       → 退出码 %s（⚠️ 掩盖失败）\n" "$?"
(set -o pipefail; ctest 2>&1 | tail -1 >/dev/null 2>&1); printf "   pipefail + ctest   → 退出码 %s（✅ 正确）\n" "$?"
