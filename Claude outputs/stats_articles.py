# -*- coding: utf-8 -*-
"""
stats_articles.py v1.1 (2026-09-22, Claude Opus 5)
  v1.1: '조' 누락 표기(제n의m) 예외 규칙 추가

목적
  방송심의 의결 내역 통계 CSV에서 「방송심의에 관한 규정」 조문별 적용 행 수, 결과 분포,
  위원회 기수별 분포를 집계한다. AGENTS.md 7.1절(통계 CSV 대조 기준)을 코드로 옮긴 것이다.

입력
  2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일(12-17_*, 18-25_*, 26.01-06.csv).
  선방위_* 파일은 뺀다. --recent 를 주면 2 data_csv/통계_csv/방송/쳇지피팅용 병합_csv/△26.01.-08.csv 의
  2026.07~08 행만 추가한다(registry stats_2026_recent, period_use).

출력
  표준 출력(텍스트). 집계 결과 파일은 만들지 않는다(AGENTS.md 2절).

규칙(7.1절)
  - 집계 단위: CSV 행. 한 행에 같은 조가 여러 번 나와도 1행.
  - 조문 식별: 관련조항에서 「방송심의에 관한 규정」 뒤, 다음 법령명 앞까지의 "제n조(의m)"만 센다.
    「상품소개 및 판매방송 심의에 관한 규정」·「방송광고심의에 관한 규정」·「선거방송심의에 관한 특별규정」은 제외.
    괄호 ｢｣, 여는 괄호 누락, 공백 차이를 허용한다. 괄호 안(조 제목, 판 표기)의 "…법"은 법령명으로 보지 않는다.
  - 결과 분류: 한 행에 여러 조치가 있으면 가장 무거운 것으로 분류.
    과징금 > 프로그램 중지 > 관계자 징계 > 시청자에 대한 사과 > 경고 > 주의 > 권고 > 의견제시 > 문제없음 (그 밖: 기타, 예: 각하)
    "주의 이상" = 주의·경고·관계자 징계·시청자에 대한 사과·프로그램 중지·과징금.
  - 의결일: CSV 표기 기준. 문자열 맨 앞의 날짜만 인정(YYYY-MM-DD, YYYY.M.D., YY. M. D.). 의결번호를 날짜로 읽지 않는다.
  - 기수 경계(근사값, 원칙 페이지 3.1절): 제3기 2014-06-01, 제4기 2018-01-01, 제5기 2021-07-01,
    제6기 2024-07-23, 방미심위 제1기 2026-01-01.
  - 판 구분: 조 제목을 함께 출력한다(--article 사용 시). 조 번호만으로 판을 가로질러 합산하지 말 것.

알려진 예외(엄격 해석으로 집계에서 빠짐)
  - 법령명 없이 조문만 적힌 3행(어느 규정인지 알 수 없어 뺀다)
  예외 규칙: "제45의2"처럼 '조'가 빠진 표기는 제45조의2로 읽는다(v1.1, 사용자 결정 2026-09-22). 2012.01~2026.06 기준 2행
  (--verify 가 행 수를 보고한다)

검증값(대상 2012.01~2026.06, --recent 없이, 12,560행)
  조문별 행: 제46조 1,351 / 제44조 760 / 제27조 777 / 제14조 1,117 / 제9조 332
  의결일 미식별 1,135행
  기수별(의결일 있음, 문제없음 제외) 의결 행·주의 이상: 제2기 2,155·951 / 제3기 2,347·773 / 제4기 2,984·654 /
  제5기 2,251·399 / 제6기 368·73 / 방미심위 제1기 165·24
  2026-09-22 기기에서 실행해 모두 일치 확인.

사용
  python stats_articles.py --verify
  python stats_articles.py --article 제46조 [--recent]
  python stats_articles.py --top 30
"""
import argparse
import collections
import csv
import datetime
import glob
import os
import re
import sys

VAULT = os.environ.get("AI_VAULT", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STATS_DIR = os.path.join(VAULT, "2 data_csv", "통계_csv", "방송", "제미나이 노트북용 분할_csv")
RECENT = os.path.join(VAULT, "2 data_csv", "통계_csv", "방송", "쳇지피팅용 병합_csv", "△26.01.-08.csv")

# ── 읽기 ────────────────────────────────────────────────
def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    h = next(i for i, r in enumerate(rows[:8]) if r and r[0].strip() == "순번")
    hdr = [c.replace("\n", " ").strip() for c in rows[h]]
    for r in rows[h + 1:]:
        d = dict(zip(hdr, r))
        d["_file"] = os.path.basename(path)
        yield d

def load(recent=False):
    out = []
    for p in sorted(glob.glob(os.path.join(STATS_DIR, "*.csv"))):
        if os.path.basename(p).startswith("선방위"):
            continue
        out.extend(_read(p))
    if recent:
        for d in _read(RECENT):
            dd = decision_date(raw_date(d))
            if dd and datetime.date(2026, 7, 1) <= dd <= datetime.date(2026, 8, 31):
                out.append(d)
    return out

def raw_date(r):
    return r.get("의결일/ 의결번호/ 심의부문") or r.get("의결일", "")

# ── 의결일·의결번호 ──────────────────────────────────────
_DP = [re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?=\s|$)"),
       re.compile(r"^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?(?=\s|$)"),
       re.compile(r"^(\d{2})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?(?=\s|$)")]

