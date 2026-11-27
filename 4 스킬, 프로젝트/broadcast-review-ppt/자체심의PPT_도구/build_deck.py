#!/usr/bin/env python3
# broadcast-review-ppt toolkit version: 2026-11-25
"""deck_spec.json + 자체심의 템플릿 → 편집 가능한 PPTX와 감사 JSON.

usage: python3 build_deck.py deck_spec.json TEMPLATE.pptx OUT.pptx
템플릿의 원형 슬라이드(표지 1, 구분 2, 단일사례 3, 2사례 4)를 복제해 채우고 원래 슬라이드는 표지만 남긴다.
표지를 뺀 모든 슬라이드 우상단에 쪽 번호(자동 갱신되는 슬라이드 번호 필드)를 넣는다.
"""
from __future__ import annotations

import copy
import io
import json
import re
import sys
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Pt

# ---- 템플릿 도형 매핑(다른 템플릿이면 이 부분만 수정) ----
MAP = {
    "cover": {"slide": 1, "title": "직사각형 6"},
    "section": {"slide": 2, "title": "Google Shape;93;p14", "subtitle": "Google Shape;94;p14"},
    "case": {"slide": 3, "title": "Google Shape;112;p15", "program": "Google Shape;107;p15",
             "datetime": "Google Shape;109;p15", "related": "Google Shape;111;p15",
             "summary": "Google Shape;103;p15", "image": "Picture 3",  # 예시 사진(있으면 삭제)
             "image_card": "Google Shape;101;p15",  # 사진 카드 배경: 이 안쪽에 사진 배치
             "image_box": (545, 136, 362, 378)},  # pt, 카드를 못 찾을 때 쓰는 영역
    "pair": {"slide": 4, "title": "Google Shape;131;p16",
             "left": {"label": "Google Shape;123;p16", "program": "Google Shape;127;p16",
                      "related": "Google Shape;128;p16", "summary": "Google Shape;124;p16"},
             "right": {"label": "Google Shape;125;p16", "program": "Google Shape;129;p16",
                       "related": "Google Shape;130;p16", "summary": "Google Shape;126;p16"}},
}
# 텍스트 상자 수용 한계(폭 pt, 최대 줄 수, 기본 글꼴 pt, 줄간격 배수)
FIT = {
    "title": (798, 1, 30, 1.2), "program": (338, 1, 16, 1.2), "datetime": (338, 1, 16, 1.2),
    "related": (338, 2, 16, 1.2), "summary": (454, 6, 18, 1.6),
    "pair_label": (372, 1, 21, 1.2), "pair_program": (328, 1, 16, 1.2), "pair_summary": (355, 6, 18, 1.2),
}
# 쪽 번호(EMU): 오른쪽 끝을 빨간 줄 끝(571500+11049000)에 맞추고, 글자 아랫선을 제목 글자의 아랫선에 맞춘다.
# 아랫선 = 상자 위쪽 + 글꼴 크기 × 비율(위쪽 정렬·여백 0, Noto Sans KR 실측: 제목 한글 1.074, 숫자 0.983).
# 제목 상자가 없는 구분 슬라이드는 단일 사례 제목(top 571500, 30pt) 기준 위치를 쓴다.
# 제목 상자가 번호 칸을 침범하면 gap만큼 띄워 제목 폭을 줄인다(FIT["title"] 798pt와 같은 값).
PAGE_NO = {"right": 11620500, "width": 762000, "height": 304800, "gap": 152400,
           "title_top": 571500, "title_size": 30, "title_ink": 1.074, "num_ink": 0.983,
           "size": 16, "color": "64748B", "font": "Noto Sans KR"}
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


# ---------------- 슬라이드 복제·삭제 ----------------
def duplicate(prs, src):
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    rid_map = {}
    for rid, rel in src.part.rels.items():
        if rel.reltype in (RT.SLIDE_LAYOUT, RT.NOTES_SLIDE):
            continue
        if rel.is_external:
            rid_map[rid] = new.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            rid_map[rid] = new.part.relate_to(rel.target_part, rel.reltype)
    src_csld, new_csld = src._element.cSld, new._element.cSld
    bg = src_csld.find("{http://schemas.openxmlformats.org/presentationml/2006/main}bg")
    if bg is not None:
        new_csld.insert(0, copy.deepcopy(bg))
    tree = new.shapes._spTree
    for el in src.shapes._spTree:
        if etree.QName(el).localname in ("nvGrpSpPr", "grpSpPr"):
            continue
        dup = copy.deepcopy(el)
        for node in dup.iter():
            for attr in list(node.attrib):
                if attr.startswith("{%s}" % R_NS) and node.attrib[attr] in rid_map:
                    node.attrib[attr] = rid_map[node.attrib[attr]]
        tree.append(dup)
    return new


