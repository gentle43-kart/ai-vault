# -*- coding: utf-8 -*-
"""
index_drafting_examples.py v2.0 (2026-11-22, Claude)

목적: 위키 분석 페이지 '안건 작성예시 색인'의 표를 만들고, 색인에 빠진 예시를 찾는다.
      '작성예시_md/안건/' 아래 변환본 md 전체를 읽어 세부안건의 머리표(방송사·프로그램, 의결번호, 의결일·차수,
      방송일, 프로그램유형)와 '적용조항' 절을 기계로 뽑는다. 판단·요약은 하지 않는다(그 칸은 사람이 채운다).
입력: <vault>/1 documents_md/작성예시_md/안건/ 아래 md 전체(images 폴더 제외). 새 폴더를 넣어도 코드를 고치지 않는다.
      <vault>/0 wiki/분석/안건 작성예시 색인.md (--check·--rows에서 이미 실린 행을 읽는 용도)
출력: --check  표준출력에 새 행·사라진 행 목록(아무것도 쓰지 않는다)
      --rows   표준출력에 색인 표 행(--only-new면 색인에 없는 것만, 절 이름으로 묶어 표시)
      --build 경로  전체 표(절별)를 그 경로 파일로 쓴다(위키 페이지 본문 조립용)
쓰기 범위: --build가 지정한 파일뿐. 위키·자료창고는 고치지 않는다.
읽는 방식(v2.0):
  - 파일에서 세부안건 머리를 찾는다. 머리 형식 3가지: (A) HTML 표 머리(th colspan=3 프로그램 / th 의결번호,
    2024년 이후 PDF 변환본·2026년 회의자료), (B) '## 프로그램 의결번호호' 제목(2019년 예시1), (C) '| 프로그램 | 의결번호 |' 표.
  - 머리가 2개 이상이면 안건마다 1행(회의자료·모음 파일), 1개 이하이면 파일마다 1행(구분은 파일 이름으로 짐작).
  - 2009~2014년 폴더(유형별 안건 모음)는 예전 방식 그대로 첫 줄 머리표만 읽는다(이미 색인된 행과 맞추기 위함).
  - 회의 순서·본문·보고사항·회의록 발췌는 안건 행으로 만들지 않는다(안건 머리가 있는 부분만).
절 이름: 유형별 안건 모음은 쟁점 폴더명, 그 밖은 '폴더명 · 쟁점 폴더명', 안건 폴더 바로 아래 파일은 '예시·회의자료'.
경로 칸: 유형별 안건 모음은 그 폴더 기준, 그 밖은 '작성예시_md/안건/' 기준. 안건이 여러 개인 파일은 뒤에 (p.N)이나 (L줄번호)를 붙인다.
검증값(2026-11-22): 2009~2014 md 115개(세부안건 74), 대구사무소 md 7개. v2.0의 새 행 수는 --check로 본다.
사용: python -I -X utf8 index_drafting_examples.py --check
      python -I -X utf8 index_drafting_examples.py --rows --only-new
      python -I -X utf8 index_drafting_examples.py --build out.md
"""
import argparse, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # -I(격리 모드)는 PYTHONIOENCODING을 무시하므로 직접 지정
ap = argparse.ArgumentParser()
ap.add_argument("--vault", default=r"J:\AI 자료")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--check", action="store_true")
g.add_argument("--rows", action="store_true")
g.add_argument("--build")
ap.add_argument("--only-new", action="store_true")
a = ap.parse_args()

VAULT = Path(a.vault)
ROOT = VAULT / "1 documents_md" / "작성예시_md" / "안건"
LEGACY = "유형별 안건 모음(2009-2014)"
PAGE = VAULT / "0 wiki" / "분석" / "안건 작성예시 색인.md"

