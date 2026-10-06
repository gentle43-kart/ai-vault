# -*- coding: utf-8 -*-
"""
refine_subcommittee_results.py v1.0 (2026-10-06)

목적: 방송심의소위원회 "회의결과" 변환본(연도별 8개 판)을 안건 1건 단위로 정리한 정제본을 만든다(AGENTS.md 6.7 새 변환본 추가).
      원래 판은 PDF 표를 줄 단위로 풀어 놓아 의결번호가 줄바꿈으로 끊기고(예: '제2019-방송' / '-01-0001호') 쪽마다 표 머리 줄이 끼어 있어
      의결번호 검색이 되지 않고 검색 잡음이 크다. 정제본은 안건마다 제목 '### 제2023-방송-46-0516호 | 방송사 | 프로그램명' 아래에
      방송일시·인지·소위 논의결과·표결 분포·적용조항·논의내용·원본 PDF 쪽 필드를 둔다.
입력: 1 documents_md/회의록_md/방송소위_md/연도별_방송소위_회의결과/방송소위_회의결과_{연도}년.md (읽기만 한다)
출력: 1 documents_md/회의록_md/방송소위_md/연도별_방송소위_회의결과_정제본/방송소위_회의결과_{연도}_정제.md (새 파일만 만든다. 이미 있으면 덮어쓰지 않는다)
내용 원칙: 논의내용은 원문 줄을 그대로 두고, 쪽 머리의 표 머리 줄('구분 의결번호 방송사 프로그램명', '(방송일시) 논의내용 인지', '구분')과
          쪽 표시 주석만 뺀다. 요약·수정·보충하지 않는다. 최종 의결은 통계 CSV, 결정 사유는 회의록이 우선한다(AGENTS.md 7.1).
검증(출력에 표시): 회의별 '상정안건 총 n건'과 안건 수 일치, 의결번호 형식 오류, 같은 연도 통계 CSV와의 의결번호 대조율(불일치 목록).
사용법:
  python refine_subcommittee_results.py --check                 파일을 쓰지 않고 검증만(기본 출력 폴더 대신 --out 지정 가능)
  python refine_subcommittee_results.py --write                 정제본 파일을 만든다
  python refine_subcommittee_results.py --check --out 임시폴더 --write   임시 폴더에 만들어 시험
옵션: --vault 자료창고 경로(기본: 이 파일의 상위 폴더), --years 2021,2023, --csv 통계 CSV 대조(기본 켬, --no-csv로 끔)
"""
import argparse
import collections
import csv
import io
import os
import re
import sys
from datetime import date

csv.field_size_limit(10 ** 9)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_REL = "1 documents_md/회의록_md/방송소위_md/연도별_방송소위_회의결과"
OUT_REL = "1 documents_md/회의록_md/방송소위_md/연도별_방송소위_회의결과_정제본"
CSV_RELS = ["2 data_csv/통계_csv/방송/쳇지피팅용 병합_csv/총 병합/방송심의_전체통합(120101-260622).csv",
            "2 data_csv/통계_csv/방송/쳇지피팅용 병합_csv/△26.01.-08.csv"]      # 총 병합본은 2026년 6월 22일까지라 뒤쪽 보조 CSV를 함께 쓴다
# 소위 단계에서 종결되는 결과(통계 CSV에 같은 번호로 올라오는 것이 정상). 그 밖의 결과(의견진술·의결보류·미논의·전체회의 상정·법정제재 등)는
# 전체회의 최종 의결번호나 후속 회의 번호로 CSV에 올라오므로 소위 번호와 일치하지 않을 수 있다.
FINAL_AT_SUBCOMMITTEE = ("권고", "의견제시", "문제없음")

H2_RE = re.compile(r"^##\s+(\d{4})년\s+제\s*(\d+)\s*차\s+방송심의소위원회\s+회의\s*결과\s*—\s*(\d{4}-\d{2}-\d{2})\s*$")
SRC_RE = re.compile(r"^\*원본:\s*(.+?)\s*·\s*PDF\s*(\d+)\s*쪽부터\*\s*$")
PAGE_RE = re.compile(r"^<!--\s*(\d{4})\s+PDF\s+p\.\s*(\d+)\s*-->\s*$")
START_RE = re.compile(r"^(\d{1,3})\s+제\s*(\d{4})\s*-")
HEAD_RE = re.compile(
    r"^\d{1,3}\s+제\s*(\d{4})\s*-\s*(?:([가-힣]+)\s*-\s*)?(\d{1,2})\s*-\s*(\d(?:\s?\d){2,3})\s*호\s*(.*?)\s*"
    r"\(\s*(\d{4}[^)]*|)\s*\)\s*(.*)$")
