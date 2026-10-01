# -*- coding: utf-8 -*-
"""해설집(2016) PDF -> Markdown 재변환 (펼침면 좌우 분리, 옆면 탭 제거, 문단 재구성)."""
import re, sys
import pypdfium2 as pdfium

SRC = sys.argv[1]
OUT = sys.argv[2]
pdf = pdfium.PdfDocument(SRC)

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
TAG_RE = re.compile(r"^(사례|판결|법령|참고)$")
ART_RE = re.compile(r"^제\d+조(의\d+)?\([^)]*\)\s*$")
SEC_RE = re.compile(r"^제\d+절(의\d+)?\s*\S.*$")
HDR_L = re.compile(r"^\d{1,3}\s*방송심의에 관한 규정 해설집\s*$")
HDR_R = re.compile(r"^\d{1,3}\s*$")
ZW = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)


def item_kind(t):
    s = t.lstrip("▹ ").strip()
    if s.startswith(("「", "『")) and "[" not in s:
        return "법령"
    if "판결" in s or "선고" in s or "결정)" in s:
        return "판결"
    if re.search(r"<[^>]+>\s*\((19|20)\d\d\.", s):
        return "사례"
    return "참고"


def half_lines(tp, L, R, h):
    t = tp.get_text_bounded(left=L, bottom=0, right=R, top=h).translate(ZW)
    out = []
    for raw in t.split("\n"):
        line = raw.rstrip("\r")
        s = line.strip()
        if not s or len(s) <= 1:
            continue
        if HDR_L.match(s) or HDR_R.match(s) or TAG_RE.match(s):
            continue
        line = re.sub(r"\s제\d절$", " ", line)   # 첫 줄 끝에 붙는 옆면 탭 '제1절'
        out.append(line)
    return out


def is_divider(lines):
    ss = [l.strip() for l in lines]
    return bool(ss) and SEC_RE.match(ss[0]) and all(re.match(r"^제\d+조(의\d+)?\s", x) for x in ss[1:]) and len(ss) > 1


def ends_para(prev):
    p = prev.rstrip()
    if p.endswith("\n  ") or prev.endswith("\n  "):
        return False
    return (p.endswith((".", "]", "다.", "”", "\"")) and not p.endswith("선고")) or \
           (p.lstrip().startswith("▹") and p.endswith(")"))


def starts_block(s):
    return s.startswith("▹") or s[0] in CIRCLED or ART_RE.match(s) or re.match(r"^\d+\.\s", s) \
        or re.match(r"^[^:]{2,20}\s:\s", s)


md = ["# 방송심의에 관한 규정 해설집", "",
      "<!-- 재변환본: 원본 PDF(방송심의에관한 규정 해설집(2016).pdf)에서 펼침면을 좌우로 나누어 추출. "
      "쪽 표시는 '책 N쪽 (PDF p.M 왼쪽/오른쪽)'. 책 쪽 = 왼쪽 2M-2, 오른쪽 2M-1(머리글 쪽번호 171개로 검증). 2026-09-21 Claude 재변환 -->", ""]
for pi in range(len(pdf)):
    page = pdf[pi]
    w, h = page.get_size()
    tp = page.get_textpage()
    halves = [("왼쪽", 30, w / 2 - 15), ("오른쪽", w / 2 + 15, w - 35)] if w > h else [("", 0, w)]
    for side, L, R in halves:
        raw = tp.get_text_bounded(left=L, bottom=0, right=R, top=h).translate(ZW)
        # 책 쪽번호: 머리글에서 읽는다
        m = re.search(r"^\s*(\d{1,3})(\s*방송심의에 관한 규정 해설집)?\s*$", raw, re.M)
        # 머리글이 없는 쪽(간지·부록 등)은 검증된 공식(왼쪽 2p-2, 오른쪽 2p-1)으로 채운다
        calc = 2 * (pi + 1) - 2 + (1 if side == "오른쪽" else 0)
        bookp = m.group(1) if m else f"{calc}(추정)"
        lines = half_lines(tp, L, R, h)
        if not lines:
            continue
        loc = f"책 {bookp}쪽 (PDF p.{pi + 1}{' ' + side if side else ''})"
        md.append(f"<!-- {loc} -->")
        if is_divider(lines):
            md.append(f"## {lines[0].strip()}")
            md.append("")
            md += [f"- {l.strip()}" for l in lines[1:]]
            md.append("")
            continue
        paras, cur, prev_line = [], "", ""
        in_item, title_done = False, False
        block_start = 0            # 조문 박스가 시작된 문단 위치(제목을 이 앞으로 옮긴다)
        for li, line in enumerate(lines):
            if li == 0 and side == "왼쪽":
                m0 = re.match(r"^제\d+(?=[▹①-⑮])", line)
                if m0:   # 첫 줄에 끼어든 옆면 탭 '제1 … 절'
                    line = line[m0.end():]
                    line = re.sub(r"\s절\s*$", " ", line)
                    line = re.sub(r"(?<=\))\s?절(?=\S)", "", line, count=1)
            s = line.strip()
            if SEC_RE.match(s) and len(s) < 20:
                continue            # 쪽 끝의 '제2절 객관성' 같은 탭 표기
            if ART_RE.match(s):
                if cur:
                    paras.append(cur); cur = ""
                paras.insert(block_start, f"### {s}")
                block_start = len(paras)
                in_item = False
                continue
            unclosed = cur.count("[") > cur.count("]")
            is_result = re.match(r"^\[\d{4}\.", s) is not None
            if cur and not unclosed and not is_result and (ends_para(cur) or starts_block(s)) \
                    and not (in_item and not title_done):
                paras.append(cur); cur = ""; in_item = False
            if not cur:
                if s[0] in CIRCLED:
                    block_start = len(paras)
                if s.startswith("▹"):
                    cur = f"- **[{item_kind(s)}]** {s.lstrip('▹ ').strip()}"
                    in_item, title_done = True, s.endswith(")")
                    if title_done:
                        cur += "  \n  "
                else:
                    cur = s
            else:
                word_end = prev_line.rstrip().endswith(("및", "등", ",")) or \
                    (cur.count("[") > cur.count("]") and cur.rstrip().endswith("."))
                sep = "" if cur.endswith("\n  ") else (" " if (prev_line.endswith(" ") or is_result or word_end) else "")
                cur = cur + sep + s
                if in_item and not title_done and s.endswith(")"):
                    title_done = True
                    cur += "  \n  "
            prev_line = line
            if cur.rstrip().endswith("]") and not (cur.count("[") > cur.count("]")):
                paras.append(cur.rstrip()); cur = ""; in_item = False
                block_start = len(paras)
        if cur:
            paras.append(cur.rstrip())
        for p in paras:
            md.append(p)
            md.append("")
open(OUT, "w", encoding="utf-8").write("\n".join(md).rstrip() + "\n")
print("written", OUT)
