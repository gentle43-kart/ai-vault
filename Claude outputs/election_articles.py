# -*- coding: utf-8 -*-
"""
목적: 선거방송심의위원회(선방위) 의결 내역 통계 CSV에서 「선거방송심의에 관한 특별규정」 조문별
      적용 행 수·결과 분포·선거별 분포를 집계한다(AGENTS.md 7.1 "선거방송심의 통계" 기준).
입력: 2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/선방위_02-25_part01~04.csv (registry stats, 2002~2025)
      2 data_csv/통계_csv/방송/쳇지피팅용 병합_csv/선방위 통계(02-26.7).csv (registry stats_election_recent, 2026년 행만)
출력: 표준출력(JSON). 인자로 조 번호를 주면 해당 조만 출력한다. 예) python3 election_articles.py 5 10 18
규칙:
  - 집계 단위: CSV 행. 2026년 행은 (의결번호, 의결일, 관련조항, 결과)가 같은 중복 행을 1행으로 센다.
  - 조문 식별: 관련조항 칸을 왼쪽부터 읽어 규정명(특별규정 / 방송심의에 관한 규정 / 그 밖의 법령)을 추적하고,
    특별규정에 속하는 "제N조(조 제목)"만 센다. 조는 (조 번호, 조 제목) 쌍으로 식별하며, 한 행에 같은 쌍이
    여러 번 나와도 1행으로 센다. 규정명 없이 시작하는 조는 "규정명 미표기"로 따로 센다.
  - 항: 특별규정 조 표기 뒤, 다음 조·규정명 앞까지의 "제N항"을 모아 (조, 항) 쌍별 행 수를 센다(항 표기 없는 행은 항 집계에서 빠진다).
  - 결과 분류: 시청자에 대한 사과 > 관계자 징계 > 경고 > 주의 > 권고 > 의견제시 순으로 가장 무거운 것 하나,
    그 밖에 문제없음, 기각, 각하, 의결불성립, 이첩, 부결, 인용(반론보도 청구 등), 미분류.
검증값(2026-09-25): 02-25 파일 1,467행, 2026년 고유 행 51행(원 행 56행),
  특별규정 제5조(공정성) 232행, 제18조(여론조사의 보도) 193행, 제10조(시사정보프로그램) 157행,
  제17조(여론조사의 보도) 150행, 제17조(출처명시) 4행 (2002~2026.7, 2026년 고유 행 포함).
  수치는 첫 실행 결과로 정했으며(관련조항 표본 대조로 규정명 추적을 확인) 스크립트를 고치면 다시 확인한다.
수정(2026-09-26, 33차): 규정명에 구 법률명 「공직선거및선거부정방지법」을 추가했다. 전에는 2002 RTV 4행의 공직선거법
  제81조·제82조가 특별규정 조 목록에 섞였다. 수정 전후 특별규정 조별 행 수는 이 4행(제81조 3, 제82조 1)이 빠진 것 말고는 같다.
"""
import csv, glob, json, os, re, sys, collections

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '2 data_csv', '통계_csv')
MAIN = sorted(glob.glob(os.path.join(BASE, '방송', '제미나이 노트북용 분할_csv', '선방위_02-25_part*.csv')))
RECENT = os.path.join(BASE, '방송', '쳇지피팅용 병합_csv', '선방위 통계(02-26.7).csv')

def load():
    out = []
    for f in MAIN:
        with open(f, encoding='utf-8-sig', newline='') as fh:
            rd = csv.reader(fh); next(rd)
            for r in rd:
                out.append(('main', r))
    n_main = len(out)
    seen = set(); n_raw26 = 0
    with open(RECENT, encoding='utf-8-sig', newline='') as fh:
        rd = csv.reader(fh); next(rd)
        for r in rd:
            if re.search(r'2026', r[1] or '') :
                n_raw26 += 1
                key = (r[0].strip(), r[1].strip(), r[6].strip(), r[7].strip())
                if key in seen: continue
                seen.add(key); out.append(('2026', r))
    return out, n_main, n_raw26

def year_of(r):
    m = re.search(r'(20\d\d)', r[1] or '') or re.search(r'(20\d\d)', r[0] or '')
    return int(m.group(1)) if m else None

def election_of(r):
    g = (r[0] or '').strip()
    m = re.match(r'제?(20\d\d)-([가-힣]+\d*)-', g)
    if m: return f'{m.group(1)} {m.group(2)}'
    return g

