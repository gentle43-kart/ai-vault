# -*- coding: utf-8 -*-
# 목적: 위키 광고심의규정 조문 페이지의 열린 항목 중 "통계 CSV 의결 내용 칸 검색"이 근거인 항목을 query_decisions(MCP v1.19)와 같은 코드로 점검한다.
#       항목마다 키워드(의결 내용 칸 안에서만)로 행을 세고, 광고심의규정 조(위키 현행 번호 기준 article_basis=current)별 분포와
#       항목이 묻는 조의 행 수를 출력한다. 읽기 전용(search.db를 mode=ro로 연다).
# 입력: J:\MCP\ai-vault-mcp\data\search.db, 0 wiki\분석\조문 시기 대응표.md(2A절), J:\MCP\ai-vault-mcp\decision_query.py v0.3
# 출력: 표준출력(항목, 키워드, 전체 행, 광고심의규정 조가 있는 행, 조 분포, 목표 조 행 수). 결과 데이터는 저장하지 않는다.
# 검증: 키워드 없이 호출하면 기본 범위 12,560행(검증값)이 나오는지 확인한다. 키워드 일치는 단순 부분 문자열이며 내용을 읽고 판단한 것이 아니다.
# 실행: python open_items_content_check.py
import sqlite3
import sys

sys.path.insert(0, r"J:/MCP/ai-vault-mcp")
import decision_query as dq

con = sqlite3.connect("file:J:/MCP/ai-vault-mcp/data/search.db?mode=ro", uri=True)
CORR = r"J:/AI 자료/0 wiki/분석/조문 시기 대응표.md"


def q(**kw):
    return dq.query(con, "1 = 1", "all", kw.pop("unit", "row"), corr_path=CORR, **kw)


# (페이지, 키워드, 시작, 끝, 항목이 묻는 현행 조 목록)
ITEMS = [
    ("제11조", "친환경|무공해", "", "", ["제21조"]),
    ("제13조", "외모|신체", "2019-09-23", "", ["제13조", "제5조"]),
    ("제16조", "유인|고가", "", "", ["제18조", "제21조"]),
    ("제18조", "비교|비방", "2019-01-01", "", ["제18조", "제21조"]),
    ("제19조", "사용전|사용후|전후비교|비포|애프터", "2019-01-01", "2020-12-27", ["제19조"]),
    ("제20조", "근거|입증", "", "", ["제20조", "제21조"]),
    ("제22조", "인증|수상", "", "", ["제22조", "제21조"]),
    ("제23조", "연출|재연", "", "", ["제23조", "제21조"]),
    ("제24조", "원료|시료", "", "", ["제24조", "제21조"]),
    ("제25조", "추천|보증|전문가", "", "", ["제25조", "제21조"]),
    ("제40조", "학습효과|성적향상|학원", "", "", ["제40조", "제21조"]),
    ("제5조", "조롱|희화화", "2019-09-23", "", ["제5조", "제13조"]),
    ("제6조", "소송|재판|분쟁", "", "", ["제6조", "제5조"]),
    ("제7조", "오인|고정출연자", "", "", ["제7조", "제21조"]),
    ("제8조", "재난|긴급|방송사고", "", "", ["제8조", "제4조"]),
]

if __name__ == "__main__":
    base = q()["reproduction"]["검증값"]
    print("검증값:", base["기본 범위 행 수"], base["기대"], base["일치"])
    for page, kw, d1, d2, arts in ITEMS:
        a = dict(content=kw)
        if d1:
            a["date_from"] = d1
        if d2:
            a["date_to"] = d2
        tot = q(**a)["count"]
        ad = q(law="광고심의규정", **a)["count"]
        g = q(law="광고심의규정", group_by=["article"], article_basis="current", **a)["groups"] or []
        g = sorted(g, key=lambda x: -x["count"])[:6]
        tgt = {t: q(law="광고심의규정", article=t, article_basis="current", **a)["count"] for t in arts}
        print(f"{page} | {kw} | {d1}~{d2} | 전체 {tot}행, 광고심의규정 조 있는 {ad}행 | 목표 조 {tgt}")
        print("    분포(구→현행):", [(x["article"], x.get("article_current"), x["count"]) for x in g])
