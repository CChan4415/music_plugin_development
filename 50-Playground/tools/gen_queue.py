#!/usr/bin/env python3
"""生成 _meta/待写队列.md

队列 = 从断链反推出来的知识缺口：
  某些页面写了 [[某某]] 但目标不存在 → 这就是待写项
  被引用越多 = 越多页面在等它 = 优先级越高

用法:
    python3 50-Playground/tools/gen_queue.py
"""
import pathlib, re
from collections import defaultdict

VAULT = pathlib.Path(__file__).resolve().parents[2]
LINK   = re.compile(r'\[\[([^\]\|#]+)(?:[#\|][^\]]*)?\]\]')
FENCE  = re.compile(r'```.*?```', re.S)
INLINE = re.compile(r'`[^`\n]*`')

def strip_code(t):
    return INLINE.sub('', FENCE.sub('', t))

def find_missing():
    files = {p.stem for p in VAULT.rglob('*.md') if '.git' not in p.parts}
    missing = defaultdict(set)
    for p in VAULT.rglob('*.md'):
        if '.git' in p.parts or p.parts[0] == '99-Templates':
            continue
        for m in LINK.finditer(strip_code(p.read_text(encoding='utf-8', errors='replace'))):
            t = m.group(1).strip().replace('\\', '')
            if '...' in t or t.startswith('10-Sources/'):
                continue
            if '/' in t and not t.startswith('_meta/'):
                continue
            name = pathlib.Path(t).name
            if name not in files:
                missing[name].add(p.relative_to(VAULT).with_suffix('').as_posix())
    return missing

def main():
    missing = find_missing()
    queue = sorted(((len(v), k, sorted(v)) for k, v in missing.items()),
                   key=lambda x: (-x[0], x[1]))
    hot = [(n, k, s) for n, k, s in queue if n >= 2]

    L = []
    A = L.append
    A("---"); A("title: 待写队列"); A("type: meta"); A("domain: meta")
    A("status: solid"); A("confidence: high"); A("sources: []")
    A("tags: [todo]"); A("created: 2026-10-15"); A("updated: 2026-10-15")
    A("---"); A("")
    A("# 待写队列"); A("")
    A("> [!important] 这一页是**生成**的，不要手改")
    A("> 生成命令：`python3 50-Playground/tools/gen_queue.py`")
    A(">")
    A("> **队列不是人工维护的清单，而是从「断链」反推出来的缺口。**")
    A("> 页面里写了 `[[某某]]` 但目标还不存在 → 那就是待写项。")
    A("> **被引用越多 = 越多地方在等它 = 优先级越高。**")
    A("")
    A("## 统计"); A("")
    A("| 项 | 数量 |"); A("|---|---|")
    A(f"| 被 >= 2 个页面引用（**优先写**） | **{len(hot)}** |")
    A(f"| 只被引用 1 次（正常） | {len(queue)-len(hot)} |")
    A(f"| 合计 | {len(queue)} |"); A("")
    A(f"## 优先队列（{len(hot)} 项，按引用数排序）"); A("")
    A("| # | 引用 | 待写页面 | 谁在引用 |"); A("|---|---|---|---|")
    for i, (n, k, srcs) in enumerate(hot, 1):
        src = "、".join(f"[[{s}]]" for s in srcs[:3])
        if len(srcs) > 3:
            src += f" 等 {len(srcs)} 处"
        A(f"| {i} | **{n}** | `{k}` | {src} |")
    A("")
    A("## 只被引用 1 次"); A("")
    A("> 多半是随手一提，不影响优先级。")
    A("")
    for n, k, srcs in queue:
        if n == 1:
            A(f"- `{k}` — 来自 [[{srcs[0]}]]")
    A("")
    A("## 相关"); A("")
    A("- [[_meta/page-inventory]] — 已有页面清单")
    A("- [[_meta/roadmap]] — 路线图")
    A("- [[_meta/open-questions]] — 待核实的疑问")
    A("- [[Home]]"); A("")
    A("> [!note] 待补充")
    A("> 无（生成物）")

    out = VAULT / '_meta' / '待写队列.md'
    out.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f"✅ {out.relative_to(VAULT)}")
    print(f"   优先项 {len(hot)} 个 | 单项 {len(queue)-len(hot)} 个")
    for n, k, _ in hot[:5]:
        print(f"   {n}  {k}")

if __name__ == '__main__':
    main()
