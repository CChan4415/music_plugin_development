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

    # 路径式链接的合法目标（如 [[_meta/roadmap]]、[[50-Playground/tools/tools 说明]]）
    # Obsidian 支持 [[目录/文件]]，只要文件真的存在就不是错误。
    path_keys = {str(rel)[:-3] if str(rel).endswith('.md') else str(rel): rel
                 for rel in docs}

    # ---- 1 & 2: 链接分析 ----
    # 断链是**特性不是 bug**：MOC 里的链接构成待写队列。
    # 所以按「被引用次数」聚合 —— 被引用越多，越该优先写。
    inbound = defaultdict(int)
    missing_refs = defaultdict(set)      # 目标 -> 引用它的文件集合
    for rel, d in docs.items():
        if rel.parts[0] in ('99-Templates',):
            continue                      # 模板里的链接是占位符
        for raw in LINK_RE.findall(strip_code(d['text'])):
            # 表格里的链接要转义竖线：[[_meta/roadmap\|路线图]]
            # 所以要去掉反斜杠，否则目标名会带上 "\"
            target = raw.strip().replace('\\', '')
            if target.endswith('.md'):
                target = target[:-3]
            if '...' in target or target.startswith('10-Sources/'):
                continue                  # 说明性占位符
            # Obsidian 陷阱：链接名里含 "/" 会被当成路径 -> 永远解析不到。
            # 这是**真实错误**，必须报告（不是待写队列）。
            # 路径式链接是**合法的**（Obsidian 支持 [[目录/文件]]），
            # 只要目标文件真的存在。只有**文件名本身**含 / 才是错误。
            if '/' in target:
                if target in path_keys:      # 合法路径链接，且目标存在
                    continue
                problems['链接名含斜杠'].append(
                    f"{rel}  ->  [[{target}]]   （路径不存在，或文件名本身含 /）")
                continue
            target = Path(target).name
            if target in by_stem:
                inbound[target] += 1
            else:
                missing_refs[target].add(str(rel))

    # ---- 2.5: 孤儿页 + 同名冲突 ----
    # Obsidian 按**文件名**识别笔记。所以：
    #   • 同名文件（如 9 个 README.md）→ 链接无法解析 → 显示为孤儿
    #   • 没有任何入链的页面 → 图谱里孤立，等于"写了没人看得到"
    stems_map = defaultdict(list)
    for rel in docs:
        stems_map[rel.stem].append(rel)

    for stem, lst in sorted(stems_map.items()):
        if len(lst) > 1 and stem != 'README':
            problems['同名冲突'].append(
                f"『{stem}』有 {len(lst)} 个文件 —— Obsidian 无法解析 [[{stem}]]：" +
                "、".join(str(x) for x in lst))

    path_keys = {str(rel)[:-3] if str(rel).endswith('.md') else str(rel): rel for rel in docs}
    inbound_ok = set()
    for rel, d in docs.items():
        for raw in LINK_RE.findall(strip_code(d['text'])):
            t = raw.strip()
            if t in path_keys:
                inbound_ok.add(str(path_keys[t]))
            elif t in stems_map and len(stems_map[t]) == 1:
                inbound_ok.add(str(stems_map[t][0]))

    SKIP_ORPHAN = ('99-Templates',)          # 模板通过插件调用，不需要入链
    for rel in docs:
        if rel.parts[0] in SKIP_ORPHAN:
            continue
        if str(rel) not in inbound_ok:
            problems['孤儿页'].append(f"{rel}  （没有任何页面链接到它）")

    # ---- 3: frontmatter ----
    for rel, d in docs.items():
        name = rel.name
        # 转义的 frontmatter 定界符（\---）会让 Obsidian 完全不解析元数据。
        # 这是**真错误**：通常是批量格式化工具误伤。
        if d['text'].lstrip().startswith('\\---'):
            problems['frontmatter 被转义'].append(
                f"{rel}  以 \\--- 开头，Obsidian 不会解析元数据（应为 ---）")
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
    # 契约: 10-Sources/ 下的**原始资料**只增不改。
    # ⚠️ README.md 是目录说明，不是原始资料，修改它是合法的 —— 要排除。
    try:
        # ⚠️ 加 -c core.quotePath=false：否则非 ASCII 文件名会被 git 转义成
        #    "10-Sources/xxx \350\257\264..."，导致后续 git 命令找不到文件
        out = subprocess.run(
            ['git', '-c', 'core.quotePath=false', 'log', '--name-status',
             '--pretty=format:', '--', '10-Sources'],
            cwd=VAULT, capture_output=True, text=True, timeout=10)
        modified = set()
        for line in out.stdout.splitlines():
            parts = line.split('\t')
            if len(parts) >= 2 and parts[0].startswith('M'):
                f = parts[1]
                if not f.endswith('README.md'):
                    modified.add(f)
        for f in sorted(modified):
            # 只检查**创建之后**的修改。git log -p 会把首次提交的每一行
            # 都算作 '+'，所以必须跳过创建那次提交。
            log = subprocess.run(
                ['git', 'log', '--format=%H', '--', f],
                cwd=VAULT, capture_output=True, text=True, timeout=10).stdout.split()
            diff = ""
            if len(log) > 1:
                diff = subprocess.run(
                    ['git', 'log', '-p', f'{log[1]}..HEAD', '--', f],
                    cwd=VAULT, capture_output=True, text=True, timeout=10).stdout
            changed = [l[1:].strip() for l in diff.splitlines()
                       if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
            only_links = bool(changed) and all(
                l.startswith('- [[') or l.startswith('+ [[') for l in changed)
            if only_links:
                print(f"  ℹ️  {f}  仅链接行变更（重命名的连带修改，合法）")
            elif changed:
                problems['Sources 被修改'].append(
                    f"{f}  内容被修改 —— 契约要求 10-Sources/ 只增不改")
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

    order = ['frontmatter 被转义', '链接名含斜杠', '同名冲突', '孤儿页', '缺 frontmatter',
             'frontmatter 字段不全', '非法 type', '日期格式错', '长期未更新',
             'Sources 被修改']
    for key in order:
        items = problems.get(key, [])
        if not items:
            continue
        icon = '⚠️ ' if key in ('Sources 被修改', '链接名含斜杠',
                                   'frontmatter 被转义', '同名冲突') else '·'
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
