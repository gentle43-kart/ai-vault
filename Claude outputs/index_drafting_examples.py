# -*- coding: utf-8 -*-
"""
index_drafting_examples.py v1.0 (2026-11-22, Claude)

목적: 위키 분석 페이지 '안건 작성예시 색인'의 표를 만들고, 색인에 빠진 예시 파일(추가분)을 찾는다.
      '유형별 안건 모음(2009-2014)' 변환본 md의 머리표(방송사·프로그램, 의결번호, 의결일·차수, 방송일,
      프로그램유형)와 '적용조항' 절을 기계로 뽑는다. 판단·요약은 하지 않는다(그 칸은 사람이 채운다).
입력: <vault>/1 documents_md/작성예시_md/안건/유형별 안건 모음(2009-2014)/ 아래 md 전체(images 폴더 제외),
      <vault>/0 wiki/분석/안건 작성예시 색인.md (--check·--rows에서 이미 실린 경로를 읽는 용도)
출력: --check  표준출력에 새 파일·사라진 파일 목록(아무것도 쓰지 않는다)
      --rows   표준출력에 색인 표 행(--only-new면 색인에 없는 파일만)
      --build 경로  전체 표(쟁점 폴더별 절)를 그 경로 파일로 쓴다(위키 페이지 본문 조립용)
쓰기 범위: --build가 지정한 파일뿐. 위키·자료창고는 고치지 않는다.
검증값(2026-11-22): md 115개, 그중 머리표가 있는 세부안건 75개, 묶음 27개(쟁점 폴더 26개 + 폴더 밖 문서 5개의 '(폴더 밖)').
        새 예시를 넣은 뒤에는 --check로 추가분을 보고, 반영하면 다시 --check가 0건이어야 한다.
사용: python -I index_drafting_examples.py --check
      python -I index_drafting_examples.py --rows --only-new
      python -I index_drafting_examples.py --build out.md
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
BASE = VAULT / "1 documents_md" / "작성예시_md" / "안건" / "유형별 안건 모음(2009-2014)"
PAGE = VAULT / "0 wiki" / "분석" / "안건 작성예시 색인.md"

RE_HEAD = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|\s]+)\s*\|\s*$")
RE_MEET = re.compile(r"[<〈]\s*(\d{4}\.\s*\d+\.\s*\d+\.)\s*([^>〉]*?)\s*[>〉]")
RE_AIR = re.compile(r"방송시간</td><td[^>]*>\s*(\d{4}\.\s*\d+\.\s*\d+)")
RE_PTYPE = re.compile(r"프로그램<br>유형</td><td[^>]*>([^<]*)</td>")
RE_ART = re.compile(r"(?:\*\*|#{1,6})\s*\d+\.\s*적용\s*조항\s*(?:\*\*)?\s*\n+(.*?)(?=\n\*\*|\n#{1,6} |\Z)", re.S)
RE_PATH_IN_PAGE = re.compile(r"`([^`|]+\.md)`")

KIND_KEYS = [("녹취", "녹취록"), ("쟁점", "쟁점 요약"), ("유사사례", "유사사례"), ("권고문", "권고문"),
             ("의결서", "의결서"), ("회의록", "회의록"), ("자문", "자문"), ("붙임", "붙임"),
             ("본문", "본문"), ("참고", "참고자료")]
FEATS = [("시청자 민원", "민원"), ("자문내용", "자문"), ("참고사항", "참고사항"), ("제안사유", "의견진술"), ("녹취", "녹취")]


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def cell(s):
    return clean(s).replace("|", "\\|")


def scan():
    rows = []
    for p in sorted(BASE.rglob("*.md")):
        rel = p.relative_to(BASE).as_posix()
        if "images/" in rel:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.lstrip().splitlines()
        m = RE_HEAD.match(lines[0]) if lines else None
        parts = rel.split("/")
        group = parts[0] if len(parts) > 1 else "(폴더 밖)"
        stem = p.stem
        if m:
            kind, prog, no = "세부안건", clean(m.group(1)), m.group(2)
        else:
            kind = next((v for k, v in KIND_KEYS if k in stem), "기타")
            prog, no = stem, ""
        mm, air, pt, art = RE_MEET.search(text), RE_AIR.search(text), RE_PTYPE.search(text), RE_ART.search(text)
        feats = [v for k, v in FEATS if (k in text or k in rel)] if m else []
        rows.append(dict(rel=rel, group=group, kind=kind, prog=prog, no=no,
                         meet=clean(mm.group(1) + " " + mm.group(2)) if mm else "",
                         air=clean(air.group(1)) if air else "",
                         pt=clean(pt.group(1)) if pt else "",
                         art=re.sub(r"^[#○\s]+", "", clean(art.group(1)))[:200] if art else "", feats=" ".join(feats)))
    return rows


def row_md(r):
    art = r["art"] or ("[확인 필요]" if r["kind"] == "세부안건" else "")
    return "| " + " | ".join([cell(r["kind"]), cell(r["prog"]), cell(r["no"]), cell(r["meet"]), cell(r["air"]),
                              cell(r["pt"]), cell(art), cell(r["feats"]), f"`{cell(r['rel'])}`"]) + " |"


HEADER = ("| 구분 | 방송사·프로그램(문서명) | 의결번호 | 의결일·차수 | 방송일 | 프로그램유형 | 적용조항(심의 당시) | 포함 내용 | 변환본 경로 |\n"
          "|---|---|---|---|---|---|---|---|---|")

rows = scan()
if a.check or a.rows:
    listed = set(RE_PATH_IN_PAGE.findall(PAGE.read_text(encoding="utf-8"))) if PAGE.exists() else set()
    new = [r for r in rows if r["rel"] not in listed]
    gone = sorted(listed - {r["rel"] for r in rows})
    if a.check:
        print(f"md {len(rows)}개, 색인에 실린 경로 {len(listed)}개, 새 파일 {len(new)}개, 사라진 파일 {len(gone)}개")
        for r in new:
            print("  + " + r["rel"])
        for p in gone:
            print("  - " + p)
    else:
        for r in (new if a.only_new else rows):
            print(row_md(r))
else:
    out, cur = [], None
    groups = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r)
    for gname, rs in groups.items():
        out.append(f"## {gname} ({len(rs)})\n\n{HEADER}")
        out += [row_md(r) for r in rs]
        out.append("")
    Path(a.build).write_text("\n".join(out), encoding="utf-8")
    n = sum(1 for r in rows if r["kind"] == "세부안건")
    print(f"md {len(rows)}개, 세부안건 {n}개, 폴더 {len(groups)}개 -> {a.build}")
