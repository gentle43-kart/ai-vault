# -*- coding: utf-8 -*-
"""
ad_articles.py v1.1 (2026-09-27, Claude Opus 5.5) — AGENTS.md 7.1 "광고심의규정 통계" 기준(v1.12, 사용자 승인 2026-09-27)
  v1.1: 안건 구분을 통계부문 기준으로 바꾸고, 의결번호 형태는 "번호 형태"로 따로 출력한다(v1.0의 "방송 안건" 해석 정정).

목적
  방송심의 의결 내역 통계 CSV에서 「방송광고심의에 관한 규정」(광고심의규정) 조문별 적용 행 수와
  결과 분포를 집계한다. 7.1절 방송심의 기준(stats_articles.py)의 읽기·날짜·결과 분류 함수를 그대로 쓰고,
  조문 식별 대상 규정만 광고심의규정으로 바꾼다.

입력
  stats_articles.py 와 같다(2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일, 선방위 제외).

출력
  표준 출력(텍스트). 파일을 만들지 않는다.

규칙(7.1 광고심의규정 통계)
  - 집계 단위: CSV 행. 한 행에 같은 조가 여러 번 나와도 1행.
  - 조문 식별: 관련조항에서 「방송광고심의에 관한 규정」(띄어쓰기·괄호 변형, "(규칙 제142호)" 같은 판 표기 허용) 뒤,
    다음 법령명 앞까지의 "제n조(의m)"만 센다. 괄호 안의 "…법"은 법령명으로 보지 않는다(stats_articles.py와 같음).
  - 조는 조 번호로 세고, 조 제목 표기 변형을 함께 출력한다. 판에 따라 내용이 바뀐 조(예: 제26조 건강기능식품,
    2020.12.28. 삭제)는 조 제목으로 판을 구분한다.
  - 표기 예외(사용자 결정 2026-09-26): "11조의2"('제' 누락) → 제11조의2, "제38조(보험광고)의2" → 제38조의2.
    "「방송광고심의에 관한 규정」제56호(방송광고의 제한)" 1행(2012.10.11. 씨알로)은 방송심의규정 구 제56조의
    오기로 보아 광고심의규정 집계에서 뺀다(조 번호로 읽히지 않아 자동으로 빠지며, 방송심의 집계에도 넣지 않음).
  - 안건 구분(v1.1): 통계부문이 "방송광고"이거나 매체명(PP·지상파·종편·SO·위성, 2012~2013년 파일에서 광고 행에 쓴 표기)이면
    방송광고 안건, 그 밖의 부문(연예오락·보도교양 등)이면 방송프로그램 안건.
  - 번호 형태(보조 정보): 의결번호에 "광고"가 있으면 "광고 번호", 없으면 "그 밖의 번호", 의결번호가 없으면 "의결번호 없음".
  - 결과 분류: stats_articles.result_class(가장 무거운 조치 하나).

검증값(대상 2012.01~2026.06, 12,560행, 2026-09-26 기기에서 실행)
  광고심의규정 표기 3,276행, 조 식별 3,275행(방송광고 안건 3,271 / 방송프로그램 안건 4), 미식별 1행(위 예외)
  번호 형태: 광고 번호 1,951 / 그 밖의 번호 887 / 의결번호 없음 437
  제18조 1,512 / 제3조 237 / 제23조 216 / 제38조의2 89 / 제11조의2 14

사용
  python ad_articles.py            # 전체 요약
  python ad_articles.py --article 제3조
"""
import argparse, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S

_TARGET = ("방송광고심의에관한규정",)

def ad_articles(text):
    s = S._norm(text or "")
    dm = S._depth(s)
    laws = [m for m in S._LAW.finditer(s) if dm[m.start()] == 0]
    res = {}
    for i, m in enumerate(laws):
        if m.group(1) not in _TARGET:
            continue
        seg = s[m.end():laws[i + 1].start() if i + 1 < len(laws) else len(s)]
        # 예외 표기(사용자 결정 2026-09-26): "11조의2"처럼 '제'가 빠진 조 → 제11조의2,
        # "제38조(보험광고)의2" → 제38조의2(조 제목이 가지 번호 앞에 끼어든 표기). 원자료는 고치지 않는다.
        seg = re.sub(r"(?<![제\d])(\d+조의\d+)", r"제\1", seg)
        seg = re.sub(r"제(\d+)조\(([^)]*)\)의(\d+)", r"제\1조의\3(\2)", seg)
        for a in S._ART.finditer(seg):
            sub = a.group(2) or a.group(3)
            k = f"제{a.group(1)}조" + (f"의{sub}" if sub else "")
            res.setdefault(k, a.group(4) or "")
    return res

_AD_SECTORS = {"방송광고", "PP", "지상파", "종편", "SO", "위성"}

def kind(r):
    """안건 구분(v1.1): 통계부문 기준."""
    return "방송광고" if (r.get("통계부문") or "").strip() in _AD_SECTORS else "방송프로그램"

def numform(r):
    """번호 형태(보조 정보, v1.0의 kind)."""
    c = S.case_no(r)
    if not c:
        return "의결번호 없음"
    return "광고 번호" if "-광고-" in c else "그 밖의 번호"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--article"); a = ap.parse_args()
    R = S.load()
    rows = []; mention = 0
    for r in R:
        rel = r.get("관련조항", "")
        if "방송광고심의에관한규정" in S._norm(rel):
            mention += 1
        arts = ad_articles(rel)
        if arts:
            rows.append((r, arts))
    print(f"대상 행 {len(R)} / 관련조항에 광고심의규정 표기 {mention} / 광고심의규정 조가 식별된 행 {len(rows)}")
    kc = collections.Counter(kind(r) for r, _ in rows)
    print("안건 구분:", dict(kc))
    print("번호 형태:", dict(collections.Counter(numform(r) for r, _ in rows)))
    rc = collections.Counter(S.result_class(r.get("심의결과", "")) for r, _ in rows)
    print("결과:", {k: rc[k] for k in S.ORDER if rc[k]})
    art = collections.Counter(); titles = collections.defaultdict(collections.Counter)
    for r, arts in rows:
        for k, t in arts.items():
            art[k] += 1; titles[k][t] += 1
    if a.article:
        sel = [(r, arts) for r, arts in rows if a.article in arts]
        print(a.article, len(sel), dict(titles[a.article]))
        print(" 안건:", dict(collections.Counter(kind(r) for r, _ in sel)))
        print(" 번호 형태:", dict(collections.Counter(numform(r) for r, _ in sel)))
        c = collections.Counter(S.result_class(r.get("심의결과", "")) for r, _ in sel)
        print(" 결과:", {k: c[k] for k in S.ORDER if c[k]})
        print(" 연도:", dict(sorted(collections.Counter(S.year(r) for r, _ in sel).items(), key=lambda x: (x[0] is None, x[0] or 0))))
        return
    for k, n in art.most_common():
        print(f"{k}\t{n}\t{dict(titles[k].most_common(3))}")
    miss = [r for r in R if "방송광고심의에관한규정" in S._norm(r.get("관련조항", "")) and not ad_articles(r.get("관련조항", ""))]
    print("표기는 있으나 조가 식별되지 않은 행:", len(miss))
    for r in miss[:5]:
        print("  ", S.case_no(r), (r.get("관련조항", "") or "")[:120].replace("\n", " "))

if __name__ == "__main__":
    main()
