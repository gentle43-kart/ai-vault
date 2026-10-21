# -*- coding: utf-8 -*-
"""
stats_fill_1217.py v1.1 (2026-10-21, Claude Opus 5.5)
  v1.1: 광고 길이 정정(NAME_FIX) 추가, 기본 출력 경로 지정(2 data_csv/통계_csv/방송/2012-2017 방송심의 통계(보정).csv)

목적
  2012~2017 방송심의 통계 CSV(stats의 12-17_part01~09)의 의결 내용 등 빈칸을 원본 xlsx의 병합 셀 정보로 보정한
  "보정본" CSV 1개를 만든다. 원자료(CSV·xlsx)는 읽기만 한다. 배경: 0 wiki/분석/2026-09-22 해설집 사례와 통계 활용 원칙 3.2절.

입력
  - 2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/12-17_part01~09.csv (stats_articles._read로 읽음, 6,136행)
  - 3 source_raw/통계_raw/2012-2017 방송심의 통계.xlsx (첫 시트, 머리글 5행, 데이터 6~6141행)
  두 자료는 행 순서가 같아야 한다. 의결일/의결번호·방송사/프로그램명·심의결과(공백 제거)가 한 행이라도 다르면 중단한다.

출력 (--out 경로, 없으면 요약만 출력)
  CSV(utf-8-sig). 1행 제목, 2행 머리글(stats_articles._read가 "순번" 행을 머리글로 찾음).
  열: 원래 11개 열(보정값 반영) + 원본 파일, 의결 내용(원본), 방송사/ 프로그램명(원본), 관련조항(원본), 보정 근거, 보정 출처
  보정 근거 값:
    병합      원본 xlsx 병합 범위 안의 빈 셀 → 범위 첫 셀 값으로 채움 (의결 내용·방송사/프로그램명·관련조항)
    상동        "상동"만 적힌 의결 내용 → 바로 앞쪽에서 가장 가까운 실제 내용으로 채움.
                조건(모두): 그 행과 관련조항·심의결과가 같고(공백 무시), 같은 회의(의결일, 없으면 의결번호의 연도·구분·회차)이며,
                방송사/프로그램명에 두 글자 이상 같은 낱말이 있거나, 의결일이 같거나,
                의결번호 일련번호가 앞 행부터 행 간격만큼 이어지는 경우(채널명만 적힌 행)
    묶음        병합되지 않은 빈 의결 내용 → "상동"과 같은 조건이면 채움(원본 작성자가 병합하지 않은 묶음 반복 행)
    회의록      위 조건을 채우지 못한 "상동" 행 가운데 광고소위 회의록으로 안건 내용을 확인한 행 → 회의록 사무처 보고 요지로 채움
                (MINUTES 표. 2016.7.27. 제26차 13행)
    길이 정정   방송사/프로그램명의 광고 길이를 회의록·사용자 확인으로 고침(NAME_FIX 표. 2016-광고-26-0395·0396 코웨이 정수기
                "(30초)" → "(15초)": 회의록은 7건 모두 15초, 사용자 확인 2026-10-21)
    상동(확인)  "상동"이지만 위 조건을 채우지 못하고 회의록 확인도 없음 → 채우지 않고 "상동" 그대로 둠(검토 목록)
    원본 빈칸   병합되지 않은 빈칸이고 위 조건을 채우지 못함 → 채우지 않음(검토 목록)
  보정 출처: 값을 가져온 행의 "xlsx 행 번호 / 의결일·의결번호 칸 값", 회의록이면 파일·줄
  (원본) 열에는 값을 바꾼 행만 원래 값을 적는다(바꾸지 않은 행은 빈칸)
  --review 경로를 주면 "상동(확인)"과 "원본 빈칸" 행의 검토 목록 CSV를 따로 쓴다(앞뒤 내용 있는 행 요약 포함).

검증(실행 때 출력)
  행 수 6,136, 원본 일치 0건 불일치, 병합 범위 201개, 의결 내용 병합 빈칸 668, 비병합 빈칸 63, "상동" 252 (2026-10-21 측정값)
  보정 뒤 조문별 행 수(stats_articles.bangsim_articles·ad_articles.ad_articles)를 보정 전과 비교해 출력한다.

사용
  python stats_fill_1217.py                          # 요약·검증만
  python stats_fill_1217.py --out <보정본.csv> --review <검토목록.csv>
"""
import argparse, csv, collections, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S, ad_articles as A
import openpyxl

