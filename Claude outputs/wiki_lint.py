# -*- coding: utf-8 -*-
"""
wiki_lint.py v1.2 (2026-09-29; v1.1: 중복본 판정에 레지스트리 규칙 2 적용, v1.2: _Inbox·_templates 제외(AGENTS.md v1.16 6.3))
목적: AGENTS.md 6.6절 lint 항목 가운데 기계적으로 점검할 수 있는 것을 한 번에 점검한다.
입력: 자료창고 루트(기본값: 이 파일의 상위 폴더), SOURCE_REGISTRY.yaml, 0 wiki/**/*.md (@clippings·@Inbox·@templates 제외, 옛 이름도 제외)
출력: 표준출력에 JSON(점검 항목별 결과). 파일을 고치지 않는다(읽기 전용).
검증값: 2026-09-22 lint 보고 당시 기준(조문 60개 verified_at 공란)과 현재 조문 페이지 수를 함께 출력해 대조한다.
"""
import os, re, sys, json, glob, yaml
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, '0 wiki')
LIT = '위원회 관련 소송 현황'
reg = yaml.safe_load(open(os.path.join(ROOT, 'SOURCE_REGISTRY.yaml'), encoding='utf-8'))
items = next(v for v in reg.values() if isinstance(v, list))
noncanon = [i['path'] for i in items if i.get('canonical') is False]
internal_src = [i['path'] for i in items if i.get('classification') == 'internal']

