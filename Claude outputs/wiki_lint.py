# -*- coding: utf-8 -*-
"""
wiki_lint.py v1.7 (2026-11-13; v1.7: '추가 확인 필요' 절의 `- [→]` 항목(외부 확인 대기 목록으로 옮긴 것)을 external로 읽고 R['external_wait']로 따로 집계한다. 출력은 v1.6에 항목만 더했다;
  v1.6: 판정 정리 — ① log.md·0 wiki/log/ 조각에서 나온 끊긴 링크(옛 조 번호 등 과거 기록)는 broken_links_log(참고)로 따로 내고
  broken_links에는 내용 페이지에서 나온 것만 남긴다 ② 종료 코드 1의 조건을 broken_sources 외에 broken_links·yaml_error·sources_bad까지 넓힌다(종료 코드는 0·1만 쓴다).
  그 밖의 출력은 v1.5와 같다;
  v1.5: AGENTS.md v1.38 8절 단서 — internal 출처가 모두 registry type statistics이고 링크·언급 단서가 없는 페이지는
  internal_suspect 대신 internal_aggregate(확인용 목록)로 출력, 그 밖의 출력은 v1.4와 같음;
  v1.4: 0 wiki/log/ 월별 조각을 머리말 점검·stray 점검에서 빼고 링크 스캔에는 포함(AGENTS.md v1.35 10절);
  v1.3 2026-10-06; v1.1: 중복본 판정에 레지스트리 규칙 2 적용, v1.2: _Inbox·_templates 제외(AGENTS.md v1.16 6.3),
  v1.3: ① 링크 해석에 머리말 aliases 반영 ② 내부 출처·중복본 판정을 색인기 Registry.match와 같은 규칙(파일 단위 우선, 그다음 가장 긴 폴더)으로
  ③ 위키 전체 페이지의 sources 로컬 경로 존재 검사 결과를 broken_sources로 따로 출력, 깨진 출처가 있으면 종료 코드 1)
목적: AGENTS.md 6.6절 lint 항목 가운데 기계적으로 점검할 수 있는 것을 한 번에 점검한다.
입력: 자료창고 루트(기본값: 이 파일의 상위 폴더), SOURCE_REGISTRY.yaml, 0 wiki/**/*.md (@clippings·@Inbox·@templates 제외, 옛 이름도 제외)
출력: 표준출력에 JSON(점검 항목별 결과). 파일을 고치지 않는다(읽기 전용). 종료 코드(v1.6): broken_sources(존재하지 않는 로컬 출처)·broken_links(내용 페이지의 끊긴 링크)·yaml_error·sources_bad 가운데 하나라도 있으면 1, 모두 없으면 0.
      broken_links_log(log 기록의 끊긴 링크)는 참고용이라 종료 코드에 넣지 않는다. 스크립트가 예외로 죽어도 파이썬은 1을 내므로, 호출하는 쪽은 표준출력이 JSON인지도 확인해야 한다.
검증값: 2026-09-22 lint 보고 당시 기준(조문 60개 verified_at 공란)과 현재 조문 페이지 수를 함께 출력해 대조한다.
"""
import os, re, sys, json, glob, yaml
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, '0 wiki')
LIT = '위원회 관련 소송 현황'
reg = yaml.safe_load(open(os.path.join(ROOT, 'SOURCE_REGISTRY.yaml'), encoding='utf-8'))
items = next(v for v in reg.values() if isinstance(v, list))
noncanon = [i['path'] for i in items if i.get('canonical') is False]


def _norm(p):
    return str(p).replace(chr(92), '/').strip('/')


def reg_match(rel):
    """build_index.Registry.match와 같은 규칙: 파일 단위 항목 우선, 그다음 가장 긴 폴더 경로."""
    rel = _norm(rel)
    best, best_len = None, -1
    for i in items:
        raw = str(i['path'])
        p = _norm(raw)
        if not raw.endswith('/'):
            if rel == p:
                return i
            continue
        if (rel == p or rel.startswith(p + '/')) and len(p) > best_len:   # 출처가 폴더 자체일 수도 있다(sources의 'a/b/')
            best, best_len = i, len(p)
    return best

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
        # v1.4: 0 wiki/log/ 월별 조각은 머리말이 없는 게 정상(AGENTS.md 10절). 형식 점검은 빼고 링크는 log.md처럼 센다
        err = None if rel.startswith('log' + os.sep) else 'no frontmatter'
    name = os.path.basename(rel)[:-3]
    pages[rel] = dict(name=name, fm=fm, body=body, err=err, full=txt)

names = {v['name']: k for k, v in pages.items()}
# v1.3: 머리말 aliases도 링크 대상 이름으로 인정한다(조 번호가 바뀐 조문의 '구 제n조' 이름 등, AGENTS.md 3.1)
alias_names = {}
for k, v in pages.items():
    al = v['fm'].get('aliases') if isinstance(v['fm'], dict) else None
    for a in (al if isinstance(al, list) else [al] if al else []):
        a = str(a).strip()
        if a and a not in names:
            alias_names[a] = k
link_names = {**alias_names, **names}   # 같은 이름이면 실제 페이지가 우선
mgmt = {'index', 'log', '_index'}
R = {}
R['yaml_error'] = {k: v['err'] for k, v in pages.items() if v['err']}
R['stray_root_files'] = [k for k in pages if os.sep not in k and k not in ('index.md', 'log.md')] + \
    [k for k in pages if k.split(os.sep)[0] not in ('문서', '조문', '쟁점', '사례', '분석', 'log') and os.sep in k]