RE_HEAD = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|\s]+)\s*\|\s*$")  # 첫 줄 머리표(예전 방식)
RE_HEAD_C = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(제?\d{4}-[^|\s]+?호)\s*\|\s*\n\|\s*---", re.M)
RE_HEAD_A = re.compile(r'<tr><th colspan="3">(.+?)</th><th>(제?\d{4}-[^<]*?호)</th></tr>')
RE_HEAD_B = re.compile(r"^## (.+?)\s*(제\d{4}-\S+?호)\s*$", re.M)
RE_MEET = re.compile(r"[<〈]\s*(\d{4}\.\s*\d+\.\s*\d+\.)\s*([^>〉]*?)\s*[>〉]")
RE_AIR = re.compile(r"방송시간</td><td[^>]*>\s*(\d{4}\.\s*\d+\.\s*\d+)")
RE_AIR_T = re.compile(r"방송시간\s+(\d{4}\.\s*\d+\.\s*\d+)")
RE_PTYPE = re.compile(r"프로그램<br>유형</td><td[^>]*>([^<]*)</td>")
RE_PTYPE_T = re.compile(r"프로그램\s*\n?\s*유형\s*\n?\s*(.+?)\s+구분\s")
RE_ART = re.compile(r"(?:\*\*|#{1,6})\s*\d+\.\s*적용\s*조항\s*(?:\*\*)?\s*\n+(.*?)(?=\n\*\*|\n#{1,6} |\Z)", re.S)
RE_ART_PLAIN = re.compile(r"(?m)^[ \t]*(?:-[ \t]*)?\d+\.\s*적용\s*조항[ \t]*\n+(.*?)(?=\n[ \t]*(?:-[ \t]*)?\d+\.\s|\n\*\*|\n#{1,6} |\n붙임|\Z)", re.S)
RE_IMG = re.compile(r"!\[image\]\(images/.*?\.(?:png|jpe?g)\)")
RE_PAGE = re.compile(r"<!-- p\.(\d+) -->")
RE_PATH_IN_PAGE = re.compile(r"`([^`|]+\.md)`")

KIND_KEYS = [("녹취", "녹취록"), ("쟁점", "쟁점 요약"), ("유사사례", "유사사례"), ("권고문", "권고문"),
             ("의결서", "의결서"), ("회의록", "회의록"), ("자문", "자문"), ("붙임", "붙임"),
             ("본문", "본문"), ("참고", "참고자료")]
FEATS = [("시청자 민원", "민원"), ("자문내용", "자문"), ("참고사항", "참고사항"), ("제안사유", "의견진술"), ("녹취", "녹취")]
HEADER = ("| 구분 | 방송사·프로그램(문서명) | 의결번호 | 의결일·차수 | 방송일 | 프로그램유형 | 적용조항(심의 당시) | 포함 내용 | 변환본 경로 |\n"
          "|---|---|---|---|---|---|---|---|---|")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def cell(s):
    return clean(s).replace("|", "\\|")


def unesc(t):
    return t.replace("&lt;", "<").replace("&gt;", ">")


def fields(block):
    """머리·적용조항을 block 글에서 기계로 뽑는다."""
    b = unesc(block)
    mm = RE_MEET.search(b)
    air = RE_AIR.search(b) or RE_AIR_T.search(b)
    pt = RE_PTYPE.search(b) or RE_PTYPE_T.search(b)
    art = RE_ART.search(b) or RE_ART_PLAIN.search(b)
    art_t = ""
    if art:
        t = RE_IMG.sub("", art.group(1))
        t = re.sub(r"의결 - - \d+\(붙임\)", "", t)
        t = clean(t)
        t = clean(re.sub(r"<!--.*?-->", " ", t))  # 쪽 주석은 문장 중간에도 끼므로 먼저 뺀다
        t = re.split(r"\s*(?:<|붙임\s*[:：])", t)[0]  # 표·그림 제목·붙임 목록 앞에서 끊는다
        k = re.search(r"[「｢]", t)  # 사유 문장이 앞에 있으면 조항(「…」부터)을 앞세워 자르지 않게 한다
        if k and k.start() > 0:
            t = t[k.start():]
        art_t = re.sub(r"^[#○\s-]+", "", t)[:300]
    return dict(meet=clean(mm.group(1) + " " + mm.group(2)) if mm else "", air=clean(air.group(1)) if air else "",
                pt=clean(pt.group(1)) if pt else "", art=art_t)


def feats_of(block, rel):
    return " ".join(v for k, v in FEATS if (k in block or k in rel))


def group_and_rel(p):
    """(절 이름, 변환본 경로 칸 값)"""
    r = p.relative_to(ROOT).as_posix()
    parts = r.split("/")
    if parts[0] == LEGACY:
        sub = parts[1:]
        return (sub[0] if len(sub) > 1 else "(폴더 밖)"), "/".join(sub)
    if len(parts) == 1:
        return "예시·회의자료", r
    return parts[0] + " · " + (parts[1] if len(parts) > 2 else "(폴더 밖)"), r


def headers_of(text):
    """세부안건 머리 목록 [(위치, 프로그램, 의결번호)]. 같은 의결번호·프로그램은 처음 것만."""
    hs = []
    for rx in (RE_HEAD_A, RE_HEAD_B, RE_HEAD_C):
        for m in rx.finditer(text):
            prog = clean(unesc(re.sub(r"<br\s*/?>", " ", m.group(1))).replace("&amp;", "&"))
            if prog == "의안번호":  # 본문의 안건 요약표(의안번호 행)는 세부안건 머리가 아니다
                continue
            hs.append((m.start(), prog, clean(m.group(2))))
    hs.sort()
    seen, out = set(), []
    for pos, prog, no in hs:
        if (no, prog) in seen:
            continue
        seen.add((no, prog))
        out.append((pos, prog, no))
    return out


