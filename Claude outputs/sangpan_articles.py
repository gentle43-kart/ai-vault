# -*- coding: utf-8 -*-
"""
sangpan_articles.py v1.0 (2026-11-12, Claude Sonnet 5.5) — AGENTS_통계기준.md 7.1 "상품판매방송규정 통계" 기준(v1.41, 사용자 승인 2026-11-12)

목적
  방송심의 의결 내역 통계 CSV에서 「상품소개 및 판매방송 심의에 관한 규정」(약칭 상품판매방송규정) 조문별
  적용 행 수와 결과 분포를 집계한다. 구 번호(제152호 체계, ~2026.9.28.)는 [[조문 시기 대응표]]의
  "상품판매방송규정 (제152호 → 제11호)" 표로 현행 조(제11호, 2026.9.29. 시행)에 대응시킨다.
  읽기·날짜·결과 분류는 stats_articles.py의 함수를 그대로 쓴다. hyup_articles.py의 구조를 따른다.

입력
  stats_articles.py 와 같다(2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/ 의 방송심의 파일, 선방위 제외).
  옵션: --recent(2026.07 이후 잠정본 행 추가) --until YYYY-MM-DD --article "제6조" --rows --verify

출력
  표준 출력(텍스트). 파일을 만들지 않는다. 읽기 전용(CSV·위키를 고치지 않는다).

규칙(7.1 상품판매방송규정 통계)
  - 대상 행: 관련조항에 「상품소개 및 판매방송 심의에 관한 규정」(띄어쓰기·괄호·"구"·"(규칙 제n호)" 판 표기 변형 허용)이 있는 행.
  - 조문 식별: 규정명 뒤, 다음 법령명(「·｢로 시작하는 다른 이름, "방송심의에 관한 규정", "방송광고심의에", "협찬고지", "등급분류") 앞까지의
    "제n조"·"제n조의m"만 센다. 한 행에 같은 조가 여러 번 나와도 1행.
  - 판 판별: 조 제목으로 한다. 구 번호+제목이 대응표와 맞으면(제목 앞 4글자, 띄어쓰기·가운뎃점 제외) 현행 조로 센다.
    구 제49조(건강기능식품, 2020.12.21. 삭제)는 "구 제49조"로 따로 센다. 제목이 없거나 표와 맞지 않으면 "판 미상".
  - 결과 분류: stats_articles.result_class(가장 무거운 조치 하나).
검증값(--verify, 2012.01~2026.06, 12,560행): 상품판매방송규정 표기 1,337행, 조 식별 1,337행, 조 발생 1,625건, 판 미상 0,
  구 제5조(→ 제6조) 885건, 구 제34조 88, 구 제9조 84, 구 제15조 71, 구 제49조 43행.
"""
import argparse, collections, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_articles as S

