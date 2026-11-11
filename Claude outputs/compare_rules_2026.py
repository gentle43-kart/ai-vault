# -*- coding: utf-8 -*-
"""
compare_rules_2026.py v1.1 (2026-11-11, Claude Sonnet 5.5)

목적
  위원회 규칙 제8~12호(2026.9.21. 제정, 2026.9.29. 시행)의 국가법령정보센터 등재본 변환본과,
  조문 페이지 238개의 "## 1." 절 인용 블록(">"로 시작하는 줄)을 비교해 일치·불일치로 분류한다(lint 제안 ①).
  파일을 고치지 않는다(읽기 전용). 위키 반영은 별도 단계에서 한다.

입력
  - 조문 페이지: 0 wiki/조문/*.md 중 머리말 law가 방송심의규정·광고심의규정·상품판매방송규정·통신심의규정·등급분류규칙이고
    본문에 열린 항목 "- [ ] 국가법령정보센터에 제N호가 등재되면 원문과 대조하고 ..."가 있는 페이지
  - 등재본 변환본(1 documents_md/법령_md/방송_md·통신_md, 파일명 끝 "(제N호)(20260929).md")
출력
  표준출력에 규칙별 개수와 불일치 목록. --json 경로를 주면 페이지별 판정(일치 여부, 정규화 전 일치 여부, 차이 위치)을 JSON으로 저장.
방법
  페이지의 인용 블록(앞의 "> " 제거, 줄 연결)과 변환본 전체를 같은 방식으로 정규화한 뒤,
  인용 블록이 변환본 안에 그대로 들어 있으면 일치로 본다. 변환본이 쪽 단위 기본 모드라 조문 줄바꿈이 원본과 달라서
  줄 단위가 아니라 문자열 포함으로 비교한다. 포함되지 않으면 인용 블록 앞 20자를 시작점으로 찾고
  difflib으로 첫 차이를 위치와 함께 보고한다(시작점이 없으면 "시작점 없음").
정규화 규칙(양쪽에 같은 규칙)
  1. 변환본의 쪽 표시 `<!-- p.N -->` 제거
  2. 날짜 표기 "2026. 9. 21." / "2026.9.21." / "2026. 9. 21" → "2026-09-21" (개정 주석 포함 모든 날짜)
  3. 따옴표 모양 “ ” → ", ‘ ’ → '
  4. 가운뎃점 ㆍ(U+318D) ・(U+30FB) ‧(U+2027) • → ·(U+00B7)
  5. 모든 공백(줄바꿈 포함) 제거
  6. (v1.1) 낫표 ｢ ｣(U+FF62·FF63) → 「 」, 점 모양 ․(U+2024) ･(U+FF65) → ·
  7. (v1.1) 변환본(PDF 쪽 머리글)의 "법제처 N 국가법령정보센터 [규칙명]" 쪽 머리글을 정규화 후 문자열에서 제거
  9. (v1.1) 포함 확인 뒤, 등재본에서 인용 블록 바로 뒤가 다음 조·장·절·부칙·별표(또는 끝)로 이어지는지 확인해 조문 끝 누락을 잡는다
  8. (v1.1) 페이지 인용 블록 안에서 `**`로 시작하는 줄(정정·반영 메모)은 비교에서 빼고 따로 센다
  정규화로 해소한 일치 수는 별도로 센다(정규화 전 포함 여부 = 공백만 정리해 비교).
검증값(기대): 대상 238개 = 방송심의규정 70, 광고심의규정 59, 상품판매방송규정 72, 통신심의규정 26, 등급분류규칙 11.
  기대와 다르면 종료 코드 2.
사용
  python "Claude outputs/compare_rules_2026.py" [--json 결과.json]
"""
import argparse, difflib, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, '0 wiki', '조문')
MD = os.path.join(ROOT, '1 documents_md', '법령_md')
RULES = {  # law -> (호수, 변환본 폴더)
    '방송심의규정': (8, '방송_md'), '광고심의규정': (10, '방송_md'), '상품판매방송규정': (11, '방송_md'),
    '통신심의규정': (12, '통신_md'), '등급분류규칙': (9, '방송_md')}
EXPECT = {'방송심의규정': 70, '광고심의규정': 59, '상품판매방송규정': 72, '통신심의규정': 26, '등급분류규칙': 11}
OPEN = re.compile(r'(?m)^- \[ \] 국가법령정보센터에 제(\d+)호가 등재되면')

HDR = re.compile('법제처' + r'\d*' + '국가법령정보센터' + '(?:방송심의에관한규정|방송광고심의에관한규정|상품소개및판매방송심의에관한규정|방송프로그램의등급분류및표시등에관한규칙|정보통신에관한심의규정)?')

def norm_light(s):
    return re.sub(r'\s+', '', s)