XLSX = os.path.join(S.VAULT, "3 source_raw", "통계_raw", "2012-2017 방송심의 통계.xlsx")
COLS = ["순번", "의결일/ 의결번호/ 심의부문", "방송사/ 프로그램명", "방송일시", "의결 내용", "관련조항", "심의결과", "통계부문", "인지방법", "부서", ""]
FILL_COLS = {"의결 내용": 5, "방송사/ 프로그램명": 3, "관련조항": 6}   # xlsx 열 번호(1부터)
HDR, FIRST = 5, 6
_SD = re.compile(r"\s*(상동|동일|위와\s*같음|〃)\s*\W*\s*")
def n(s): return re.sub(r"\s+", "", s or "")
_M16 = "1 documents_md/회의록_md/광고소위_md/연도별 광고소위 회의록 md파일 원본_md/2016년 광고소위 회의록.md"
_NOTE = "[회의록 사무처 보고 요지, 광고소위 2016.7.27. 제26차] "
MINUTES = {}
for a, b, line, txt in [
    (377, 379, 32062, "젊은 청년이 홀로 침대에 누워 있는 영상과 함께 '지금이 아니면 살릴 수 없습니다' 등의 멘트가 나오면서 청소년의 눈에서 눈물이 떨어지고 '삐' 소리와 함께 사망을 암시하는 장면은 노동개혁이 아니면 청년이 자살할 수 있다는 잘못된 메시지를 전달할 우려가 있다는 민원. 관련조항은 「방송광고심의에 관한 규정」 제4조(품위등)제3호, 제7조(음향·화면)제3호. 소위 결정: 의견제시"),
    (380, 382, 32202, "고통스러워하며 사경을 헤매는 아들의 모습과 그 옆에서 간병하는 어머니의 모습을 사실적으로 보여주는 것은 유가족에게 안타깝고 슬펐던 기억을 다시 떠오르게 한다는 민원. 관련조항은 「방송광고심의에 관한 규정」 제4조(품위등)제10호. 소위 결정: 문제없음"),
    (390, 396, 32286, "어린이가 보는 앞에서 사람에게 물을 끼얹은 장면 등이 폭력적이며 고부관계를 대립적으로 묘사한 것 역시 여성에 대한 부정적인 면만을 강조했다는 민원. 적용조항은 「방송광고심의에 관한 규정」 제4조(품위등)제10호. 소위 결정: 문제없음")]:
    for k in range(a, b + 1):
        MINUTES[("2016", "광고", 26, k)] = (_NOTE + txt, f"{_M16} {line}행(회의록 번호 표기 제2016-광고-25-{a:04d}~{b:04d}호)")
def blank(s): return not (s or "").strip()
OUT_DEFAULT = os.path.join(S.VAULT, "2 data_csv", "통계_csv", "방송", "2012-2017 방송심의 통계(보정).csv")
NAME_FIX = {("2016", "광고", 26, 395): ("(30초)", "(15초)"), ("2016", "광고", 26, 396): ("(30초)", "(15초)")}
# 의결일·의결번호는 이 파일 안에서 따로 읽는다(stats_articles.case_no는 "2016-17-0269"의 앞 "2016-17-02"를 날짜로 지워
# 번호를 못 읽는 문제가 있음, 2026-10-21 확인). 날짜는 뒤에 숫자가 붙지 않는 연-월-일만 인정한다.
_DATE = re.compile(r"^\s*(\d{4})\s*[-.]\s*(\d{1,2})\s*[-.]\s*(\d{1,2})(?!\d)|^\s*(\d{2})\.\s*(\d{1,2})\.\s*(\d{1,2})(?!\d)")
_CNO = re.compile(r"(\d{4})\s*-\s*(방송\s*-\s*|광고\s*-\s*)?(\d{1,2})\s*-\s*(\d{3,4})(?!\d)")
def _raw(r): return r.get(COLS[1]) or ""
def _date(r):
    m = _DATE.match(_raw(r))
    if not m: return None
    g = [x for x in m.groups() if x is not None]; y, mo, d = map(int, g); y += 2000 if y < 100 else 0
    return (y, mo, d)
