# -*- coding: utf-8 -*-
"""search.db 점검 (읽기 전용). 사용법: python check_index.py"""
import os
import sqlite3

db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "search.db")
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
q = lambda s: c.execute(s).fetchall()

print("1) 회의록·법령 조각 중 의결번호가 붙은 비율")
for reg, n, k in q("""SELECT d.registry_id, COUNT(*), COUNT(c.case_no) FROM chunks c
                     JOIN documents d ON d.doc_id=c.doc_id WHERE c.kind='text'
                     GROUP BY 1 ORDER BY 1"""):
    print(f"   {reg:28s} {k:>7,} / {n:>7,} ({k/n:.0%})")

print("\n2) 통계 행 중 회의록과 의결번호로 연결되는 비율 (연도별)")
for y, n, k in q("""SELECT substr(decision_date,1,4) y, COUNT(*),
                      SUM(EXISTS(SELECT 1 FROM chunks c WHERE c.kind='text' AND c.case_prefix=d.case_prefix
                               AND d.case_num BETWEEN c.num_from AND c.num_to))
                    FROM decisions d GROUP BY y ORDER BY y"""):
    print(f"   {y or '날짜없음':8s} {k:>6,} / {n:>6,} ({k/n:.0%})")

print("\n3) 의결번호 표기 형태 (통계, 상위 8개)")
for pat, n in q("""SELECT CASE
          WHEN case_no IS NULL OR case_no='' THEN '(없음)'
          WHEN case_prefix GLOB '[0-9][0-9][0-9][0-9]-[0-9]*' THEN 'YYYY-NN-NNNN (전체회의 등, 부문 없음)'
          ELSE 'YYYY-' || substr(case_prefix,6, instr(substr(case_prefix,6),'-')-1) || '-NN-NNNN' END p, COUNT(*)
        FROM decisions GROUP BY p ORDER BY 2 DESC LIMIT 8"""):
    print(f"   {pat:32s} {n:>7,}")