GROUP_RE = re.compile(r"^[가-하]\.\s*[^\s].{0,30}에\s*관한\s*건\s*$")          # 가. 의견진술 청취에 관한 건
SUB_RE = re.compile(r"^\d{1,2}\)\s*.{2,20}부문\s*\(총\s*\d+\s*건\)\s*$")       # 1) 지상파방송 부문(총 2건)
NOISE = {"구분 의결번호 방송사 프로그램명", "(방송일시) 논의내용 인지", "구분"}
KNOWN_FLAG = ("민원", "모니터", "심의", "기관", "기타")                           # '인지' 구분
CASE_OK = re.compile(r"^제\d{4}-(?:방송-)?\d{2}-\d{4}호$")        # 2025년 번호부터 분야 표기('방송')가 없다(예: 제2025-16-0241호)
CASE_STAT_RE = re.compile(r"(?<!\d)(\d{4})\s?-\s?(?:([가-힣]+)\s?-\s?)?(\d{1,2})\s?-\s?(\d{3,4})(?!\d)")


class Item:
    def __init__(self, no, line_no, page):
        self.no, self.line_no, self.page_start, self.page_end = no, line_no, page, page
        self.head = []          # 머리 줄(의결번호~방송일시~인지)
        self.head_done = False
        self.fields = {}
        self.body = []          # 본문 줄
        self.group, self.sub = "", ""
        self.problems = []


class Meeting:
    def __init__(self, year, nth, day, line_no):
        self.year, self.nth, self.day, self.line_no = year, int(nth), day, line_no
        self.src, self.page0 = "", None
        self.header = []        # 첫 안건 앞의 줄
        self.items = []
        self.total = None
        self.summary = []       # '○ 법정제재 : 주의 7건' 같은 줄
        self.when = ""


def case_label(y, sec, nn, seq):
    seq = re.sub(r"\s+", "", seq)        # 줄바꿈으로 숫자가 끊긴 경우('024' '1호')
    return f"제{y}-{sec + '-' if sec else ''}{int(nn):02d}-{int(seq):04d}호"


def parse_head(item, tail_pending=False):
    """머리 줄을 합쳐 의결번호·방송사·프로그램·방송일시·논의내용·인지를 읽는다. 아직 끝나지 않았으면 None."""
    text = " ".join(l.strip() for l in item.head)
    m = HEAD_RE.match(text)
    if not m:
        return None
    y, sec, nn, seq, mid, when, tail = m.groups()
    mid = re.sub(r"\s+", " ", mid).strip()
    q = mid.find("‘")
    if q >= 0:
        bro, prog = mid[:q].strip(), mid[q:].strip()
        if prog.startswith("‘") and prog.endswith("’") and prog.count("‘") == 1:
            prog = prog[1:-1].strip()
    else:
        bro, prog = mid, ""
    dates = [d.strip(" ,;") for d in re.split(r"(?=\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2})", re.sub(r"\s+", " ", when)) if d.strip(" ,;")]
    tail = re.sub(r"\s+", " ", tail).strip()
    toks = tail.split(" ") if tail else []
    flag = toks[-1] if toks and toks[-1] in KNOWN_FLAG else ""
    result = " ".join(toks[:-1] if flag else toks)
    return dict(case=case_label(y, sec, nn, seq), sector=sec or "", broadcaster=bro, program=prog, when=dates, result=result, flag=flag, tail=tail)


def balanced(text):
    """text에서 첫 '(' 에 대응하는 ')' 안쪽을 돌려준다: (앞부분, 괄호 안, 뒷부분)"""
    i = text.find("(")
    if i < 0:
        return text.strip(), "", ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return text[:i].strip(), text[i + 1:j].strip(), text[j + 1:].strip()
    return text[:i].strip(), text[i + 1:].strip(), ""      # 닫는 괄호가 없으면 끝까지