pages = {}
for p in glob.glob(os.path.join(W, '**', '*.md'), recursive=True):
    rel = os.path.relpath(p, W)
    if rel.startswith(('@clippings', '@Inbox', '@templates', '_clippings', 'Clippings', '_Inbox', '_templates', '.')):
        continue
    txt = open(p, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', txt, re.S)
    fm, body, err = {}, txt, None
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception as e:
            err = str(e)
        body = m.group(2)
    else:
        err = 'no frontmatter'
    name = os.path.basename(rel)[:-3]
    pages[rel] = dict(name=name, fm=fm, body=body, err=err, full=txt)

names = {v['name']: k for k, v in pages.items()}
mgmt = {'index', 'log', '_index'}
R = {}
R['yaml_error'] = {k: v['err'] for k, v in pages.items() if v['err']}
R['stray_root_files'] = [k for k in pages if os.sep not in k and k not in ('index.md', 'log.md')] + \
    [k for k in pages if k.split(os.sep)[0] not in ('문서', '조문', '쟁점', '사례', '분석') and os.sep in k]

# links
link_re = re.compile(r'\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]')
out, inn, broken = {}, {}, {}
for k, v in pages.items():
    if v['err'] == 'no frontmatter': continue
    ls = set(l.strip() for l in link_re.findall(v['body']))
    out[k] = ls
    for l in ls:
        base = l.split('/')[-1]
        if l in names or base in names or l.endswith('_index') or l in ('index', 'log'):
            tgt = names.get(l) or names.get(base)
            if tgt: inn.setdefault(tgt, set()).add(k)
        else:
            broken.setdefault(l, []).append(k)
todo = set(link_re.findall(open(os.path.join(W, 'index.md'), encoding='utf-8').read().split('## 작성 필요')[-1]))
R['broken_links'] = {l: dict(pages=sorted(ps), in_todo=l in todo) for l, ps in broken.items() if l != '페이지 이름'}
R['todo_list'] = sorted(todo)
R['todo_now_exists'] = sorted(t for t in todo if t in names)
content = {k for k, v in pages.items() if v['fm'].get('type') in ('문서', '조문', '쟁점', '사례', '분석')}
R['orphans'] = sorted(k for k in content if not (inn.get(k, set()) - {x for x in pages if pages[x]['name'] == '_index'}))
# _index registration
idx_missing = []
for k in content:
    folder = k.split(os.sep)[0]
    ip = os.path.join(folder, '_index.md')
    if ip in pages and '[[' + pages[k]['name'] + ']]' not in pages[ip]['body']:
        idx_missing.append(k)
R['index_missing'] = sorted(idx_missing)
# mgmt links from content body
R['mgmt_links_in_body'] = sorted(k for k in content if any(l.split('/')[-1] in mgmt for l in out.get(k, ())) and pages[k]['fm'].get('type') != '분석')
# reverse links: A links B (both content, 조문/쟁점/사례/문서) but B does not link A
def nonreciprocal(k):
    res = []
    for l in out.get(k, ()):
        t = names.get(l) or names.get(l.split('/')[-1])
        if t and t in content and t != k and pages[t]['fm'].get('type') != '분석' and pages[k]['name'] not in out.get(t, set()):
            res.append(pages[t]['name'])
    return sorted(res)
R['_nonrecip'] = {pages[k]['name']: nonreciprocal(k) for k in content if pages[k]['fm'].get('type') != '분석'}

# sources
src_bad = {}
for k in content:
    for s in pages[k]['fm'].get('sources') or []:
        s = str(s)
        if s.startswith('web:'): continue
        if s.startswith('script:'):
            if not os.path.exists(os.path.join(ROOT, s[7:].strip())): src_bad.setdefault(k, []).append(s)
            continue
        if not os.path.exists(os.path.join(ROOT, s)): src_bad.setdefault(k, []).append('없음: ' + s)
        # SOURCE_REGISTRY 규칙 2: 가장 구체적인(가장 긴) 일치 항목이 우선한다
        match = [i for i in items if s.rstrip('/') == i['path'].rstrip('/') or (i['path'].endswith('/') and s.startswith(i['path']))]
        if match and max(match, key=lambda i: len(i['path'])).get('canonical') is False:
            src_bad.setdefault(k, []).append('중복본: ' + s)
    if not pages[k]['fm'].get('sources'): src_bad.setdefault(k, []).append('sources 없음')
R['sources_bad'] = src_bad
# internal
intr = []
for k in content:
    fm = pages[k]['fm']
    srcs = [str(s) for s in fm.get('sources') or []]
    uses = any(any(s.startswith(i) or s == i for i in internal_src) for s in srcs)
    links_lit = any(LIT in l for l in out.get(k, ()))
    mentions = LIT in pages[k]['body'] or '소송 현황 문서' in pages[k]['body']
    cls = fm.get('classification')
    if (uses or links_lit or mentions) and cls != 'internal':
        intr.append(dict(page=k, source=uses, link=links_lit, mention=mentions, classification=cls))
R['internal_suspect'] = intr
R['internal_pages'] = sorted(k for k in pages if pages[k]['fm'].get('classification') == 'internal')
# 사례 상태
cases = {k: pages[k]['fm'] for k in content if pages[k]['fm'].get('type') == '사례'}
R['case_status'] = {k: dict(ds=f.get('decision_stage'), dst=f.get('decision_status'), js=f.get('judicial_status')) for k, f in cases.items()}
# 조문
arts = {k: pages[k]['fm'] for k in content if pages[k]['fm'].get('type') == '조문'}
R['articles_total'] = len(arts)
R['articles_no_verified'] = sum(1 for f in arts.values() if not f.get('verified_at'))
R['current_text_without_verified'] = sorted(k for k in arts if not arts[k].get('verified_at') and re.search(r'현행 조문', pages[k]['body']) and not re.search(r'"현행 조문"', pages[k]['body']))
# status
R['status_not_draft'] = sorted(k for k in content if pages[k]['fm'].get('status') != 'draft')
# 충돌
R['conflict_marks'] = {k: len(re.findall('〔충돌〕', pages[k]['body'])) for k in content if '〔충돌〕' in pages[k]['body']}
# 추가 확인 필요
open_items = {}
for k in content:
    b = pages[k]['body']
    m = re.search(r'\n##+ [^\n]*추가 확인 필요[^\n]*\n(.*?)(?=\n## |\Z)', b, re.S)
    if not m: continue
    sec = m.group(1)
    o = re.findall(r'^\s*- \[ \] (.*)$', sec, re.M)
    d = re.findall(r'^\s*- \[x\] ', sec, re.M | re.I)
    plain = [l for l in re.findall(r'^\s*[-*] (?!\[)(.*)$', sec, re.M)]
    open_items[k] = dict(open=o, done=len(d), plain=plain)
R['_open_items'] = open_items
R['counts'] = dict(pages=len(pages), content=len(content), cases=len(cases), articles=len(arts))
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