REG = re.compile(r'(선거방송\s*심의에\s*관한\s*특별\s*규정|특별규정)|(방송\s*심의에\s*관한\s*규정|방송심의규정)|(공직선거\s*및\s*선거부정\s*방지법|방송법|공직선거법|선거법|정보통신망법|청소년\s*보호법)')
ART = re.compile(r'제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*(?:\(\s*([^)]*?)\s*\))?')

def articles(s):
    s = s or ''
    tokens = [(m.start(), 'reg', m) for m in REG.finditer(s)] + [(m.start(), 'art', m) for m in ART.finditer(s)]
    tokens.sort(key=lambda t: t[0])
    cur = None; res = set(); unlabeled = set(); paras = set()
    for i, (pos, kind, m) in enumerate(tokens):
        if kind == 'reg':
            cur = 'special' if m.group(1) else ('bangsim' if m.group(2) else 'other')
        else:
            # 규정명 안의 "제"는 없으므로 그대로 판정
            no = m.group(1) + (('의' + m.group(2)) if m.group(2) else '')
            title = re.sub(r'\s+', ' ', (m.group(3) or '')).strip()
            if cur == 'special':
                res.add((no, title))
                nxt = tokens[i + 1][0] if i + 1 < len(tokens) else len(s)
                for pm in re.finditer(r'제\s*(\d+)\s*항', s[m.end():nxt]):
                    paras.add((no, title, pm.group(1)))
            elif cur is None: unlabeled.add((no, title))
    articles.paras = paras
    return res, unlabeled

ORDER = ['시청자에 대한 사과', '관계자 징계', '경고', '주의', '권고', '의견제시']
def result_of(v):
    v = re.sub(r'\s+', ' ', v or '').strip()
    if not v: return '미분류(빈칸)'
    if '사과' in v: return '시청자에 대한 사과'
    if '징계' in v: return '관계자 징계'
    if v.startswith('경고'): return '경고'
    if v.startswith('주의'): return '주의'
    if v.startswith('권고'): return '권고'
    if v.startswith('의견제시'): return '의견제시'
    if v.startswith('문제없음'): return '문제없음'
    if '각하' in v: return '각하'
    if '불성립' in v: return '의결불성립'
    if '기각' in v: return '기각'
    if '이첩' in v: return '이첩'
    if '부결' in v: return '부결'
    if '인용' in v: return '인용(반론보도 청구 등)'
    return '미분류:' + v

def main(targets):
    rows, n_main, n_raw26 = load()
    stat = collections.defaultdict(lambda: {'para': collections.Counter(), 'rows': 0, 'result': collections.Counter(), 'election': collections.Counter(), 'year': collections.Counter(), 'with_bangsim': 0})
    unl = collections.Counter(); unmapped = collections.Counter()
    for src, r in rows:
        arts, un = articles(r[6])
        for a in un: unl[a] += 1
        res = result_of(r[7])
        if res.startswith('미분류'): unmapped[res] += 1
        has_bs = bool(re.search(r'방송\s*심의에\s*관한\s*규정', r[6] or ''))
        for no, title, pa in articles.paras:
            if targets and no not in targets: continue
            stat[f'제{no}조({title})']['para'][f'제{pa}항'] += 1
        for a in arts:
            if targets and a[0] not in targets: continue
            s = stat[f'제{a[0]}조({a[1]})']
            s['rows'] += 1; s['result'][res] += 1; s['election'][election_of(r)] += 1
            s['year'][year_of(r)] += 1; s['with_bangsim'] += has_bs
    out = {'n_main': n_main, 'n_2026_raw': n_raw26, 'n_2026_unique': len(rows) - n_main,
           'unlabeled_articles': {f'제{k[0]}조({k[1]})': v for k, v in unl.items()},
           'unmapped_results': dict(unmapped),
           'articles': {k: {'rows': v['rows'], 'with_bangsim_reg': v['with_bangsim'],
                            'result': dict(v['result'].most_common()),
                            'para': dict(sorted(v['para'].items(), key=lambda t: int(re.sub(r'\D', '', t[0])))),
                            'election': dict(v['election']), 'year': {str(y): n for y, n in sorted(v['year'].items(), key=lambda t: (t[0] is None, t[0] or 0))}}
                        for k, v in sorted(stat.items(), key=lambda t: -t[1]['rows'])}}
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main(set(sys.argv[1:]))