def finish_item(it):
    """본문 줄에서 논의내용·소위 논의결과·표결 분포·적용조항을 가른다."""
    body = [l.rstrip() for l in it.body]
    while body and not body[-1].strip():
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    ridx = next((i for i, l in enumerate(body) if re.match(r"^\s*○\s*소위\s*논의\s*결과", l)), None)
    cidx = next((i for i, l in enumerate(body) if re.match(r"^\s*▶\s*적용조항", l)), None)
    narr, res_lines, clause_lines, extra = body, [], [], []
    if ridx is not None:
        narr = body[:ridx]
        end = cidx if (cidx is not None and cidx > ridx) else len(body)
        res_lines = body[ridx:end]
        if cidx is not None and cidx > ridx:
            clause_lines = body[cidx:]
    elif cidx is not None:
        narr, clause_lines = body[:cidx], body[cidx:]
    # 적용조항이 끝난 뒤 이어지는 비고(※ …)는 논의내용 끝에 둔다
    for k, l in enumerate(clause_lines[1:], 1):
        if re.match(r"^\s*(※|○|\[)", l):
            extra = clause_lines[k:]
            clause_lines = clause_lines[:k]
            break
    narr = narr + ([""] if narr and extra else []) + extra
    res_text = " ".join(l.strip() for l in res_lines)
    res_text = re.sub(r"^○\s*소위\s*논의\s*결과\s*:?\s*", "", res_text)
    pre, inside, post = balanced(res_text)
    if ridx is not None and not pre and inside:      # '(346호와 병합 결정)'처럼 괄호 안에만 내용이 있으면 결과로 보존한다
        pre, inside = f"({inside})", ""
    it.fields["sowi_result"] = pre if ridx is not None else ""
    it.fields["vote"] = inside + (f" {post}" if post else "")
    it.fields["clause"] = re.sub(r"^▶\s*적용조항\s*:?\s*", "", " ".join(l.strip() for l in clause_lines)).strip()
    it.fields["narrative"] = narr
    it.fields["has_result"] = ridx is not None
    it.fields["has_clause"] = cidx is not None


HDR_A = ["구분 의결번호 방송사 프로그램명", "(방송일시) 논의내용 인지", "구분"]
HDR_B = ["구분", "의결번호", "방송사", "프로그램명", "(방송일시)", "논의내용", "인지", "구분"]


def clean_lines(raw_lines):
    """쪽마다 끼어 있는 표 머리 줄(한 줄 판 3줄, 칸마다 풀린 판 8줄)을 뺀다. (원래 줄 번호, 줄) 목록을 돌려준다."""
    out, i, n = [], 0, len(raw_lines)
    while i < n:
        seg_b = [x.strip() for x in raw_lines[i:i + 8]]
        seg_a = [x.strip() for x in raw_lines[i:i + 3]]
        if seg_b == HDR_B:
            i += 8
            continue
        if seg_a == HDR_A:
            i += 3
            continue
        out.append((i + 1, raw_lines[i].rstrip()))
        i += 1
    return out


def is_start(lines, k):
    """lines[k]가 안건 시작인가: '1 제2020-방송'(한 줄 판) 또는 '1' 다음 줄이 '제2021-방송'(칸마다 풀린 판)"""
    s = lines[k][1].strip()
    if START_RE.match(lines[k][1]):
        return True
    return bool(re.fullmatch(r"\d{1,3}", s)) and k + 1 < len(lines) and re.match(r"^제\s*\d{4}\s*-", lines[k + 1][1].strip()) is not None


