#!/usr/bin/env python3
"""从 30-Wiki/ 的 frontmatter 生成 _meta/不确定清单.md

用法: python3 50-Playground/tools/gen_uncertainty.py
"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
pages = sorted((ROOT / '30-Wiki').rglob('*.md'))

rows = []
for p in pages:
    s = p.read_text(encoding='utf-8')
    m = re.search(r'^confidence:\s*(\w+)', s, re.M)
    c = m.group(1) if m else 'missing'
    if c not in ('low', 'medium'):
        continue
    st = re.search(r'^status:\s*(\w+)', s, re.M)
    dom = re.search(r'^domain:\s*(\w+)', s, re.M)
    todos = re.findall(r'^> - (.+)$', s, re.M)
    rows.append((c, dom.group(1) if dom else '?', p.stem,
                 st.group(1) if st else '?', len(todos)))

rows.sort(key=lambda r: (r[0] != 'low', r[1], r[2]))

L = []
L += ['---', 'title: 不确定清单', 'type: meta', 'domain: craft',
      'status: solid', 'confidence: high', 'sources: []', 'tags: [meta]',
      'created: 2026-10-16', 'updated: 2026-10-16', '---', '']
L += ['# 不确定清单', '']
L += ['> [!important] 这一页的存在本身就是知识库的质量指标',
      '> **诚实地列出「我不知道 / 没验证」的东西**，比假装什么都知道更有价值。',
      '> AGENTS.md §0 的第一原则：知识的价值 = 可溯源 × 可复用 × **可推翻**。', '']
L += [f'**统计**：共 {len(rows)} 个页面标了 medium/low（其余 high）。', '']
L += ['| confidence | domain | 页面 | status | 待补充项 |',
      '|---|---|---|---|---|']
for c, d, n, st, t in rows:
    L.append(f'| `{c}` | {d} | [[{n}]] | {st} | {t} |')

L += ['', '## 全局性的未验证项（跨页）', '',
      '| # | 未验证的东西 | 影响范围 | 为什么没验证 |',
      '|---|---|---|---|',
      '| 1 | **JUCE 相关的一切 API 细节** | 8 个页面 | 本机无 JUCE、无 cmake |',
      '| 2 | **真实插件在宿主里的行为** | 6 个页面 | 本机无 DAW、无插件构建环境 |',
      '| 3 | **Windows 侧的工具链** | 4 个页面 | 本机是 macOS |',
      '| 4 | **x86-64 的 SIMD/FMA 行为** | 2 个页面 | 本机是 arm64 |',
      '| 5 | **DMG 创建流程** | 1 个页面 | hdiutil 被沙箱拒绝 |',
      '| 6 | **听感相关的结论** | 5 个页面 | 无法做主观实验 |',
      '| 7 | **多核竞争下的原子开销** | 1 个页面 | 只测了单线程读 |',
      '| 8 | **各平台 LUFS 标准数值** | 1 个页面 | 会变，需查官方文档 |',
      '', '## 使用建议', '',
      '> [!tip] 读 medium/low 的页面时',
      '> 1. 先看页首的 `> [!warning]` —— 那里写明了哪部分实测、哪部分没测',
      '> 2. 「怎么验证」一节的命令**本机都跑过**（除非明确标注）',
      '> 3. 「AI 会怎么写错」的表格**不依赖未验证的部分**（那些错误是通用规律）',
      '', '## 相关', '',
      '- [[Home]]',
      '- [[_meta/open-questions]] — 开放问题',
      '- [[_meta/page-inventory]] — 页面清单',
      '- [[2026-10-14 测量工具会骗你 —— 十一次踩坑记录]]',
      '', '> [!note] 维护方式',
      '> 这一页由脚本生成，见 `50-Playground/tools/gen_uncertainty.py`。',
      '> 修改 confidence 字段后重新运行即可更新。', '']

out = ROOT / '_meta/不确定清单.md'
out.write_text('\n'.join(L), encoding='utf-8')
print(f'✅ {out.relative_to(ROOT)} 已生成（{len(rows)} 个页面）')
