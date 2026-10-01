# -*- coding: utf-8 -*-
"""
section_stats.py v1.0 (2026-09-23, Claude Opus 5.5)

목적
  방송심의규정 제150호의 절(節) 단위로 통계 CSV 행을 모아 다음을 집계한다.
  ① 절 행 수 ② 절 밖 조문이 함께 적힌 행 수 ③ 특정 조문 행 가운데 그 조문만 적힌 행 비율
  ④ 안건 수 추정: 의결일과 프로그램명이 같은 행을 한 안건으로 묶은 수(같은 날 같은 프로그램의 여러 회차·채널을 하나로 봄)

입력
  stats_articles.py의 load()와 조문 식별(bangsim_articles)을 그대로 쓴다(AGENTS.md 7.1). 대상 2012.01~2026.06, 12,560행.

출력
  표준 출력(텍스트). 파일을 만들지 않는다.

절 구성(제150호 변환본의 절별 조문)
  제5절 소재 및 표현기법: 제35조, 제36조, 제36조의2, 제37조, 제38조, 제38조의2, 제39조, 제40조, 제41조, 제42조, 제42조의2
  제7절 광고효과 등: 제46조, 제46조의2, 제46조의3, 제46조의4, 제47조, 제48조, 제49조, 제50조

프로그램명 추출
  2012~2017 파일: '방송사/ 프로그램명' 칸의 따옴표·꺾쇠 안 문자열, 없으면 첫 단어(채널)를 뺀 나머지.
  2018~ 파일: '프로그램명 (방송일시)' 칸에서 방송일시 앞부분. 공백은 모두 지운 뒤 비교한다.

검증값(2026-09-23 실행)
  제5절 965행(원칙 페이지 4.2절 값과 일치), 절 밖 조문 병합 452행
  제7절 1,816행(원칙 페이지 4.2절 값과 일치), 제46조 1,351행(7.1절 검증값), 제46조만 적힌 행 1,126(83%),
  절 안 조문 가운데 제46조만 적힌 행 1,277(95%), 제7절 안건 추정 1,367건

사용
  python section_stats.py
"""
import re
import stats_articles as S

SECTIONS = {
    "제5절": {"제35조", "제36조", "제36조의2", "제37조", "제38조", "제38조의2", "제39조", "제40조", "제41조", "제42조", "제42조의2"},
    "제7절": {"제46조", "제46조의2", "제46조의3", "제46조의4", "제47조", "제48조", "제49조", "제50조"},
}

def arts(r):
    return set(S.bangsim_articles(r["관련조항"]))

def prog(r):
    if "방송사/ 프로그램명" in r:
        p = r["방송사/ 프로그램명"]
        m = re.search(r"['‘<「](.+?)['’>」]", p)
        p = m.group(1) if m else (p.split(None, 1)[1] if len(p.split(None, 1)) > 1 else p)
    else:
        p = re.split(r"\(\s*\d{4}\.|\d{4}\.\d", r["프로그램명 (방송일시)"])[0]
    return re.sub(r"\s+", "", p)

def agenda_key(r):
    d = S.decision_date(S.raw_date(r))
    return (str(d) if d else "nodate:" + S.case_no(r).rsplit("-", 1)[0], prog(r))

def main():
    R = S.load()
    print("대상 행", len(R))
    for name, sec in SECTIONS.items():
        rows = [r for r in R if arts(r) & sec]
        outside = sum(1 for r in rows if arts(r) - sec)
        print(f"{name}: {len(rows)}행, 절 밖 조문 병합 {outside}행 ({outside / len(rows):.0%}), "
              f"안건 추정 {len({agenda_key(r) for r in rows})}건")
    r46 = [r for r in R if "제46조" in arts(r)]
    only = sum(1 for r in r46 if arts(r) == {"제46조"})
    only_in = sum(1 for r in r46 if arts(r) & SECTIONS["제7절"] == {"제46조"})
    print(f"제46조 {len(r46)}행: 방송심의규정 조문이 제46조뿐 {only} ({only / len(r46):.0%}), "
          f"제7절 안에서 제46조뿐 {only_in} ({only_in / len(r46):.0%})")

if __name__ == "__main__":
    main()
