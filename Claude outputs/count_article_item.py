# -*- coding: utf-8 -*-
"""
count_article_item.py v1.0 (2026-09-23, Claude Opus 5.5)

목적
  통계 CSV에서 「방송심의에 관한 규정」 특정 조의 특정 호(또는 항)가 관련조항에 적힌 행을 뽑는다.
  stats_articles.py는 조 단위로만 집계하므로, 호·항 단위 확인이 필요할 때 보조로 쓴다.
  조문 식별(규정명 구간, 조 표기, 괄호 깊이)은 stats_articles.py의 함수를 그대로 가져다 쓴다.

입력
  stats_articles.load()와 같다: 2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일(선방위_* 제외).
  인자: --article 27 --item 4 (호) 또는 --para 2 (항). 조의m은 --sub m.

출력
  표준 출력: 해당 행 목록(파일, 순번, 의결일, 방송일, 방송사·프로그램, 심의결과)과 행 수. 결과 파일은 만들지 않는다(AGENTS.md 2절).

규칙
  - 「방송심의에 관한 규정」 구간 안에서 해당 조 표기 뒤, 다음 조 표기 앞까지에 "제K호"(또는 "제K항")가 있으면 해당 행으로 본다.
  - 한 행은 1행으로 센다(7.1). 방송일은 "프로그램명 (방송일시)" 칸 또는 방송일 칸에서 처음 나오는 날짜로 읽는다.
  - 호 번호는 판마다 내용이 다를 수 있다. 판 구분은 방송일로 한다(7.1).

검증
  같은 파서로 센 조 단위 행 수를 함께 출력한다. 제27조는 stats_articles.py 검증값 777과 일치해야 한다(2012.01~2026.06).
"""
import argparse, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S

def match(text, art, sub_no, num, kind):
    s = S._norm(text or "")
    dm = S._depth(s)
    laws = [m for m in S._LAW.finditer(s) if dm[m.start()] == 0]
    art_hit = False; item_hit = False
    for i, m in enumerate(laws):
        if m.group(1) not in S._TARGET:
            continue
        seg = s[m.end():laws[i + 1].start() if i + 1 < len(laws) else len(s)]
        arts = list(S._ART.finditer(seg))
        for j, a in enumerate(arts):
            sub = a.group(2) or a.group(3)
            if int(a.group(1)) != art or (sub and int(sub)) != (sub_no or None) and not (sub is None and sub_no is None):
                continue
            art_hit = True
            if num is None:
                continue
            part = seg[a.end():arts[j + 1].start() if j + 1 < len(arts) else len(seg)]
            if re.search(r"제%d%s" % (num, kind), part):
                item_hit = True
    return art_hit, item_hit

def bdate(r):
    for k in r:
        if "방송일" in k or "프로그램명" in k:
            m = re.search(r"(20\d\d|\d\d)[.\-]\s*(\d{1,2})[.\-]\s*(\d{1,2})", r[k] or "")
            if m:
                return m.group(0)
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", type=int, required=True)
    ap.add_argument("--sub", type=int)
    ap.add_argument("--item", type=int)
    ap.add_argument("--para", type=int)
    a = ap.parse_args()
    num, kind = (a.item, "호") if a.item else ((a.para, "항") if a.para else (None, ""))
    R = S.load()
    n_art = n_item = 0
    for r in R:
        text = r.get("관련조항", "")
        ah, ih = match(text, a.article, a.sub, num, kind)
        n_art += ah
        if ih:
            n_item += 1
            prog = (r.get("채널명") or r.get("방송사") or "") + " " + (r.get("프로그램명 (방송일시)") or r.get("프로그램명") or "")
            print(r["_file"], r.get("순번", ""), S.raw_date(r)[:12].strip(), bdate(r), prog.replace("\n", " ")[:50], "|", (r.get("심의결과") or "")[:20])
    print("조 단위 행 수(검증):", n_art)
    if num is not None:
        print("해당 %s 행 수:" % kind, n_item)

if __name__ == "__main__":
    main()