def decision_date(v):
    v = (v or "").strip()
    for p in _DP:
        m = p.match(v)
        if m:
            y, mo, d = map(int, m.groups())
            if y < 100:
                y += 2000
            try:
                return datetime.date(y, mo, d)
            except ValueError:
                return None
    return None

_CASE = re.compile(r"제?\s*(\d{4})\s*-\s*(?:(방송|광고)\s*-\s*)?(\d{1,2})\s*-\s*(\d{3,4})")

def case_no(r):
    """의결번호를 'YYYY-(방송|광고-)?NN-NNNN' 형태로 정규화. 행 식별은 의결일+의결번호(7.1)."""
    v = r.get("의결번호") or raw_date(r)
    v = re.sub(r"^\s*\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?", "", v) if not r.get("의결번호") else v
    m = _CASE.search(v)
    if not m:
        return ""
    y, k, a, b = m.groups()
    return f"{y}-{k + '-' if k else ''}{int(a):02d}-{int(b):04d}"

def year(r):
    d = decision_date(raw_date(r))
    if d:
        return d.year
    c = case_no(r)
    return int(c[:4]) if c else None

# ── 조문 식별 ────────────────────────────────────────────
_LAW = re.compile(r"(상품소개및판매방송심의에관한(?:규정|규칙)|방송광고심의에관한규정|선거방송심의에관한특별규정"
                  r"|방송심의에관한규정|방송심의규정|협찬고지(?:등)?에관한(?:규칙|규정)"
                  r"|방송프로그램의등급분류[가-힣]*?규칙|[가-힣]+법(?:시행령|시행규칙)?)")
# "제45의2"처럼 '조'가 빠진 표기도 제45조의2로 읽는다(사용자 결정 2026-09-22). 원자료는 고치지 않는다.
_ART = re.compile(r"제(\d+)(?:조(?:의(\d+))?|의(\d+))(?:\(([^)]*)\))?")
_TARGET = ("방송심의에관한규정", "방송심의규정")

def _norm(s):
    for a, b in (("｢", "「"), ("｣", "」"), ("〈", "<"), ("〉", ">"), ("（", "("), ("）", ")")):
        s = s.replace(a, b)
    return re.sub(r"\s+", "", s)

def _depth(s):
    d, out = 0, []
    for ch in s:
        if ch in "(<":
            d += 1
        out.append(d)
        if ch in ")>":
            d = max(0, d - 1)
    return out

def bangsim_articles(text):
    """관련조항 → {'제46조': '광고효과', ...} (「방송심의에 관한 규정」 조문만, 조 제목은 처음 나온 것)"""
    s = _norm(text or "")
    dm = _depth(s)
    laws = [m for m in _LAW.finditer(s) if dm[m.start()] == 0]
    res = {}
    for i, m in enumerate(laws):
        if m.group(1) not in _TARGET:
            continue
        seg = s[m.end():laws[i + 1].start() if i + 1 < len(laws) else len(s)]
        for a in _ART.finditer(seg):
            sub = a.group(2) or a.group(3)
            k = f"제{a.group(1)}조" + (f"의{sub}" if sub else "")
            res.setdefault(k, a.group(4) or "")
    return res

# ── 결과·기수 ───────────────────────────────────────────
_SEV = [("과징금", "과징금"), ("중지", "프로그램 중지"), ("징계", "관계자 징계"), ("사과", "시청자에 대한 사과"),
        ("경고", "경고"), ("주의", "주의"), ("권고", "권고"), ("의견제시", "의견제시"), ("문제없음", "문제없음")]
ORDER = [v for _, v in _SEV] + ["기타"]
HIGH = {"과징금", "프로그램 중지", "관계자 징계", "시청자에 대한 사과", "경고", "주의"}

def result_class(s):
    s = re.sub(r"\s+", "", s or "")
    for k, v in _SEV:
        if k in s:
            return v
    return "기타"

_GI = [(datetime.date(2014, 6, 1), "제2기"), (datetime.date(2018, 1, 1), "제3기"), (datetime.date(2021, 7, 1), "제4기"),
       (datetime.date(2024, 7, 23), "제5기"), (datetime.date(2026, 1, 1), "제6기"), (datetime.date(2100, 1, 1), "방미심위 제1기")]
GI_ORDER = [n for _, n in _GI]