def scan():
    rows = []
    for p in sorted(ROOT.rglob("*.md")):
        rp = p.relative_to(ROOT).as_posix()
        if "/images/" in "/" + rp:
            continue
        group, rel = group_and_rel(p)
        text = p.read_text(encoding="utf-8", errors="replace")
        legacy = rp.startswith(LEGACY + "/")
        hs = [] if legacy else headers_of(text)
        if len(hs) >= 2:  # 안건이 여러 개인 파일: 안건마다 1행
            for i, (pos, prog, no) in enumerate(hs):
                end = hs[i + 1][0] if i + 1 < len(hs) else len(text)
                block = text[pos:end]
                f = fields(block)
                pages = RE_PAGE.findall(text[:pos])
                loc = f"p.{pages[-1]}" if pages else "L" + str(text.count("\n", 0, pos) + 1)
                rows.append(dict(rel=rel, loc=loc, group=group, kind="세부안건", prog=prog, no=no, multi=True,
                                 feats=feats_of(block, ""), **f))
            continue
        lines = text.lstrip().splitlines()
        m = RE_HEAD.match(lines[0]) if lines else None
        if m:
            kind, prog, no = "세부안건", clean(m.group(1)), m.group(2)
        elif len(hs) == 1:
            kind, prog, no = "세부안건", hs[0][1], hs[0][2]
        else:
            stem = p.stem
            kind = next((v for k, v in KIND_KEYS if k in stem), "기타")
            prog, no = stem, ""
        f = fields(text)
        rows.append(dict(rel=rel, loc="", group=group, kind=kind, prog=prog, no=no, multi=False,
                         feats=feats_of(text, rel) if kind == "세부안건" else "", **f))
    return rows


def row_md(r):
    art = r["art"] or ("[확인 필요]" if r["kind"] == "세부안건" else "")
    path = f"`{cell(r['rel'])}`" + (f" ({r['loc']})" if r["loc"] else "")
    return "| " + " | ".join([cell(r["kind"]), cell(r["prog"]), cell(r["no"]), cell(r["meet"]), cell(r["air"]),
                              cell(r["pt"]), cell(art), cell(r["feats"]), path]) + " |"


def page_keys():
    """색인 페이지에 이미 실린 행의 키: 경로만, 또는 (경로, 의결번호, 프로그램)."""
    paths, trip = set(), set()
    if PAGE.exists():
        for line in PAGE.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            m = RE_PATH_IN_PAGE.search(line)
            if not m:
                continue
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            paths.add(m.group(1))
            if len(cells) >= 3:
                trip.add((m.group(1), cells[2], cells[1]))
    return paths, trip


def is_new(r, paths, trip):
    return (r["rel"], cell(r["no"]), cell(r["prog"])) not in trip if r["multi"] else r["rel"] not in paths


rows = scan()
if a.check or a.rows:
    paths, trip = page_keys()
    new = [r for r in rows if is_new(r, paths, trip)]
    now_paths = {r["rel"] for r in rows}
    now_trip = {(r["rel"], cell(r["no"]), cell(r["prog"])) for r in rows if r["multi"]}
    multi_files = {r["rel"] for r in rows if r["multi"]}
    gone = sorted(paths - now_paths)
    gone += sorted(f"{t[0]} / {t[1]} {t[2]}" for t in trip if t[0] in multi_files and t not in now_trip)
    if a.check:
        print(f"md {len(now_paths)}개, 행 {len(rows)}개, 색인에 실린 경로 {len(paths)}개, 새 행 {len(new)}개, 사라진 행 {len(gone)}개")
        for r in new:
            print("  + " + r["group"] + " / " + r["rel"] + (" " + r["no"] + " " + r["prog"] if r["multi"] else ""))
        for p in gone:
            print("  - " + p)
    else:
        sel = new if a.only_new else rows
        by = {}
        for r in sel:
            by.setdefault(r["group"], []).append(r)
        for gname, rs in by.items():  # 절 이름별로 묶어 낸다(파일 순서와 절 순서가 달라도 한 절은 한 번만)
            if a.only_new:
                print(f"\n## {gname}")
            for r in rs:
                print(row_md(r))
else:
    out, groups = [], {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    for gname, rs in groups.items():
        out.append(f"## {gname} ({len(rs)})\n\n{HEADER}")
        out += [row_md(r) for r in rs]
        out.append("")
    Path(a.build).write_text("\n".join(out), encoding="utf-8")
    n = sum(1 for r in rows if r["kind"] == "세부안건")
    print(f"md {len({r['rel'] for r in rows})}개, 행 {len(rows)}개, 세부안건 {n}개, 절 {len(groups)}개 -> {a.build}")