def _case(r):
    v = _raw(r); m0 = _DATE.match(v); v = v[m0.end():] if m0 else v
    return _CNO.search(v)
def meeting(r):
    d = _date(r)
    if d: return ("d", d)
    m = _case(r)
    return ("c", m.group(1), re.sub(r"\W", "", m.group(2) or ""), int(m.group(3))) if m else None
def words(s): return set(re.findall(r"[가-힣A-Za-z0-9]{2,}", re.sub(r"\(\d+[초분]\)", "", s or "")))
def serial(r):
    m = _case(r); return int(m.group(4)) if m else None
def same_group(p, r, gap):
    """r(빈칸·상동 행)이 p(내용 있는 앞 행, gap행 앞)와 같은 안건 묶음인지."""
    if n(p["관련조항"]) != n(r["관련조항"]) or n(p["심의결과"]) != n(r["심의결과"]): return False
    mp, mr = meeting(p), meeting(r)
    if not mp or mp != mr: return False
    if words(p[COLS[2]]) & words(r[COLS[2]]) or mp[0] == "d": return True
    sp, sr = serial(p), serial(r)
    return sp is not None and sr is not None and sr - sp == gap

def build():
    C = [r for r in S.load(False, split=True) if r["_file"].startswith("12-17")]
    ws = openpyxl.load_workbook(XLSX).worksheets[0]
    X = [[("" if c.value is None else str(c.value)) for c in ws[r]][:11] for r in range(FIRST, ws.max_row + 1)]
    assert len(C) == len(X) == 6136, (len(C), len(X))
    bad = [i for i, (x, c) in enumerate(zip(X, C)) if n(x[1]) != n(c[COLS[1]]) or n(x[2]) != n(c[COLS[2]]) or n(x[6]) != n(c[COLS[6]])]
    assert not bad, f"원본 xlsx와 CSV 행 불일치 {len(bad)}건(첫 {bad[:3]})"
    top = {}   # (xlsx row, col) -> 병합 첫 셀 xlsx row
    for m in ws.merged_cells.ranges:
        for rr in range(m.min_row + 1, m.max_row + 1):
            for cc in range(m.min_col, m.max_col + 1):
                top[(rr, cc)] = m.min_row
    out, stat = [], collections.Counter()
    for i, c in enumerate(C):
        xr = FIRST + i
        row = {k: c.get(k, "") for k in COLS}
        orig = {k: row[k] for k in FILL_COLS}
        why, src = [], []
        for k, cc in FILL_COLS.items():
            if blank(row[k]) and (xr, cc) in top:
                t = top[(xr, cc)]; row[k] = C[t - FIRST].get(k, "")
                why.append("병합" if k == "의결 내용" else f"병합({k})"); src.append(f"{t} / {C[t - FIRST][COLS[1]].strip()}")
                stat["병합:" + k] += 1
        out.append([row, orig, why, src, c["_file"]])
    # 상동·비병합 빈칸 (병합 채움 뒤 값 기준). 앞 행은 원본 값(채우기 전)으로 판단해 연쇄 채움을 막는다
    real = [not blank(o[0]["의결 내용"]) and not _SD.fullmatch(o[0]["의결 내용"]) for o in out]
    for i, (row, orig, why, src, f) in enumerate(out):
        body = row["의결 내용"]
        sd, bl = bool(_SD.fullmatch(body or "")), blank(body)
        if not (sd or bl): continue
        j = i - 1
        while j >= 0 and not real[j]: j -= 1
        p = out[j][0] if j >= 0 else None
        if p is not None and same_group(p, row, i - j):
            row["의결 내용"] = p["의결 내용"]; tag = "상동" if sd else "묶음"
            src.append(f"{FIRST + j} / {p[COLS[1]].strip()}")
        else:
            m = _case(row); key = (m.group(1), re.sub(r"\W", "", m.group(2) or ""), int(m.group(3)), int(m.group(4))) if m else None
            if sd and key in MINUTES:
                row["의결 내용"], ms = MINUTES[key]; tag = "회의록"; src.append(ms)
            else:
                tag = "상동(확인)" if sd else "원본 빈칸"
        why.append(tag); stat[tag] += 1
    for row, orig, why, src, f in out:
        m = _case(row); key = (m.group(1), re.sub(r"\W", "", m.group(2) or ""), int(m.group(3)), int(m.group(4))) if m else None
        if key in NAME_FIX and NAME_FIX[key][0] in row[COLS[2]]:
            row[COLS[2]] = row[COLS[2]].replace(*NAME_FIX[key]); why.append("길이 정정")
            src.append("2016년 광고소위 회의록 32286행(7건 모두 15초), 사용자 확인 2026-10-21"); stat["길이 정정"] += 1
    return C, out, stat, len(ws.merged_cells.ranges)

