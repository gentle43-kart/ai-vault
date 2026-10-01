# -*- coding: utf-8 -*-
"""
sanction_results.py v1.0 (2026-09-25, Claude Opus 5.5)

목적
  방송심의 의결 내역 통계 CSV 전체(방송·광고 심의 포함)의 결과 분포를 방송법 제100조의 조치 유형별로 집계한다.
  위키 [[방송법 제100조]] 5절의 수치 근거. 결과 분류·대상 범위·의결일 해석은 stats_articles.py(AGENTS.md 7.1)를 그대로 쓴다.

입력
  2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일(12-17_*, 18-25_*, 26.01-06.csv). 선방위_* 제외.

출력
  표준 출력(텍스트). 결과 파일은 만들지 않는다.

규칙
  - 집계 단위: CSV 행. 한 행의 결과는 가장 무거운 조치 하나로 분류(stats_articles.result_class).
  - "프로그램 중지" 분류는 결과 문자열에 "중지"가 들어간 행이다(방송광고 중지 포함). "해당 방송광고의 수정"처럼
    "중지" 없이 정정·수정만 적힌 행은 "기타"로 떨어진다(v1.0 기준 1행).
  - CSV에는 과징금의 근거 항(제1항 본문 / 제3항)이 적혀 있지 않으므로 항별로 나누지 않는다.
  - 연도: 의결일(CSV 표기)을 우선하고, 없으면 의결번호의 연도(stats_articles.year).

검증값(대상 2012.01~2026.06, 12,560행)
  과징금 73 / 프로그램 중지 59 / 관계자 징계 223 / 시청자에 대한 사과 18 / 경고 807 / 주의 1,932 /
  권고 6,320 / 의견제시 1,815 / 문제없음 1,301 / 기타 12(각하 10 포함)
  시청자에 대한 사과 18행은 모두 2012년이고, 의결일이 2012-08-03 이후인 행은 0이다.
  stats_articles.py --verify 가 먼저 통과해야 한다. 2026-09-25 기기에서 실행해 일치 확인.

사용
  python sanction_results.py
"""
import collections
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S  # noqa: E402

EXPECT = {"과징금": 73, "프로그램 중지": 59, "관계자 징계": 223, "시청자에 대한 사과": 18, "경고": 807, "주의": 1932,
          "권고": 6320, "의견제시": 1815, "문제없음": 1301, "기타": 12}
MAP = {"과징금": "제1항 본문·제3항(과징금)", "프로그램 중지": "제1항 제2호(정정·수정·중지)",
       "관계자 징계": "제1항 제3호(징계)", "시청자에 대한 사과": "구 제1항 제1호(2013.3.23. 삭제)",
       "경고": "제1항 제4호(주의 또는 경고)", "주의": "제1항 제4호(주의 또는 경고)",
       "권고": "제1항 단서(권고)", "의견제시": "제1항 단서(의견제시)", "문제없음": "-", "기타": "-"}


def main():
    R = S.load(False)
    ok = len(R) == 12560
    print(f"대상 행: {len(R):,} (기대 12,560)")
    c = collections.Counter(S.result_class(r["심의결과"]) for r in R)
    for k in S.ORDER:
        flag = "OK" if c[k] == EXPECT[k] else "불일치"
        ok &= c[k] == EXPECT[k]
        print(f"  {k}\t{c[k]:,}\t{MAP[k]}\t(기대 {EXPECT[k]:,}) {flag}")
    print("기타 내역:", collections.Counter(re.sub(r"\s+", " ", r["심의결과"])[:30]
                                        for r in R if S.result_class(r["심의결과"]) == "기타").most_common())
    for cls in ("과징금", "프로그램 중지", "관계자 징계", "시청자에 대한 사과"):
        y = collections.Counter(S.year(r) for r in R if S.result_class(r["심의결과"]) == cls)
        print(f"{cls} 연도별:", dict(sorted(y.items(), key=lambda x: (x[0] is None, x[0] or 0))))
    late = sum(1 for r in R if S.result_class(r["심의결과"]) == "시청자에 대한 사과"
               and (S.decision_date(S.raw_date(r)) or datetime.date(2000, 1, 1)) >= datetime.date(2012, 8, 3))
    print(f"시청자에 대한 사과 중 의결일 2012-08-03 이후: {late} (기대 0) {'OK' if late == 0 else '불일치'}")
    ok &= late == 0
    print("검증 결과:", "모두 일치" if ok else "불일치 있음 — 수치를 쓰지 말 것")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