# links
link_re = re.compile(r'\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]')
out, inn, broken = {}, {}, {}
for k, v in pages.items():
    if v['err'] == 'no frontmatter': continue
    ls = set(l.strip() for l in link_re.findall(v['body']))
    out[k] = ls
    for l in ls:
        base = l.split('/')[-1]
        if l in link_names or base in link_names or l.endswith('_index') or l in ('index', 'log'):
            tgt = link_names.get(l) or link_names.get(base)
            if tgt: inn.setdefault(tgt, set()).add(k)
        else:
            broken.setdefault(l, []).append(k)
todo = set(link_re.findall(open(os.path.join(W, 'index.md'), encoding='utf-8').read().split('## 작성 필요')[-1]))
# v1.6: log.md와 0 wiki/log/ 조각은 과거 기록이라 링크가 옛 이름이어도 고치지 않는다(AGENTS.md 10절). 내용 페이지와 나눠 센다
def _is_log(k):
    return k == 'log.md' or k.startswith('log' + os.sep)
R['broken_links'], R['broken_links_log'] = {}, {}
for l, ps in broken.items():
    if l == '페이지 이름':
        continue
    c_ps, l_ps = sorted(p for p in ps if not _is_log(p)), sorted(p for p in ps if _is_log(p))
    if c_ps:
        R['broken_links'][l] = dict(pages=c_ps, in_todo=l in todo)
    if l_ps:
        R['broken_links_log'][l] = dict(pages=l_ps, in_todo=l in todo)
R['todo_list'] = sorted(todo)
R['todo_now_exists'] = sorted(t for t in todo if t in link_names)
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
        t = link_names.get(l) or link_names.get(l.split('/')[-1])
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
        # SOURCE_REGISTRY 규칙 2: 가장 구체적인 일치 항목이 우선한다(색인기 Registry.match와 같은 규칙)
        m_ = reg_match(s)
        if m_ and m_.get('canonical') is False:
            src_bad.setdefault(k, []).append('중복본: ' + s)
    if not pages[k]['fm'].get('sources'): src_bad.setdefault(k, []).append('sources 없음')
R['sources_bad'] = src_bad
# v1.3: 위키 모든 페이지(내용 페이지 외 포함)의 로컬 출처 경로 존재 검사. web:은 제외, script:는 접두어를 떼고 검사
broken_sources = {}
for k, v in pages.items():
    fm_src = v['fm'].get('sources') if isinstance(v['fm'], dict) else None
    for s in (fm_src if isinstance(fm_src, list) else [fm_src] if fm_src else []):
        s = str(s).strip()
        if s.startswith('web:'):
            continue
        rel_s = s[7:].strip() if s.startswith('script:') else s
        if not os.path.exists(os.path.join(ROOT, rel_s)):
            broken_sources.setdefault(k, []).append(s)
R['broken_sources'] = broken_sources
# internal
intr = []
agg = []
for k in content:
    fm = pages[k]['fm']
    srcs = [str(s) for s in fm.get('sources') or []]
    uses = any((reg_match(s) or {}).get('classification') == 'internal' for s in srcs if not s.startswith(('web:', 'script:')))
    links_lit = any(LIT in l for l in out.get(k, ()))
    mentions = LIT in pages[k]['body'] or '소송 현황 문서' in pages[k]['body']
    cls = fm.get('classification')
    if (uses or links_lit or mentions) and cls != 'internal':
        # v1.5: internal 출처가 모두 registry type statistics이고 링크·언급 단서가 없으면 집계값만 옮긴 페이지로 보고 따로 낸다(AGENTS.md 8절 단서)
        int_types = {(reg_match(s) or {}).get('type') for s in srcs
                     if not s.startswith(('web:', 'script:')) and (reg_match(s) or {}).get('classification') == 'internal'}
        if uses and not links_lit and not mentions and int_types == {'statistics'}:
            agg.append(dict(page=k, source=uses, classification=cls))
        else:
            intr.append(dict(page=k, source=uses, link=links_lit, mention=mentions, classification=cls))
R['internal_suspect'] = intr
R['internal_aggregate'] = agg   # v1.5: 확인용 목록(집계값만 옮긴 페이지가 실제로 집계값뿐인지 사람이 확인)
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
    ext = re.findall(r'^\s*- \[→\] (.*)$', sec, re.M)   # v1.7: 외부 확인 대기 목록으로 옮긴 항목(열린 항목에서 뺀다)
    open_items[k] = dict(open=o, done=len(d), plain=plain, external=ext)
R['_open_items'] = open_items
# v1.7: 분석/외부 확인 대기.md의 대기(- [ ]) 항목 수와 페이지에서 옮긴 표시([→]) 수
_wait = [k for k in pages if k.endswith('외부 확인 대기')]
R['external_wait'] = dict(moved_marks=sum(len(v.get('external', [])) for v in open_items.values()),
                          waiting=sum(len(re.findall(r'^\s*- \[ \] ', pages[k]['body'], re.M)) for k in _wait),
                          list_pages=_wait)
R['counts'] = dict(pages=len(pages), content=len(content), cases=len(cases), articles=len(arts))
EXIT_KEYS = ('broken_sources', 'broken_links', 'yaml_error', 'sources_bad')
R['exit_reasons'] = [k for k in EXIT_KEYS if R[k]]
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
# v1.6: 종료 코드는 0·1만. 1이면 어느 항목 때문인지 JSON의 exit_reasons에 남긴다(maintenance_check가 요약에 쓴다)
sys.exit(1 if any(R[k] for k in EXIT_KEYS) else 0)