def delete_slides(prs, slides):
    targets = {id(s.part) for s in slides}
    lst = prs.slides._sldIdLst
    doomed = [sid for sid in lst if id(prs.part.related_part(sid.rId)) in targets]
    for sid in doomed:
        rid = sid.rId
        lst.remove(sid)
        prs.part.drop_rel(rid)


def shape(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    raise KeyError(f"템플릿 도형 없음: {name} (MAP 수정 필요)")


# ---------------- 텍스트 ----------------
def segments(text):
    """'**굵게**' 표기를 (텍스트, 굵게여부) 목록으로."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, None) for p in parts if p]


def set_text(shp, paragraphs, size=None, keep_bold=True):
    """첫 문단·첫 런 서식을 유지하며 문단 목록으로 교체. paragraphs: [str] ('**굵게**' 허용)."""
    txBody = shp.text_frame._txBody
    ps = txBody.findall(A + "p")
    proto_p = ps[0]
    proto_r = proto_p.find(A + "r")
    for p in ps:
        txBody.remove(p)
    for text in paragraphs:
        p = copy.deepcopy(proto_p)
        for child in list(p):
            if etree.QName(child).localname in ("r", "br", "fld"):
                p.remove(child)
        end = p.find(A + "endParaRPr")
        for seg, bold in segments(text):
            r = copy.deepcopy(proto_r)
            r.find(A + "t").text = seg
            rpr = r.find(A + "rPr")
            if bold is not None:
                rpr.set("b", "1")
            elif not keep_bold:
                rpr.set("b", "0")
            if size:
                rpr.set("sz", str(int(size * 100)))
            if end is not None:
                end.addprevious(r)
            else:
                p.append(r)
        txBody.append(p)


def est_lines(text, width_pt, size_pt):
    plain = re.sub(r"\*\*", "", text)
    total = 0
    for para in plain.split("\n"):
        w = 0.0
        for ch in para:
            if ch == " ":
                w += 0.3
            elif ord(ch) < 128:
                w += 0.58
            else:
                w += 1.0
        total += max(1, -(-int(w * size_pt) // int(width_pt)))
    return total


def fit(kind, paragraphs, warns, label):
    width, max_lines, base, _ = FIT[kind]
    text = "\n".join(paragraphs)
    for size in (base, base - 1, base - 2):
        if est_lines(text, width, size) <= max_lines:
            return None if size == base else size
    warns.append(f"{label}: 분량 과다로 넘칠 가능성(추정 {est_lines(text, width, base - 2)}줄/{max_lines}줄), 요약 축약 필요")
    return base - 2


# ---------------- 그림 ----------------
def prepared_image(path):
    im = Image.open(path)
    im.load()
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.convert("RGBA").split()[-1])
        im = bg
    im.thumbnail((1600, 1600))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=88)
    buf.seek(0)
    return buf, im.size


def place_images(slide, paths, box, warns):
    """사진 카드 안에 그림을 최대한 크게 배치한다.
    열 수(1~n)를 바꿔 가며 같은 크기 칸으로 나눠 보고, 가장 작게 나오는 그림이 가장 커지는 배치를 고른다.
    16:9 화면 2~3장이면 보통 위아래 한 줄씩 쌓인다. 남는 세로 공간은 위아래로 고르게 나눈다."""
    left, top, width, height = box
    ok = []
    for p in paths[:3]:
        try:
            ok.append(prepared_image(p))
        except Exception as exc:
            warns.append(f"그림 삽입 실패({Path(p).name}): {exc}")
    if not ok:
        return
    gap, n, best = 6, len(ok), None
    for cols in range(1, n + 1):
        rows = -(-n // cols)
        cw, ch = (width - gap * (cols - 1)) / cols, (height - gap * (rows - 1)) / rows
        sizes = [(iw * min(cw / iw, ch / ih), ih * min(cw / iw, ch / ih)) for _, (iw, ih) in ok]
        score = min(w * h for w, h in sizes)
        if best is None or score > best[0]:
            best = (score, cols, cw, sizes)
    _, cols, cw, sizes = best
    row_h = [max(h for _, h in sizes[r:r + cols]) for r in range(0, n, cols)]
    y = top + (height - sum(row_h) - gap * (len(row_h) - 1)) / 2
    for r, rh in enumerate(row_h):
        for c in range(cols):
            k = r * cols + c
            if k >= n:
                break
            buf, _ = ok[k]
            w, h = sizes[k]
            x = left + c * (cw + gap) + (cw - w) / 2
            slide.shapes.add_picture(buf, Pt(x), Pt(y + (rh - h) / 2), Pt(w), Pt(h))
        y += rh + gap


def add_page_number(slide, number, title=None):
    """우상단에 쪽 번호를 넣는다. PowerPoint의 슬라이드 번호 필드라서 순서를 바꾸면 자동으로 다시 매겨진다.
    템플릿 마스터가 머리글/바닥글을 꺼 두어(Google Slides 변환본) 삽입 메뉴로는 번호가 안 들어가므로 직접 넣는다."""
    g = PAGE_NO
    left = g["right"] - g["width"]
    title_top, title_size = g["title_top"], g["title_size"]
    if title is not None:
        title_top = title.top
        runs = title.text_frame.paragraphs[0].runs
        if runs and runs[0].font.size:
            title_size = runs[0].font.size.pt
        if title.left + title.width > left - g["gap"]:
            title.width = Emu(left - g["gap"] - title.left)
    top = title_top + Pt(g["title_ink"] * title_size - g["num_ink"] * g["size"])
    box = slide.shapes.add_textbox(Emu(left), Emu(top), Emu(g["width"]), Emu(g["height"]))
    box.name = "쪽 번호"
    tf = box.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.word_wrap = False
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.RIGHT
    fld = etree.SubElement(para._p, A + "fld", id="{5C1E8F2A-3B4D-4E6F-9A1B-2C3D4E5F6A7B}", type="slidenum")
    rpr = etree.SubElement(fld, A + "rPr", lang="ko-KR", sz=str(g["size"] * 100), b="0")
    fill = etree.SubElement(rpr, A + "solidFill")
    etree.SubElement(fill, A + "srgbClr", val=g["color"])
    for tag in ("latin", "ea", "cs"):
        etree.SubElement(rpr, A + tag, typeface=g["font"])
    etree.SubElement(fld, A + "t").text = str(number)


def set_notes(slide, lines):
    if lines:
        slide.notes_slide.notes_text_frame.text = "\n".join(lines)


# ---------------- 슬라이드 종류별 ----------------
def build_case(prs, proto, s, base_dir):
    m, warns = MAP["case"], list(s.get("review_warnings", []))
    slide = duplicate(prs, proto)
    for key in ("title", "program", "broadcast_datetime", "related_provisions", "main_violation"):
        if not str(s.get(key, "")).strip():
            s[key] = "확인 필요"
            warns.append(f"{key} 누락 → '확인 필요' 표기")
    set_text(shape(slide, m["title"]), [s["title"]], fit("title", [s["title"]], warns, "제목"))
    set_text(shape(slide, m["program"]), [s["program"]], fit("program", [s["program"]], warns, "프로그램명"))
    set_text(shape(slide, m["datetime"]), [s["broadcast_datetime"]], fit("datetime", [s["broadcast_datetime"]], warns, "방송일시"))
    set_text(shape(slide, m["related"]), [s["related_provisions"]], fit("related", [s["related_provisions"]], warns, "관련조항"))
    summary = [s["main_violation"]] + ([s["caveat"]] if s.get("caveat") else [])
    set_text(shape(slide, m["summary"]), summary, fit("summary", summary, warns, "주요 위반내용"), keep_bold=False)
    box = m["image_box"]
    try:
        card = shape(slide, m["image_card"])
        pad = 8
        box = (card.left.pt + pad, card.top.pt + pad, card.width.pt - 2 * pad, card.height.pt - 2 * pad)
    except KeyError:
        pass
    try:
        old = shape(slide, m["image"])
        old._element.getparent().remove(old._element)
    except KeyError:
        pass
    imgs = [str((base_dir / p).resolve()) if not Path(p).is_absolute() else p for p in s.get("images", [])]
    place_images(slide, imgs, box, warns)
    if not imgs:
        warns.append("방송화면 없음(이미지 영역 비움)")
    set_notes(slide, ["[자동 검토]"] + [f"- {w}" for w in warns] if warns else [])
    return slide, warns


def build_pair(prs, proto, s):
    m, warns = MAP["pair"], list(s.get("review_warnings", []))
    slide = duplicate(prs, proto)
    set_text(shape(slide, m["title"]), [s["title"]], fit("title", [s["title"]], warns, "제목"))
    for side, c in zip(("left", "right"), s["cases"]):
        mm = m[side]
        set_text(shape(slide, mm["label"]), [c["label"]], fit("pair_label", [c["label"]], warns, f"{side} 소제목"))
        prog = f"프로그램: {c.get('program') or '확인 필요'}"
        rel = f"관련조항: {c.get('related_provisions') or '확인 필요'}"
        set_text(shape(slide, mm["program"]), [prog], fit("pair_program", [prog], warns, f"{side} 프로그램"))
        set_text(shape(slide, mm["related"]), [rel], fit("pair_program", [rel], warns, f"{side} 관련조항"))
        set_text(shape(slide, mm["summary"]), [c["main_violation"]], fit("pair_summary", [c["main_violation"]], warns, f"{side} 요약"), keep_bold=False)
        if c.get("broadcast_datetime"):
            pass  # 2사례 레이아웃에는 방송일시 칸이 없음 → 노트에 기록
        warns += [f"{side}: {w}" for w in c.get("review_warnings", [])]
    notes = ["[자동 검토]"] + [f"- {w}" for w in warns] if warns else []
    notes += [f"{c['label']} 방송일시: {c.get('broadcast_datetime', '확인 필요')}" for c in s["cases"]]
    set_notes(slide, notes)
    return slide, warns


def main():
    spec_path, tpl, out = map(Path, sys.argv[1:4])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    prs = Presentation(str(tpl))
    originals = list(prs.slides)
    protos = {k: originals[v["slide"] - 1] for k, v in MAP.items() if v["slide"] <= len(originals)}
    cover = protos["cover"]
    station = spec.get("station") or "방송사"
    set_cover_station(shape(cover, MAP["cover"]["title"]), station)

    audit = {"schema_version": "2.0", "template": str(tpl), "output": str(out), "station": station, "slides": []}
    sec_no = 0
    built = []  # (슬라이드, 종류): 쪽 번호용
    for s in spec["slides"]:
        kind = s.get("type", "case")
        if kind == "section":
            sec_no += 1
            slide = duplicate(prs, protos["section"])
            title = s["title"] if re.match(r"^\d+\.", s["title"]) else f"{sec_no}. {s['title']}"
            set_text(shape(slide, MAP["section"]["title"]), [title])
            set_text(shape(slide, MAP["section"]["subtitle"]), [s.get("subtitle", "")])
            built.append((slide, "section"))
            audit["slides"].append({"type": "section", "title": title})
        elif kind == "pair":
            slide, w = build_pair(prs, protos["pair"], s)
            built.append((slide, "pair"))
            audit["slides"].append({"type": "pair", "title": s["title"], "review_warnings": w})
        else:
            slide, w = build_case(prs, protos["case"], s, spec_path.parent)
            built.append((slide, "case"))
            audit["slides"].append({"type": "case", "title": s.get("title"), "program": s.get("program"),
                                    "broadcast_datetime": s.get("broadcast_datetime"),
                                    "related_provisions": s.get("related_provisions"),
                                    "images": s.get("images", []), "review_warnings": w,
                                    "source_content": s.get("source_content", ""),
                                    "source_opinion": s.get("source_opinion", "")})
    delete_slides(prs, [sl for sl in originals if sl is not cover])
    for number, (slide, kind) in enumerate(built, start=2):  # 1쪽은 표지(번호 없음)
        title = shape(slide, MAP[kind]["title"]) if kind in ("case", "pair") else None
        add_page_number(slide, number, title)
    prs.save(str(out))
    audit["slide_count"] = len(prs.slides)
    audit["warning_count"] = sum(len(x.get("review_warnings", [])) for x in audit["slides"])
    out.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {out} slides={audit['slide_count']} warnings={audit['warning_count']}")
    for x in audit["slides"]:
        if x.get("review_warnings"):
            print(f"  [{x['type']}] {x['title']}: {x['review_warnings']}")


def set_cover_station(shp, station):
    """표지: 템플릿의 문단·서식(부제·기관명 줄 등)은 그대로 두고, 글자가 있는 첫 문단(방송사명)만 바꾼다."""
    for p in shp.text_frame.paragraphs:
        if p.runs and p.text.strip():
            p.runs[0].text = station
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            return
    raise KeyError("표지 제목 상자에 방송사명 문단이 없음 (템플릿 확인 필요)")


if __name__ == "__main__":
    main()