# 구 조(제152호 체계) → (구 제목, 현행 조). 출처: 0 wiki/분석/조문 시기 대응표.md "상품판매방송규정 (제152호 → 제11호)"
MAP = {
    "제1조": ("목적", "제1조"),
    "제2조": ("정의", "제2조"),
    "제3조": ("기본원칙", "제3조"),
    "제3조의2": ("적용범위", "제4조"),
    "제4조": ("청약철회등의고지", "제5조"),
    "제5조": ("일반원칙", "제6조"),
    "제6조": ("소비자보호", "제7조"),
    "제7조": ("자체심의", "제8조"),
    "제8조": ("실증책임", "제9조"),
    "제9조": ("법령의준수", "제10조"),
    "제10조": ("품위등", "제11조"),
    "제11조": ("선정성", "제12조"),
    "제12조": ("공정성", "제13조"),
    "제13조": ("특정방송프로그램과의구별", "제14조"),
    "제14조": ("원산지등표시", "제15조"),
    "제15조": ("한정판매및판매조건", "제16조"),
    "제16조": ("충동구매", "제17조"),
    "제17조": ("보도형식의표현", "제18조"),
    "제18조": ("보도내용등의인용", "제19조"),
    "제19조": ("수상인증등", "제20조"),
    "제20조": ("특허등", "제21조"),
    "제21조": ("출처명시", "제22조"),
    "제22조": ("자료인용", "제23조"),
    "제23조": ("최상급표현", "제24조"),
    "제24조": ("재방송", "제25조"),
    "제25조": ("혐오감", "제26조"),
    "제26조": ("비과학적내용", "제27조"),
    "제27조": ("화면비교", "제28조"),
    "제28조": ("음향화면", "제29조"),
    "제29조": ("안전성", "제30조"),
    "제30조": ("국가등의존엄성", "제31조"),
    "제31조": ("환경보호등", "제32조"),
    "제32조": ("개인또는단체의동의", "제33조"),
    "제32조의2": ("인권보호", "제34조"),
    "제32조의3": ("사생활보호", "제35조"),
    "제33조": ("차별금지등", "제36조"),
    "제34조": ("비교의기준", "제37조"),
    "제35조": ("실연실험조사", "제38조"),
    "제36조": ("추천보증", "제39조"),
    "제37조": ("언어", "제40조"),
    "제38조": ("음악", "제41조"),
    "제39조": ("어린이청소년", "제42조"),
    "제40조": ("가격표시", "제43조"),
    "제41조": ("기존가", "제44조"),
    "제42조": ("가격비교", "제45조"),
    "제43조": ("할인특매", "제46조"),
    "제44조": ("경품류", "제47조"),
    "제45조": ("자동주문전화", "제48조"),
    "제46조": ("상품구성", "제49조"),
    "제47조": ("기타가격표시", "제50조"),
    "제48조": ("식품등", "제51조"),
    "제50조": ("의약외품", "제52조"),
    "제51조": ("의료기기", "제53조"),
    "제52조": ("건강보조기구등", "제54조"),
    "제53조": ("화장품", "제55조"),
    "제54조": ("이미용기구", "제56조"),
    "제55조": ("영화비디오물공연물", "제57조"),
    "제56조": ("학습교재등", "제58조"),
    "제57조": ("여행관광등", "제59조"),
    "제58조": ("투자자문업투자일임업", "제60조"),
    "제58조의2": ("부동산등", "제61조"),
    "제59조": ("보험상품", "제62조"),
    "제60조": ("상품권", "제63조"),
    "제61조": ("의류", "제64조"),
    "제62조": ("속옷", "제65조"),
    "제63조": ("정수기등", "제66조"),
    "제63조의2": ("젖병젖꼭지제품", "제67조"),
    "제64조": ("방송금지", "제68조"),
    "제65조": ("출연제한", "제69조"),
    "제65조의2": ("심의절차의준용", "제70조"),
    "제65조의3": ("시행에필요한세부사항", "제71조"),
    "제65조의4": ("결정사항게시등", "제72조")
}
ALIAS = {"방송및보도내용인용": "보도내용등의인용"}   # 구 제18조 제목의 표기 변형
GONE = {"제49조": "건강기능식품"}                    # 2020.12.21. 삭제, 현행 대응 조 없음

NAME_RE = re.compile(r"상품\s*소개\s*및\s*판매\s*방송\s*심의\s*에\s*관한\s*(?:규정|규칙)")
ART_RE = re.compile(r"제\s*(\d+)\s*조\s*(?:의\s*(\d+))?\s*(?:\(([^)]*)\)?)?")
STOP_RE = re.compile(r"[「｢]|방송\s*심의에\s*관한\s*규정|방송광고\s*심의에|협찬고지|등급분류")

def sq(s):
    return re.sub(r"[\s·ㆍ‧․∙,]", "", s or "")

def segments(rel):
    out = []
    for m in NAME_RE.finditer(rel):
        s = rel[m.end():]
        n = STOP_RE.search(s)
        out.append(s[:n.start()] if n else s)
    return out

def articles(rel):
    """관련조항 → {(구 조, 판정)} 판정: 현행 조 이름 / '구 제49조' / '판 미상'. 규정명이 없으면 None."""
    segs = segments(rel)
    if not segs:
        return None
    out = set()
    for s in segs:
        for m in ART_RE.finditer(s):
            key = "제%s조%s" % (m.group(1), "의" + m.group(2) if m.group(2) else "")
            t = ALIAS.get(sq(m.group(3)), sq(m.group(3)))
            if key in GONE and t and (t.startswith(GONE[key][:4])):
                out.add((key, "구 " + key))
            elif key in MAP and t and (t.startswith(MAP[key][0][:4]) or MAP[key][0].startswith(t[:4])):
                out.add((key, MAP[key][1]))
            else:
                out.add((key, "판 미상"))
    return out