def counts(rows):
    b, a = collections.Counter(), collections.Counter()
    for r in rows:
        for k in S.bangsim_articles(r.get("관련조항", "")): b[k] += 1
        for k in A.ad_articles(r.get("관련조항", "")): a[k] += 1
    return b, a

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--review"); a = ap.parse_args()
    C, out, stat, nm = build()
    print("행", len(out), "/ 병합 범위", nm, "/", dict(stat))
    b0, a0 = counts(C); b1, a1 = counts([o[0] for o in out])
    print("조문 행 수 변화(방송심의):", {k: (b0[k], b1[k]) for k in set(b0) | set(b1) if b0[k] != b1[k]})
    print("조문 행 수 변화(광고심의):", {k: (a0[k], a1[k]) for k in set(a0) | set(a1) if a0[k] != a1[k]})
    if a.out:
        with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["2012-2017년 방송심의 의결 내역(보정본: 원본 xlsx 병합 셀·상동 보정, stats_fill_1217.py v1.0)"])
            w.writerow(COLS + ["원본 파일", "의결 내용(원본)", "방송사/ 프로그램명(원본)", "관련조항(원본)", "보정 근거", "보정 출처"])
            for row, orig, why, src, f in out:
                o = [orig[k] if orig[k] != row[k] else "" for k in ("의결 내용", "방송사/ 프로그램명", "관련조항")]
                w.writerow([row[k] for k in COLS] + [f] + o + ["; ".join(why), "; ".join(src)])
        print("보정본:", a.out)
    if a.review:
        with open(a.review, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["xlsx 행", "원본 파일", "순번", "의결일/ 의결번호", "방송사/ 프로그램명", "관련조항", "심의결과", "통계부문", "보정 근거", "채운 내용(앞 80자)", "보정 출처", "바로 앞 내용 있는 행(의결번호 / 앞 60자)", "바로 뒤 내용 있는 행(의결번호 / 앞 60자)"])
            for i, (row, orig, why, src, f) in enumerate(out):
                if not any(x in ("상동(확인)", "원본 빈칸", "묶음", "회의록") for x in why): continue
                def near(rng):
                    for j in rng:
                        v = out[j][0]["의결 내용"]
                        if not blank(v) and not _SD.fullmatch(v): return f"{out[j][0][COLS[1]].strip()[:30]} / {re.sub(chr(10), ' ', v)[:60]}"
                    return ""
                w.writerow([FIRST + i, f, row["순번"], row[COLS[1]].strip(), row[COLS[2]].strip(), row["관련조항"].strip(), row["심의결과"].strip(), row["통계부문"].strip(),
                            "; ".join(why), re.sub(r"\s+", " ", row["의결 내용"])[:80] if ("묶음" in why or "회의록" in why) else "", "; ".join(src),
                            near(range(i - 1, max(-1, i - 40), -1)), near(range(i + 1, min(len(out), i + 40)))])
        print("검토 목록:", a.review)

if __name__ == "__main__":
    main()
