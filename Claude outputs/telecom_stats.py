#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""통신심의 의결 내역 통계 집계 (AGENTS.md 7.1 "통신심의 통계", registry id stats_telecom)

입력: 2 data_csv/통계_csv/통신/연도별 심의내역 정리/{연도}년 심의의결 내역 정리.csv (2008~2026, 36열)
집계 단위: CSV 행(접수번호 1건). 파일 안 접수번호 중복은 0이다. 파일 사이 중복은 확인하지 않았다.

사용법:
  python telecom_stats.py --verify                      연도별 행 수와 검증값 확인
  python telecom_stats.py --topic 해킹・바이러스           주제 칸이 같은 행을 연도 x 심의결정으로 집계
  python telecom_stats.py --law "통신비밀보호법"          관련법령 칸이 같은 행
  python telecom_stats.py --kw "헌혈증" --years 2012-2014  정보명·키워드·처리비고에서 정규식 검색(마스킹된 행은 못 찾는다)
--topic, --law, --kw 는 함께 주면 모두 만족하는 행만 센다. 정보명·URL·신청자명은 출력하지 않는다.
"""
import argparse, collections, csv, os, re, sys

csv.field_size_limit(10 ** 9)
VAULT = os.environ.get("AI_VAULT", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DIR = os.path.join(VAULT, "2 data_csv", "통계_csv", "통신", "연도별 심의내역 정리")
YEARS = list(range(2008, 2027))
EXPECT_ROWS = {2008: 48638, 2009: 24346, 2010: 45758, 2011: 57944, 2012: 75819, 2013: 110714, 2014: 140421,
               2015: 182912, 2016: 211185, 2017: 91853, 2018: 252166, 2019: 216350, 2020: 226846, 2021: 153085,
               2022: 248130, 2023: 264920, 2024: 356945, 2025: 181892, 2026: 149610}
EXPECT_DECISION = {"시정요구": 2849509, "해당없음": 146676, "시정요구철회": 26746, "각하": 11434}
EXPECT_SEL = {("topic", "해킹・바이러스"): 1059, ("topic", "범죄관련정보"): 491,
              ("law", "정보통신망법 제48조 제1항(해킹)"): 9342, ("law", "통신비밀보호법"): 176, ("law", "도로교통법"): 9042}


def rows(year):
    fn = os.path.join(DIR, "%d년 심의의결 내역 정리.csv" % year)
    with open(fn, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        h = next(r)
        ix = {k: h.index(k) for k in ("정보명", "키워드", "처리비고", "주제", "관련법령", "심의결정")}
        for row in r:
            yield row, ix


def parse_years(s):
    if not s:
        return YEARS
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    ap = argparse.ArgumentParser(description="통신심의 의결 내역 통계 집계(AGENTS.md 7.1)")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--topic")
    ap.add_argument("--law")
    ap.add_argument("--kw")
    ap.add_argument("--years")
    a = ap.parse_args()
    if a.verify:
        tot = 0
        dec = collections.Counter()
        sel = collections.Counter()
        ok = True
        for y in YEARS:
            n = 0
            for row, ix in rows(y):
                n += 1
                dec[row[ix["심의결정"]]] += 1
                sel[("topic", row[ix["주제"]])] += 1
                sel[("law", row[ix["관련법령"]])] += 1
            tot += n
            flag = "OK" if n == EXPECT_ROWS[y] else "불일치(기대 %d)" % EXPECT_ROWS[y]
            ok &= n == EXPECT_ROWS[y]
            print("%d년: %d행 %s" % (y, n, flag))
        print("전체 %d행 (기대 %d)" % (tot, sum(EXPECT_ROWS.values())))
        for k, v in EXPECT_DECISION.items():
            ok &= dec[k] == v
            print("  심의결정 %s: %d (기대 %d)" % (k, dec[k], v))
        for k, v in EXPECT_SEL.items():
            ok &= sel[k] == v
            print("  %s=%s: %d (기대 %d)" % (k[0], k[1], sel[k], v))
        print("검증 결과:", "모두 일치" if ok else "불일치 있음")
        return
    rx = re.compile(a.kw) if a.kw else None
    table = collections.defaultdict(collections.Counter)
    for y in parse_years(a.years):
        for row, ix in rows(y):
            if a.topic and row[ix["주제"]] != a.topic:
                continue
            if a.law and row[ix["관련법령"]] != a.law:
                continue
            if rx and not rx.search(row[ix["정보명"]] + " " + row[ix["키워드"]] + " " + row[ix["처리비고"]]):
                continue
            table[y][row[ix["심의결정"]]] += 1
    decs = sorted({d for c in table.values() for d in c})
    print("연도\t합계\t" + "\t".join(decs))
    for y in sorted(table):
        print("%d\t%d\t" % (y, sum(table[y].values())) + "\t".join(str(table[y][d]) for d in decs))
    print("합계\t%d" % sum(sum(c.values()) for c in table.values()))


if __name__ == "__main__":
    main()