def norm(s):
    s = re.sub(r'<!-- p\.\d+ -->', '', s)
    s = re.sub(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?', lambda m: '%s-%02d-%02d' % (m.group(1), int(m.group(2)), int(m.group(3))), s)
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    for c in 'ㆍ・‧•․･':
        s = s.replace(c, '·')
    s = s.replace('｢', '「').replace('｣', '」')
    return re.sub(r'\s+', '', s)

def front(txt):
    m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
    d = {}
    if m:
        for l in m.group(1).split('\n'):
            k, _, v = l.partition(':')
            if k and not l.startswith((' ', '-')):
                d[k.strip()] = v.strip()
    return d

def quote_block(txt):
    m = re.search(r'(?m)^## 1\..*$', txt)
    if not m:
        return None
    rest = txt[m.end():]
    n = re.search(r'(?m)^## ', rest)
    sec = rest[:n.start()] if n else rest
    lines = [re.sub(r'^>\s?', '', l) for l in sec.split('\n') if l.startswith('>')]
    memo = [l for l in lines if l.startswith('**')]
    lines = [l for l in lines if not l.startswith('**')]
    return ('\n'.join(lines), len(memo)) if lines else None

def find_md(law):
    no, d = RULES[law]
    c = glob.glob(os.path.join(MD, d, '*(제%d호)(20260929).md' % no))
    return c[0] if len(c) == 1 else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    a = ap.parse_args()
    full = {}
    for law in RULES:
        p = find_md(law)
        if not p:
            sys.exit('등재본 변환본을 찾지 못함: %s' % law)
        t = open(p, encoding='utf-8').read()
        full[law] = (HDR.sub('', norm(t)), norm_light(re.sub(r'<!-- p\.\d+ -->', '', t)), p)
    pages = []
    for p in sorted(glob.glob(os.path.join(W, '*.md'))):
        txt = open(p, encoding='utf-8').read()
        fm = front(txt)
        law = fm.get('law')
        if law in RULES and OPEN.search(txt):
            pages.append((p, law, txt))
    cnt = {}
    for _, law, _ in pages:
        cnt[law] = cnt.get(law, 0) + 1
    print('대상 페이지', len(pages), cnt)
    res = []
    for p, law, txt in pages:
        qb = quote_block(txt)
        q, memo = qb if qb else (None, 0)
        name = os.path.basename(p)[:-3]
        if not q:
            res.append(dict(page=name, law=law, status='인용블록없음'))
            continue
        nq = norm(q)
        nf, lf, _ = full[law]
        if nq in nf:
            # v1.1: 인용 블록 뒤에 등재본의 다른 문언이 더 이어지면(조문 끝 누락) 일치로 보지 않는다
            ends = [m.end() for m in re.finditer(re.escape(nq), nf)]
            if any(re.match(r'(?:방송심의에관한규정|방송광고심의에관한규정|상품소개및판매방송심의에관한규정|방송프로그램의등급분류및표시등에관한규칙|정보통신에관한심의규정)?(?:$|제\d+(?:조|장|절)|부칙|\[별|별표|별지|\[서식)', nf[e:e + 40]) for e in ends):
                res.append(dict(page=name, law=law, status='일치', light=norm_light(q) in lf, memo=memo))
                continue
            res.append(dict(page=name, law=law, status='불일치', light=False, memo=memo,
                            detail='인용 블록은 등재본에 들어 있으나 뒤에 이어지는 문언이 있음: %s' % nf[ends[0]:ends[0] + 40]))
            continue
        anchor = nq[:20]
        i = nf.find(anchor)
        d = dict(page=name, law=law, status='불일치', light=False, memo=memo)
        if i < 0:
            d['detail'] = '시작점 없음(앞 20자: %s)' % anchor
        else:
            seg = nf[i:i + len(nq) + 200]
            sm = difflib.SequenceMatcher(None, nq, seg, autojunk=False)
            diffs = []
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    continue
                if j1 >= len(nq) + 100 and tag == 'insert':
                    continue
                diffs.append('%s 페이지[%s] ↔ 등재본[%s] (…%s…)' % (tag, nq[i1:i2][:40], seg[j1:j2][:40], nq[max(0, i1 - 8):i1]))
                if len(diffs) >= 3:
                    break
            d['detail'] = ' | '.join(diffs) if diffs else '끝부분만 다름'
        res.append(d)
    ok = [r for r in res if r['status'] == '일치']
    bad = [r for r in res if r['status'] != '일치']
    print('일치 %d (정규화 필요 없이 공백만 정리해도 일치 %d), 불일치·기타 %d' % (len(ok), sum(1 for r in ok if r.get('light')), len(bad)))
    per = {}
    for r in res:
        k = per.setdefault(r['law'], [0, 0])
        k[0 if r['status'] == '일치' else 1] += 1
    for law in RULES:
        print('  %s: 일치 %d / 불일치 %d (기대 대상 %d, 실제 %d)' % (law, per.get(law, [0, 0])[0], per.get(law, [0, 0])[1], EXPECT[law], cnt.get(law, 0)))
    print('주석(**) 줄을 제외하고 비교한 페이지', sum(1 for r in res if r.get('memo')))
    for r in bad[:40]:
        print('- [%s] %s : %s' % (r['status'], r['page'], r.get('detail', '')[:200]))
    if len(bad) > 40:
        print('  … 외 %d건(전체는 --json 결과 참조)' % (len(bad) - 40))
    if a.json:
        json.dump(res, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if len(pages) != 238 or cnt != EXPECT:
        print('검증값 불일치: 기대 238', EXPECT)
        sys.exit(2)

main()