def parse_file(path):
    raw = open(path, encoding="utf-8-sig").read().split("\n")
    lines = clean_lines(raw)
    meetings, mt, item = [], None, None
    page = None
    group = sub = ""
    state = "none"      # none | head | tail | body

    def close_item():
        nonlocal item, state
        if item is not None:
            if not item.head_done:
                item.problems.append("머리 줄을 끝까지 읽지 못함")
            finish_item(item)
            item = None
        state = "none"

    def special(s):
        return bool(re.match(r"^(○|▶|-|※|<!--)", s)) or bool(GROUP_RE.match(s)) or bool(SUB_RE.match(s))

    for k, (ln, line) in enumerate(lines):
        s = line.strip()
        m = H2_RE.match(line)
        if m:
            close_item()
            mt = Meeting(int(m.group(1)), m.group(2), m.group(3), ln)
            meetings.append(mt)
            group = sub = ""
            page = None
            continue
        if mt is None:
            continue
        m = SRC_RE.match(line)
        if m and not mt.items:
            mt.src, mt.page0 = m.group(1), int(m.group(2))
            page = mt.page0
            continue
        m = PAGE_RE.match(line)
        if m:
            page = int(m.group(2))      # 이 쪽에 실제 내용 줄이 나올 때 그 안건의 끝쪽을 늘린다(쪽 표시만 걸친 경우는 세지 않음)
            continue
        if s in NOISE and state != "head":
            continue
        if state != "head" and is_start(lines, k):
            close_item()
            nm = re.match(r"^(\d{1,3})", s)
            item = Item(int(nm.group(1)), ln, page)
            item.group, item.sub = group, sub
            mt.items.append(item)
            item.head = [line]
            state = "head"
            r = parse_head(item)
            if r:
                item.fields.update(r)
                item.head_done = True
                state = "tail"
            continue
        if state == "head":
            if is_start(lines, k) or len(item.head) >= 14:
                item.problems.append("머리 줄을 끝까지 읽지 못함")
                state = "body"
                item.body.append(line)
                continue
            item.head.append(line)
            if s and page is not None:
                item.page_end = page
            r = parse_head(item)
            if r:
                item.fields.update(r)
                item.head_done = True
                state = "tail"
            continue
        if state == "tail":
            # 방송일시 괄호 뒤의 '논의내용 인지'가 다음 줄(들)로 넘어간 경우: 짧은 줄을 이어 붙이다 '인지' 낱말이 나오면 끝낸다
            f = item.fields
            if (not f["flag"]) and s and len(s) <= 12 and not special(s) and f.get("tail_lines", 0) < 3:
                t = (f["tail"] + " " + s).strip()
                toks = t.split(" ")
                f["tail"], f["tail_lines"] = t, f.get("tail_lines", 0) + 1
                if toks[-1] in KNOWN_FLAG:
                    f["flag"], f["result"] = toks[-1], " ".join(toks[:-1])
                else:
                    f["result"] = t
                continue
            state = "body"
        if GROUP_RE.match(s) and not line.startswith(" "):
            close_item()
            group, sub = s, ""
            if not mt.items:
                mt.header.append(line)
            continue
        if SUB_RE.match(s) and not line.startswith(" "):
            close_item()
            sub = s
            continue
        if item is not None and state == "body":
            item.body.append(line)
            if s and page is not None:
                item.page_end = page
            continue
        if item is None:
            mt.header.append(line)
    close_item()
    return meetings


def meeting_info(mt):
    """첫 안건 앞의 줄에서 회의일시·상정안건 총건수·처리 요약을 읽는다. '○ 행정지도 :' 뒤의 값이 다음 줄에 있는 판도 처리한다."""
    mt.summary, mt.when, mt.total = [], "", None
    hdr = [l.rstrip() for l in mt.header]
    joined = []
    for l in hdr:
        if joined and re.match(r"^\s*(□|○)[^:：]*[:：]\s*$", joined[-1]) and not re.match(r"^\s*(□|○)", l):
            joined[-1] = joined[-1].rstrip() + " " + l.strip()
        else:
            joined.append(l)
    for l in joined:
        m = re.match(r"^\s*□\s*회의일시\s*:\s*(.+)$", l)
        if m:
            mt.when = m.group(1).strip()
        m = re.match(r"^\s*□\s*상정안건\s*:\s*총\s*(\d+)\s*건", l)
        if m:
            mt.total = int(m.group(1))
        if re.match(r"^\s*○\s*\S", l):
            mt.summary.append(re.sub(r"\s+", " ", l.strip().lstrip("○").strip()))


