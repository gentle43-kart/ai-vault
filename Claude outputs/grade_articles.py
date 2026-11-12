# -*- coding: utf-8 -*-
"""
grade_articles.py v1.0 (2026-11-12, Claude Sonnet 5.5) — AGENTS_통계기준.md 7.1 "등급분류규칙 통계" 기준(v1.41, 사용자 승인 2026-11-12)

목적
  방송심의 의결 내역 통계 CSV에서 「방송프로그램의 등급분류 및 표시 등에 관한 규칙」(구 명칭 「방송프로그램의 등급분류에 관한 규칙」,
  약칭 등급분류규칙) 조문별 적용 행 수와 결과 분포를 집계한다. 읽기·날짜·결과 분류는 stats_articles.py의 함수를 그대로 쓴다.
  hyup_articles.py의 구조를 따른다.

입력
  stats_articles.py 와 같다(2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일, 선방위 제외).
  옵션: --recent(2026.07 이후 잠정본 행 추가) --until YYYY-MM-DD --article "제4조" --rows --verify

출력
  표준 출력(텍스트). 파일을 만들지 않는다. 읽기 전용.

규칙(7.1 등급분류규칙 통계)
  - 대상 행: 관련조항에 위 규칙명(띄어쓰기·「｢ 변형, "(규칙 제n호)" 판 표기, 괄호 없이 붙은 표기 허용)이 있는 행.
  - 조문 식별: 규칙명 뒤, 다음 법령명(「·｢로 시작하는 다른 이름, "방송심의에 관한 규정", "방송광고심의에", "협찬고지", "상품소개") 앞까지의 "제n조"만 센다.
    한 행에 같은 조가 여러 번 나와도 1행.
  - 판 판별: 제9호(2026.9.29. 시행)는 조 번호·제목이 종전 제126호와 같으므로 구·신 구분 없이 조 번호로 현행 조에 대응시킨다.
    조 제목이 있는데 현행 제목(제3조 등급분류, 제4조 등급분류기준, 제5조 등급표시, 제8조 예고방송, 제10조 권고 등 …)과 다르면 "판 미상".
    제목이 없으면 현행 조 번호로 세고 "제목 없음"으로 따로 보고한다. 제1~11조 밖의 번호는 "판 미상".
  - 결과 분류: stats_articles.result_class(가장 무거운 조치 하나).
검증값(--verify, 2012.01~2026.06, 12,560행): 등급분류규칙 표기 76행, 조 식별 76행, 제4조 70·제5조 3·제3조 2·제8조 2·제10조 1,
  판 미상 0, 결과 권고 29·경고 14·주의 17·의견제시 10·관계자 징계 5·기타 1.
"""
import argparse, collections, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S

# 현행 등급분류규칙(제9호) 조 제목. 종전 제126호와 조 번호·제목이 같다(등급분류규칙 조문 페이지 1절 자동 대조).
TITLES = {1: "목적", 2: "기본원칙", 3: "등급분류", 4: "등급분류기준", 5: "등급표시", 6: "등급사전고지",
          7: "청소년유해매체물", 8: "예고방송", 9: "적용범위", 10: "권고등", 11: "자료제출"}

NAME_RE = re.compile(r"방송프로그램의?\s*등급\s*분류[^「｢」｣]{0,20}?규[칙정]")
ART_RE = re.compile(r"제\s*(\d+)\s*조\s*(?:의\s*(\d+))?\s*(?:\(([^)]*)\)?)?")
STOP_RE = re.compile(r"[「｢]|방송\s*심의에\s*관한\s*규정|방송광고\s*심의에|협찬고지|상품\s*소개")

def sq(s):
    return re.sub(r"[\s·ㆍ‧․∙,]", "", s or "")

