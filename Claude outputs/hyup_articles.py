# -*- coding: utf-8 -*-
"""
hyup_articles.py v1.0 (2026-09-27, Claude Opus 5.5) — AGENTS.md 7.1 "협찬고지규칙 통계" 기준(v1.13)

목적
  방송심의 의결 내역 통계 CSV에서 「협찬고지 등에 관한 규칙」(구 명칭 「협찬고지에 관한 규칙」, 약칭 협찬고지규칙)
  조문별 적용 행 수와 결과 분포를 집계한다. 읽기·날짜·결과 분류는 stats_articles.py의 함수를 그대로 쓴다.

입력
  stats_articles.py 와 같다(2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일, 선방위 제외).

출력
  표준 출력(텍스트). 파일을 만들지 않는다.

규칙(7.1 협찬고지규칙 통계)
  - 대상 행: 관련조항에 "협찬고지에 관한 규칙" 또는 "협찬고지 등에 관한 규칙"(띄어쓰기·괄호·"(제43호)" 판 표기 변형 허용)이 있는 행.
  - 조문 식별: 규칙명 뒤, 다음 법령명(「·｢로 시작하는 다른 이름, 또는 "방송심의에 관한 규정"·"방송광고심의에") 앞까지의 "제n조"만 센다.
    한 행에 같은 조가 여러 번 나와도 1행. 제16조 이상은 규칙에 없는 번호이므로 세지 않는다(예: 규칙명 뒤에 붙은 "제44조(수용수준)").
  - 표기 예외: "「협찬고지에 관한 규정」제7조(방송의 공정성 및 공공성 유지)"(1행)는 규칙의 오기로 보아 포함한다.
    "* tvN건만 <협찬고지 규칙> 위반임"(1행)처럼 조 번호 없이 적은 메모는 세지 않는다.
  - 판 판별: 조 제목으로 한다. 제1~7조는 구 판(2008.5.19. 제정~2021.9.15.)과 제56호의 조 제목이 같으므로 현행 조에 합산한다.
    구 제8조(지상파텔레비전중앙방송사업자)·제9조(지상파텔레비전지역방송사업자)·제10조(지상파라디오방송사업자)·
    제11조(종합유선방송사업자·위성방송사업자·방송채널사용사업자)·제12~15조는 "구 제n조"로 따로 세고 현행 조에 합산하지 않는다.
    조 제목이 없는 제8조 이상은 "판 미상"으로 센다(방송일·의결일이 모두 2021.9.16. 전이면 구 판으로 본다).
  - 결과 분류: stats_articles.result_class(가장 무거운 조치 하나).
"""
import argparse, collections, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S

NAME_RE = re.compile(r"협찬\s*고지\s*(?:등\s*)?에\s*관한\s*규[칙정]")
OLD_TITLES = {8: "지상파텔레비전중앙방송사업자", 9: "지상파텔레비전지역방송사업자",
              10: "지상파라디오방송사업자", 11: "종합유선방송사업자", 12: "제재조치명령의절차",
              13: "제재조치명령의이행", 14: "자료제출", 15: "재검토"}
ART_RE = re.compile(r"제\s*(\d+)\s*조\s*(?:의\s*\d+)?\s*(\(([^)]*)\)?)?")

def segment(rel):
    m = NAME_RE.search(rel)
    if not m: return None
    s = rel[m.end():]
    n = re.search(r"[「｢]\s*(?!협찬)|방송\s*심의에\s*관한\s*규정|방송광고\s*심의에", s)
    return s[:n.start()] if n else s

def articles(rel):
    s = segment(rel)
    if s is None: return None
    out = set()
    for m in ART_RE.finditer(s):
        no = int(m.group(1)); title = re.sub(r"\s", "", m.group(3) or "")
        if no > 15:
            continue          # 규칙에 없는 조 번호(뒤에 붙은 다른 규정의 조)는 세지 않는다
        if no <= 7:
            out.add("제%d조" % no)
        else:
            old = OLD_TITLES.get(no, "\0")
            if title and (title.startswith(old[:6]) or old.startswith(title[:6])):
                out.add("구 제%d조" % no)
            elif title:
                out.add("제%d조(%s)" % (no, title[:12]))
            else:
                out.add("제%d조(판 미상)" % no)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--article"); ap.add_argument("--rows", action="store_true")
    a = ap.parse_args()
    rows = S.load()
    tgt = [(r, articles(r.get("관련조항") or "")) for r in rows]
    tgt = [(r, arts) for r, arts in tgt if arts is not None]
    print("대상 행 %d / 협찬고지규칙 표기 %d / 조 식별 %d" % (len(rows), len(tgt), sum(1 for _, x in tgt if x)))
    name = collections.Counter("등" if re.search(r"협찬\s*고지\s*등", r["관련조항"]) else "구 명칭" for r, _ in tgt)
    print("명칭:", dict(name))
    c = collections.Counter(x for _, arts in tgt for x in arts)
    print("조별:", sorted(c.items(), key=lambda kv: (kv[0].startswith("구"), int(re.search(r"\d+", kv[0]).group()))))
    def yr(r):
        d = S.decision_date(S.raw_date(r)); return d.year if d else None
    print("연도:", sorted(collections.Counter(yr(r) for r, _ in tgt).items(), key=str))
    print("결과:", dict(collections.Counter(S.result_class(r.get("심의결과") or "") for r, _ in tgt)))
    if a.article:
        sel = [r for r, arts in tgt if a.article in arts]
        print("\n%s %d행" % (a.article, len(sel)))
        print(" 결과:", dict(collections.Counter(S.result_class(r.get("심의결과") or "") for r in sel)))
        print(" 연도:", sorted(collections.Counter(yr(r) for r in sel).items(), key=str))
        print(" 통계부문:", dict(collections.Counter((r.get("통계부문") or "").strip() for r in sel)))
        hang = collections.Counter()
        for r in sel:
            s = segment(r["관련조항"]); no = re.search(r"\d+", a.article).group()
            for m in re.finditer(r"제\s*%s\s*조\s*(?:\([^)]*\)?)?\s*((?:제?\s*\d+\s*항)?\s*(?:제?\s*\d+\s*호)?)" % no, s):
                hang[re.sub(r"\s", "", m.group(1)) or "(항 없음)"] += 1
        print(" 항·호:", hang.most_common())
        if a.rows:
            for r in sel:
                print(" -", r.get("_file"), r.get("순번"), S.raw_date(r)[:40].replace("\n", " "), "|", (r.get("방송사/ 프로그램명") or r.get("프로그램명 (방송일시)") or "")[:40], "|", r.get("심의결과"), "|", r["관련조항"][:150])

if __name__ == "__main__":
    main()