def gisu(d):
    if not d:
        return None
    for b, n in _GI:
        if d < b:
            return n

# ── 명령 ────────────────────────────────────────────────
VERIFY = {"제46조": 1351, "제44조": 760, "제27조": 777, "제14조": 1117, "제9조": 332}
VERIFY_GI = {"제2기": (2155, 951), "제3기": (2347, 773), "제4기": (2984, 654), "제5기": (2251, 399),
             "제6기": (368, 73), "방미심위 제1기": (165, 24)}

def cmd_verify(R):
    ok = True
    print(f"대상 행: {len(R):,} (기대 12,560)")
    ok &= len(R) == 12560
    c = collections.Counter(k for r in R for k in bangsim_articles(r["관련조항"]))
    for k, v in VERIFY.items():
        print(f"  {k}: {c[k]:,} (기대 {v:,}) {'OK' if c[k] == v else '불일치'}")
        ok &= c[k] == v
    nod = sum(1 for r in R if not decision_date(raw_date(r)))
    print(f"의결일 미식별: {nod:,} (기대 1,135) {'OK' if nod == 1135 else '불일치'}")
    ok &= nod == 1135
    t = collections.defaultdict(lambda: [0, 0])
    for r in R:
        d, rc = decision_date(raw_date(r)), result_class(r["심의결과"])
        if d and rc != "문제없음":
            g = gisu(d); t[g][0] += 1; t[g][1] += rc in HIGH
    for g, (a, b) in VERIFY_GI.items():
        print(f"  {g}: {t[g][0]:,}행, 주의 이상 {t[g][1]:,} (기대 {a:,}·{b:,}) {'OK' if tuple(t[g]) == (a, b) else '불일치'}")
        ok &= tuple(t[g]) == (a, b)
    ex1 = sum(1 for r in R if re.search(r"제\d+의\d+", _norm(r["관련조항"])) and bangsim_articles(r["관련조항"]))
    ex2 = sum(1 for r in R if re.search(r"제\d+조", r["관련조항"]) and not _LAW.search(_norm(r["관련조항"])))
    print(f"예외 처리: '조' 누락 표기를 조로 읽은 행 {ex1}행(포함) / 법령명 없음 {ex2}행(제외)")
    print("검증 결과:", "모두 일치" if ok else "불일치 있음 — 스크립트를 사용하지 말 것")
    return 0 if ok else 1

def cmd_article(R, art):
    rows = [(r, bangsim_articles(r["관련조항"])) for r in R]
    rows = [(r, a) for r, a in rows if art in a]
    print(f"{art}: {len(rows):,}행")
    print("결과 분포:", ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(result_class(r['심의결과']) for r, _ in rows).items(), key=lambda x: ORDER.index(x[0]))))
    hi = sum(result_class(r["심의결과"]) in HIGH for r, _ in rows)
    nz = sum(result_class(r["심의결과"]) != "문제없음" for r, _ in rows)
    print(f"주의 이상: {hi:,} / 문제없음 제외 {nz:,} ({100 * hi / nz:.0f}%)" if nz else "주의 이상: 0")
    print("조 제목(판 구분용):", dict(collections.Counter(a[art] for _, a in rows).most_common()))
    print("연도별:", dict(sorted(collections.Counter(year(r) for r, _ in rows).items(), key=lambda x: (x[0] is None, x[0] or 0))))
    t = collections.defaultdict(lambda: [0, 0])
    for r, _ in rows:
        g = gisu(decision_date(raw_date(r))) or "의결일 없음"
        rc = result_class(r["심의결과"])
        if rc != "문제없음":
            t[g][0] += 1; t[g][1] += rc in HIGH
    print("기수별(문제없음 제외, 행·주의 이상):", {g: tuple(t[g]) for g in GI_ORDER + ["의결일 없음"] if g in t})

def main():
    ap = argparse.ArgumentParser(description="방송심의 통계 CSV 조문별 집계(AGENTS.md 7.1)")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--article", help="예: 제46조, 제55조의2")
    ap.add_argument("--top", type=int, help="조문별 행 수 상위 N")
    ap.add_argument("--recent", action="store_true", help="2026.07~08 행 추가(stats_2026_recent)")
    a = ap.parse_args()
    if a.verify and a.recent:
        sys.exit("--verify 는 --recent 없이 실행한다(검증값은 2012.01~2026.06 기준)")
    R = load(a.recent)
    if a.recent:
        print(f"※ stats_2026_recent 2026.07~08 행 추가: 대상 {len(R):,}행")
    if a.verify:
        sys.exit(cmd_verify(R))
    if a.article:
        cmd_article(R, a.article)
    if a.top:
        c = collections.Counter(k for r in R for k in bangsim_articles(r["관련조항"]))
        for k, v in c.most_common(a.top):
            print(f"{k}\t{v}")
    if not (a.article or a.top):
        ap.print_help()

if __name__ == "__main__":
    main()
