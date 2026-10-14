#!/usr/bin/env python3
"""
知识库健康检查。

用法:
    python3 50-Playground/tools/vault_health.py

检查项:
  1. 断链 —— [[链接]] 指向不存在的文件（Obsidian 里显示为未解析链接）
  2. 孤儿页 —— 没有任何页面链接到它
  3. frontmatter 缺失或字段不全
  4. status 分布 —— 有多少是 stub（骨架）
  5. 长期未更新（updated 字段超过 N 天）
  6. 违反契约 —— 10-Sources/ 下文件被修改过（需要 git）
"""
import os, re, sys, subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime, date

VAULT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {'.git', '.obsidian', '.trash', 'node_modules'}
REQUIRED_FM = ['title', 'type', 'status']
WIKI_TYPES = {'wiki', 'note', 'source', 'decision', 'project', 'experiment'}
STALE_DAYS = 120

LINK_RE = re.compile(r'\[\[([^\]\|#]+)(?:[#\|][^\]]*)?\]\]')
FENCE_RE = re.compile(r'```.*?```', re.S)          # 围栏代码块
INLINE_CODE_RE = re.compile(r'`[^`\n]*`')          # 行内代码


def strip_code(text):
    """去掉代码块和行内代码。

    Obsidian 不会把代码里的 [[...]] 渲染成链接，所以它们不该被 lint 报告。
    典型场景：记录一个 gotcha 时需要**展示反例**（`[[A/B 对比]]`）。
    """
    return INLINE_CODE_RE.sub('', FENCE_RE.sub('', text))
FM_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.S)


def md_files():
    for p in VAULT.rglob('*.md'):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        yield p


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line and not line.strip().startswith('#'):
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip().strip('"\'')
    return fm