def render(year, meetings, src_name):
    out = [f"# 방송소위 회의결과 정제본({year}년)", "",
           f"- 이 파일은 `{SRC_REL}/{src_name}`(원래 판)를 안건 1건 단위로 정리한 변환본이다. 논의내용은 원문 줄을 그대로 두고, 쪽 머리의 표 머리 줄과 쪽 표시 주석만 뺐다. 요약·수정·보충하지 않았다.",
           "- 최종 의결 여부·결과는 통계 CSV, 결정 사유는 회의록이 우선한다. 이 문서의 고유 정보는 소위 표결 분포와 처리 경과다.",
           f"- 생성: `Claude outputs/refine_subcommittee_results.py` v1.0 ({date.today():%Y-%m-%d}). 안건 {sum(len(m.items) for m in meetings)}건, 회의 {len(meetings)}회.", ""]
    for mt in meetings:
        meeting_info(mt)
        out += [f"## {mt.year}년 제{mt.nth}차 방송심의소위원회 회의 결과 — {mt.day}", ""]
        out.append(f"- 원본: {mt.src} (PDF {mt.page0}쪽부터)" if mt.src else "- 원본: (원래 판에 표시 없음)")
        if mt.when:
            out.append(f"- 회의일시: {mt.when}")
        out.append(f"- 상정안건: 총 {mt.total}건" + (f" ({' / '.join(mt.summary)})" if mt.summary else "") if mt.total is not None else "- 상정안건: (표시 없음)")
        out += [f"- 정제 안건 수: {len(mt.items)}건", ""]
        for it in mt.items:
            f = it.fields
            case = f.get("case", f"(의결번호 미확인, 원래 판 {it.line_no}줄)")
            out.append(f"### {case} | {f.get('broadcaster', '')} | {f.get('program', '')}".rstrip(" |"))
            out.append("")
            part = " > ".join(x for x in (it.group, it.sub) if x)
            if part:
                out.append(f"- 안건구분: {part}")
            out.append(f"- 방송일시: {'; '.join(f['when']) if f.get('when') else '(표시 없음)'}")
            out.append(f"- 인지: {f.get('flag') or '(표시 없음)'}")
            res = f.get("sowi_result") or f.get("result") or ""
            out.append(f"- 소위 논의결과: {res or '(표시 없음)'}")
            if f.get("vote"):
                out.append(f"- 표결 분포: {f['vote']}")
            out.append(f"- 적용조항: {f.get('clause') or '(표시 없음)'}")
            narr = f.get("narrative") or []
            if narr:
                out.append("- 논의내용:")
                prev_blank = False
                for l in narr:
                    if not l.strip():
                        if not prev_blank:
                            out.append("")
                        prev_blank = True
                        continue
                    prev_blank = False
                    out.append("  " + l.rstrip())
            pages = f"{it.page_start}" if it.page_end in (None, it.page_start) else f"{it.page_start}~{it.page_end}"
            out.append(f"- 원본 PDF 쪽: {mt.src} p.{pages}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def csv_cases(path):
    """통계 CSV의 의결번호 집합({연도: set(라벨)}). 의결번호 열을 찾아 CASE_STAT_RE로 정규화한다."""
    sys.path.insert(0, r"J:\MCP\ai-vault-mcp")
    import build_index as bi
    text, _ = bi.read_text(path)
    header, data, _note, _st = bi.read_csv_rows(path, text)
    cols = [bi.find_col(header, ("의결번호", "구분", "의결일/ 의결번호")), bi.find_col(header, ("의결일", "회차/의결일자"))]
    res = collections.defaultdict(set)
    for row in data:
        for c in cols:
            if c is None or c >= len(row):
                continue
            m = CASE_STAT_RE.search(row[c])
            if m:
                y, sec, nn, seq = m.groups()
                if (sec or "") in ("방송", ""):
                    res[int(y)].add(f"{int(y)}-{int(nn):02d}-{int(seq):04d}")
                break
    return res


def main():
    ap = argparse.ArgumentParser(description="방송소위 회의결과 정제본 생성")
    ap.add_argument("--vault", default=os.path.dirname(HERE))
    ap.add_argument("--out", help="출력 폴더(기본: 자료창고의 정제본 폴더)")
    ap.add_argument("--years")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-csv", action="store_true")
    a = ap.parse_args()
    src_dir = os.path.join(a.vault, SRC_REL)
    out_dir = a.out or os.path.join(a.vault, OUT_REL)
    years = [int(y) for y in a.years.split(",")] if a.years else None
    files = sorted(f for f in os.listdir(src_dir) if re.match(r"방송소위_회의결과_(\d{4})년\.md$", f))
    stat = None
    if not a.no_csv:
        stat = collections.defaultdict(set)
        for rel in CSV_RELS:
            for y, v in csv_cases(os.path.join(a.vault, rel)).items():
                stat[y] |= v
    tot_items = tot_match = 0
    all_bad = []
    by_res = collections.defaultdict(lambda: [0, 0])
    for fn in files:
        year = int(re.search(r"(\d{4})", fn).group(1))
        if years and year not in years:
            continue
        meetings = parse_file(os.path.join(src_dir, fn))
        for mt in meetings:
            meeting_info(mt)
        items = [it for mt in meetings for it in mt.items]
        cases = [it.fields.get("case") for it in items]
        bad_fmt = [(mt.nth, it.no, it.fields.get("case"), it.problems) for mt in meetings for it in mt.items
                   if not it.fields.get("case") or not CASE_OK.match(it.fields["case"])]
        cnt_bad = [(mt.year, mt.nth, mt.day, mt.total, len(mt.items)) for mt in meetings if mt.total is not None and mt.total != len(mt.items)]
        no_total = [mt.nth for mt in meetings if mt.total is None]
        dup = [(mt.nth, c) for mt in meetings for c, n in collections.Counter(it.fields.get('case') for it in mt.items).items() if n > 1]   # 같은 회의 안의 중복
        no_res = sum(1 for it in items if not it.fields.get("has_result"))
        no_clause = sum(1 for it in items if not it.fields.get("has_clause"))
        no_flag = sum(1 for it in items if not it.fields.get("flag"))
        no_when = sum(1 for it in items if not it.fields.get("when") or it.fields["when"] == [])
        no_prog = sum(1 for it in items if not it.fields.get("program"))
        probs = [(it.line_no, it.fields.get("case"), it.problems) for it in items if it.problems]
        print(f"[{year}] 회의 {len(meetings)}회 / 안건 {len(items)}건 | 상정안건 합 {sum(m.total or 0 for m in meetings)} | 건수 불일치 회의 {len(cnt_bad)} | 총건수 표시 없는 회의 {len(no_total)}"
              f" | 의결번호 형식 오류 {len(bad_fmt)} | 같은 번호 중복 {len(dup)}")
        print(f"       결과 줄 없음 {no_res} / 적용조항 없음 {no_clause} / 인지 없음 {no_flag} / 방송일시 없음 {no_when} / 프로그램명 없음 {no_prog} / 머리 읽기 문제 {len(probs)}")
        for x in cnt_bad[:30]:
            print("       건수 불일치:", x)
        for x in bad_fmt[:10]:
            print("       형식 오류:", x)
        for x in dup[:10]:
            print("       중복:", x)
        for x in probs[:5]:
            print("       문제:", x)
        if stat is not None:
            ys = stat.get(year, set())
            labels = []
            for it in items:
                m = CASE_STAT_RE.search(it.fields.get("case", ""))
                if m:
                    y, sec, nn, seq = m.groups()
                    labels.append(f"{int(y)}-{int(nn):02d}-{int(seq):04d}")
            # 통계 CSV는 연도별 파일이므로, 같은 연도(의결번호의 연도)의 CSV 번호와 대조한다
            by_y = collections.defaultdict(list)
            for l in labels:
                by_y[int(l[:4])].append(l)
            match = sum(1 for y, ls in by_y.items() for l in ls if l in stat.get(y, set()))
            miss = sorted(l for y, ls in by_y.items() for l in ls if l not in stat.get(y, set()))
            for it in items:
                m2 = CASE_STAT_RE.search(it.fields.get("case", ""))
                if not m2:
                    continue
                lab = f"{int(m2.group(1))}-{int(m2.group(3)):02d}-{int(m2.group(4)):04d}"
                r0 = (it.fields.get("sowi_result") or it.fields.get("result") or "").split("(")[0].strip() or "(없음)"
                by_res[r0][0] += 1
                by_res[r0][1] += lab in stat.get(int(m2.group(1)), set())
                if lab in miss:
                    all_bad.append((year, lab, r0))
            tot_items += len(labels)
            tot_match += match
            print(f"       통계 CSV 대조: {match}/{len(labels)} 일치 ({100*match/max(1,len(labels)):.1f}%), 불일치 {len(miss)}건")
        if a.write:
            os.makedirs(out_dir, exist_ok=True)
            op = os.path.join(out_dir, f"방송소위_회의결과_{year}_정제.md")
            if os.path.exists(op):
                print(f"       ! 이미 있어 쓰지 않음: {op}")
            else:
                open(op, "w", encoding="utf-8", newline="\n").write(render(year, meetings, fn))
                print(f"       -> {op}")
    if stat is not None:
        print(f"\n전체 통계 CSV 대조: {tot_match}/{tot_items} ({100*tot_match/max(1,tot_items):.1f}%)")
        fin = [(n, h) for r, (n, h) in by_res.items() if r in FINAL_AT_SUBCOMMITTEE]
        fn_, fh_ = sum(n for n, h in fin), sum(h for n, h in fin)
        print(f"소위 단계에서 종결되는 결과({'·'.join(FINAL_AT_SUBCOMMITTEE)}) 대조: {fh_}/{fn_} ({100*fh_/max(1,fn_):.1f}%)")
        print("소위 논의결과별 일치율:")
        for r, (n, h) in sorted(by_res.items(), key=lambda kv: -kv[1][0])[:12]:
            print(f"  {r:14s} {h:5d}/{n:5d} ({100*h/n:5.1f}%)")
        print("불일치 목록(연도: 번호 [소위 논의결과]):")
        for y, l, r in all_bad:
            print(f"  {y}: {l} [{r}]")


if __name__ == "__main__":
    main()