VERIFY = {"rows": 1337, "ident": 1337, "occ": 1625, "unknown": 0,
          "구 제5조": 885, "구 제34조": 88, "구 제9조": 84, "구 제15조": 71, "구 제49조": 43}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article"); ap.add_argument("--rows", action="store_true")
    ap.add_argument("--recent", action="store_true"); ap.add_argument("--until"); ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    rows = S.load(a.recent, until=a.until)
    tgt = [(r, articles(r.get("관련조항") or "")) for r in rows]
    tgt = [(r, x) for r, x in tgt if x is not None]
    ident = sum(1 for _, x in tgt if x)
    occ = collections.Counter(old for _, x in tgt for old, _new in x)
    cur = collections.Counter(new for _, x in tgt for _old, new in x)
    unknown = sum(1 for _, x in tgt if any(new == "판 미상" for _o, new in x))
    print("대상 행 %d / 상품판매방송규정 표기 %d / 조 식별 %d / 조 발생 %d / 판 미상 행 %d" % (len(rows), len(tgt), ident, sum(occ.values()), unknown))
    def num(k): return int(re.search(r"\d+", k).group())
    print("구 조별(조 발생 건수):", sorted(occ.items(), key=lambda kv: (num(kv[0]), kv[0])))
    print("현행 조별(제11호 기준, 판 미상·구 제49조 별도):", sorted(cur.items(), key=lambda kv: (kv[0].startswith(("판", "구")), num(kv[0]) if re.search(r"\d", kv[0]) else 0, kv[0])))
    def yr(r): return S.year(r)
    print("연도:", sorted(collections.Counter(yr(r) for r, _ in tgt).items(), key=str))
    print("결과:", dict(collections.Counter(S.result_class(r.get("심의결과") or "") for r, _ in tgt)))
    # 현행 조 → 결과 분포
    print("\n현행 조별 결과 분포:")
    dist = collections.defaultdict(collections.Counter)
    for r, x in tgt:
        rc = S.result_class(r.get("심의결과") or "")
        for new in {n for _o, n in x}:
            dist[new][rc] += 1
    for k in sorted(dist, key=lambda k: (k.startswith(("판", "구")), num(k) if re.search(r"\d", k) else 0, k)):
        print(" %s %d행: %s" % (k, sum(dist[k].values()), dict(dist[k])))
    if a.article:
        sel = [r for r, x in tgt if any(new == a.article for _o, new in x)]
        print("\n%s %d행" % (a.article, len(sel)))
        print(" 결과:", dict(collections.Counter(S.result_class(r.get("심의결과") or "") for r in sel)))
        print(" 연도:", sorted(collections.Counter(yr(r) for r in sel).items(), key=str))
        if a.rows:
            for r in sel:
                print(" -", r.get("_file"), r.get("순번"), S.case_no(r), S.raw_date(r)[:12].replace("\n", " "), "|",
                      (r.get("방송사/ 프로그램명") or r.get("프로그램명 (방송일시)") or "")[:50].replace("\n", " "), "|", r.get("심의결과"), "|", r["관련조항"][:140].replace("\n", " "))
    if a.verify:
        got = {"rows": len(tgt), "ident": ident, "occ": sum(occ.values()), "unknown": unknown,
               "구 제5조": occ["제5조"], "구 제34조": occ["제34조"], "구 제9조": occ["제9조"], "구 제15조": occ["제15조"], "구 제49조": cur["구 제49조"]}
        print("\n검증(기본 집계 2012.01~2026.06, --recent 없이 실행):")
        for k, v in VERIFY.items():
            print(" %-8s 기대 %5d 실제 %5d %s" % (k, v, got[k], "OK" if v == got[k] else "불일치"))

if __name__ == "__main__":
    main()