def articles(rel):
    """관련조항 → {(조 이름, 제목 유무)}. 규칙명이 없으면 None. 조 이름은 '제4조' 또는 '판 미상'."""
    out, found = set(), False
    for m in NAME_RE.finditer(rel):
        found = True
        s = rel[m.end():]
        n = STOP_RE.search(s)
        s = s[:n.start()] if n else s
        for x in ART_RE.finditer(s):
            no = int(x.group(1)); t = sq(x.group(3))
            if x.group(2) or no not in TITLES:
                out.add(("판 미상", bool(t)))
            elif t and not (t.startswith(TITLES[no][:4]) or TITLES[no].startswith(t[:4])):
                out.add(("판 미상", True))
            else:
                out.add(("제%d조" % no, bool(t)))
    return out if found else None

VERIFY = {"rows": 76, "ident": 76, "제4조": 70, "제5조": 3, "제3조": 2, "제8조": 2, "제10조": 1, "판 미상": 0,
          "권고": 29, "경고": 14, "주의": 17, "의견제시": 10, "관계자 징계": 5, "기타": 1}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article"); ap.add_argument("--rows", action="store_true")
    ap.add_argument("--recent", action="store_true"); ap.add_argument("--until"); ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    rows = S.load(a.recent, until=a.until)
    tgt = [(r, articles(r.get("관련조항") or "")) for r in rows]
    tgt = [(r, x) for r, x in tgt if x is not None]
    ident = sum(1 for _, x in tgt if x)
    c = collections.Counter(n for _, x in tgt for n in {n for n, _t in x})
    unknown = c.get("판 미상", 0)
    notitle = sum(1 for _, x in tgt if any(not has for _n, has in x))
    print("대상 행 %d / 등급분류규칙 표기 %d / 조 식별 %d / 판 미상 행 %d / 제목 없는 조 인용 행 %d" % (len(rows), len(tgt), ident, unknown, notitle))
    old = sum(1 for r, _ in tgt if not re.search(r"및\s*표시\s*등", r["관련조항"]))
    print("명칭: 현행 %d / 구 명칭(등급분류에 관한 규칙) %d" % (len(tgt) - old, old))
    num = lambda k: int(re.search(r"\d+", k).group()) if re.search(r"\d", k) else 99
    print("조별:", sorted(c.items(), key=lambda kv: (num(kv[0]), kv[0])))
    yr = lambda r: S.year(r)
    print("연도:", sorted(collections.Counter(yr(r) for r, _ in tgt).items(), key=str))
    rc = collections.Counter(S.result_class(r.get("심의결과") or "") for r, _ in tgt)
    print("결과:", dict(rc))
    print("\n조별 결과 분포:")
    dist = collections.defaultdict(collections.Counter)
    for r, x in tgt:
        k = S.result_class(r.get("심의결과") or "")
        for n in {n for n, _t in x}:
            dist[n][k] += 1
    for k in sorted(dist, key=lambda k: (num(k), k)):
        print(" %s %d행: %s" % (k, sum(dist[k].values()), dict(dist[k])))
    if a.article:
        sel = [r for r, x in tgt if any(n == a.article for n, _t in x)]
        print("\n%s %d행" % (a.article, len(sel)))
        print(" 결과:", dict(collections.Counter(S.result_class(r.get("심의결과") or "") for r in sel)))
        print(" 연도:", sorted(collections.Counter(yr(r) for r in sel).items(), key=str))
        if a.rows:
            for r in sel:
                print(" -", r.get("_file"), r.get("순번"), S.case_no(r), S.raw_date(r)[:12].replace("\n", " "), "|",
                      (r.get("방송사/ 프로그램명") or r.get("프로그램명 (방송일시)") or "")[:50].replace("\n", " "), "|",
                      r.get("심의결과"), "|", r["관련조항"][:140].replace("\n", " "))
    if a.verify:
        got = {"rows": len(tgt), "ident": ident, **{k: c.get(k, 0) for k in ("제4조", "제5조", "제3조", "제8조", "제10조", "판 미상")}, **{k: rc.get(k, 0) for k in ("권고", "경고", "주의", "의견제시", "관계자 징계", "기타")}}
        print("\n검증(기본 집계 2012.01~2026.06, --recent 없이 실행):")
        for k, v in VERIFY.items():
            print(" %-8s 기대 %4d 실제 %4d %s" % (k, v, got[k], "OK" if v == got[k] else "불일치"))

if __name__ == "__main__":
    main()