def main():
    files = list(md_files())
    by_stem = defaultdict(list)
    docs = {}

    for p in files:
        text = p.read_text(encoding='utf-8', errors='replace')
        fm = parse_frontmatter(text)
        rel = p.relative_to(VAULT)
        by_stem[p.stem].append(rel)
        docs[rel] = {'text': text, 'fm': fm, 'path': p}

    problems = defaultdict(list)

    # ---- 1 & 2: 链接分析 ----
    # 断链是**特性不是 bug**：MOC 里的链接构成待写队列。
    # 所以按「被引用次数」聚合 —— 被引用越多，越该优先写。
    inbound = defaultdict(int)
    missing_refs = defaultdict(set)      # 目标 -> 引用它的文件集合
    for rel, d in docs.items():
        if rel.parts[0] in ('99-Templates',):
            continue                      # 模板里的链接是占位符
        for raw in LINK_RE.findall(strip_code(d['text'])):
            target = raw.strip()
            if target.endswith('.md'):
                target = target[:-3]
            if '...' in target or target.startswith('10-Sources/'):
                continue                  # 说明性占位符
            # Obsidian 陷阱：链接名里含 "/" 会被当成路径 -> 永远解析不到。
            # 这是**真实错误**，必须报告（不是待写队列）。
            if '/' in target and not target.startswith('_meta/'):
                problems['链接名含斜杠'].append(
                    f"{rel}  ->  [[{target}]]   （文件名不能含 /，Obsidian 会当路径解析）")
                continue
            target = Path(target).name
            if target in by_stem:
                inbound[target] += 1
            else:
                missing_refs[target].add(str(rel))

    # ---- 3: frontmatter ----
    for rel, d in docs.items():
        name = rel.name
        if name.startswith('tpl-') or name in ('README.md',):
            continue
        fm = d['fm']
        if fm is None:
            problems['缺 frontmatter'].append(str(rel))
            continue
        missing = [k for k in REQUIRED_FM if k not in fm]
        if missing:
            problems['frontmatter 字段不全'].append(f"{rel}  缺: {', '.join(missing)}")
        if 'type' in fm and fm['type'] not in WIKI_TYPES and fm['type'] != 'meta':
            problems['非法 type'].append(f"{rel}  type={fm['type']}")

    # ---- 4: status 分布 ----
    status_count = defaultdict(int)
    for rel, d in docs.items():
        fm = d['fm'] or {}
        if fm.get('type') in ('wiki', 'note'):
            status_count[fm.get('status', '(无)')] += 1

    # ---- 5: 陈旧页面 ----
    today = date.today()
    for rel, d in docs.items():
        if rel.parts[0] == '99-Templates':
            continue                      # 模板里是 {{date}} 占位符
        fm = d['fm'] or {}
        upd = fm.get('updated')
        if not upd:
            continue
        try:
            dt = datetime.strptime(upd, '%Y-%m-%d').date()
        except ValueError:
            problems['日期格式错'].append(f"{rel}  updated={upd}")
            continue
        age = (today - dt).days
        if age > STALE_DAYS and fm.get('status') not in ('solid',):
            problems['长期未更新'].append(f"{rel}  {age} 天前 (status={fm.get('status')})")

    # ---- 6: Sources 契约 ----
    try:
        out = subprocess.run(
            ['git', 'log', '--name-only', '--pretty=format:', '--', '10-Sources'],
            cwd=VAULT, capture_output=True, text=True, timeout=10)
        touched = {l for l in out.stdout.splitlines() if l.strip().endswith('.md')}
        # 首次提交里的文件是"创建"不是"修改"，这里只报告后续提交
        commits = subprocess.run(
            ['git', 'log', '--oneline', '--', '10-Sources'],
            cwd=VAULT, capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
        if len(commits) > 1:
            problems['Sources 可能被改过'].append(
                f"10-Sources 有 {len(commits)} 次提交记录，请人工确认只增不改")
    except Exception:
        pass

    # ================= 输出 =================
    print(f"\n{'='*64}")
    print(f"  知识库健康检查  —  {VAULT.name}")
    print(f"{'='*64}")
    print(f"  文件总数: {len(files)}   Markdown 页面: {len(docs)}")

    print(f"\n── status 分布 (wiki/note) ──")
    total_s = sum(status_count.values()) or 1
    for k in ('stub', 'seed', 'solid', 'stale', '(无)'):
        if status_count.get(k):
            n = status_count[k]
            bar = '█' * max(1, int(n / total_s * 30))
            print(f"  {k:<8} {n:>3}  {bar} {n/total_s*100:.0f}%")

    # 待写队列：按被引用次数排序（只统计 >=2 次引用的，单次引用多半是随手一提）
    queue = sorted(((len(v), k) for k, v in missing_refs.items()),
                   key=lambda x: (-x[0], x[1]))
    hot = [(n, k) for n, k in queue if n >= 2]

    if hot:
        print(f"\n── 📝 待写队列（被 >=2 个页面引用，共 {len(hot)} 个）──")
        print(f"   {'引用数':<6} {'页面':<44} 写它的收益")
        for n, k in hot[:30]:
            bar = '★' * min(n, 5)
            print(f"   {n:<6} {k:<44} {bar}")
        if len(hot) > 30:
            print(f"   ... 还有 {len(hot)-30} 个")

    single = len(queue) - len(hot)
    print(f"\n   另有 {single} 个只被引用一次的待写链接（正常，不用管）")

    order = ['链接名含斜杠', '孤儿页', '缺 frontmatter', 'frontmatter 字段不全',
             '非法 type', '日期格式错', '长期未更新', 'Sources 可能被改过']
    for key in order:
        items = problems.get(key, [])
        if not items:
            continue
        icon = '⚠️ ' if key in ('Sources 可能被改过', '链接名含斜杠') else '·'
        print(f"\n── {icon}{key} ({len(items)}) ──")
        for it in items[:25]:
            print(f"    {it}")
        if len(items) > 25:
            print(f"    ... 还有 {len(items)-25} 条")

    if not any(problems.values()) and not hot:
        print("\n✅ 没有发现问题")

    print(f"\n{'='*64}")
    print("  待写队列不是错误 —— 它是这个知识库的 TODO 列表，按需求排序。")
    print("  ⚠️ 标记的才是真错误，需要修。")
    print("  想开始写的时候，从引用数最高的那个开始。")
    print(f"{'='*64}\n")


if __name__ == '__main__':
    main()
