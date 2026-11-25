"""의안정보시스템 응답 파싱: 원문을 고치지 않는지 확인."""
from app.services.national_assembly import parse_bill_form, parse_summary

DETAIL = """
<form id="glnbSearchForm"><input type="hidden" name="collection" value="ALL"></form>
<form id="form" name="form">
  <input type="hidden" id="billId" name="billId" value="PRC_X1">
  <input type="hidden" id="billNo" name="billNo" value="2223200">
  <input type="hidden" id="headMemoInfo" name="headMemoInfo" value="비용추계요구서 제출됨.">
  <input type="hidden" id="stageMemo" name="stageMemo" value="N"/>
</form>
"""

FRAGMENT = """<div id="tab_billInfo_sect"><h4>제안이유 및 주요내용</h4>
<pre id="prntSummary" class="theme_list_summary" style="height: 130px;">

제안이유

  현행법은 &lt;시험&gt;을 &quot;중요한&quot; 평가제도로 규정하고 있음.
  그러나 ㆍ 기준이 분산되어 있음.


주요내용

가. 대상을 정함(안 제2조).
</pre></div>"""


def test_form_only_bill_form():
    p = parse_bill_form(DETAIL)
    assert p == {"billId": "PRC_X1", "billNo": "2223200", "headMemoInfo": "비용추계요구서 제출됨.", "stageMemo": "N"}


def test_summary_verbatim():
    text = parse_summary(FRAGMENT)
    assert text.startswith("제안이유\n\n  현행법은 <시험>을 \"중요한\" 평가제도로")
    assert "  그러나 ㆍ 기준이 분산되어 있음.\n\n\n주요내용\n\n가. 대상을 정함(안 제2조)." in text
    assert text.endswith("(안 제2조).")


def test_summary_missing_returns_none():
    assert parse_summary('<div id="tab_billInfo_sect">내용 없음</div>') is None
    assert parse_summary('<pre id="prntSummary">   \n  </pre>') is None
