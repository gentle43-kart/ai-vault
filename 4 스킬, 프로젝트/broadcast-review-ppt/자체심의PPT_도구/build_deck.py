#!/usr/bin/env python3
# broadcast-review-ppt toolkit version: 2026-10-26
"""deck_spec.json + 자체심의 템플릿 → 편집 가능한 PPTX와 감사 JSON.

usage: python3 build_deck.py deck_spec.json TEMPLATE.pptx OUT.pptx
템플릿의 원형 슬라이드(표지 1, 구분 2, 단일사례 3, 2사례 4)를 복제해 채우고 원래 슬라이드는 표지만 남긴다.
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
from pptx.util import Pt

# ---- 템플릿 도형 매핑(다른 템플릿이면 이 부분만 수정) ----
MAP = {
    "cover": {"slide": 1, "title": "직사각형 6"},
    "section": {"slide": 2, "title": "Google Shape;93;p14", "subtitle": "Google Shape;94;p14"},
    "case": {"slide": 3, "title": "Google Shape;112;p15", "program": "Google Shape;107;p15",
             "datetime": "Google Shape;109;p15", "related": "Google Shape;111;p15",
             "summary": "Google Shape;103;p15", "image": "Picture 3",  # 예시 사진(있으면 삭제)
             "image_card": "Google Shape;101;p15",  # 사진 카드 배경: 이 안쪽에 사진 배치
             "image_box": (545, 168, 362, 284)},  # pt, 카드를 못 찾을 때 쓰는 영역
    "pair": {"slide": 4, "title": "Google Shape;131;p16",
             "left": {"label": "Google Shape;123;p16", "program": "Google Shape;127;p16",
                      "related": "Google Shape;128;p16", "summary": "Google Shape;124;p16"},
             "right": {"label": "Google Shape;125;p16", "program": "Google Shape;129;p16",
                       "related": "Google Shape;130;p16", "summary": "Google Shape;126;p16"}},
}
# 텍스트 상자 수용 한계(폭 pt, 최대 줄 수, 기본 글꼴 pt, 줄간격 배수)
FIT = {
    "title": (914, 1, 30, 1.2), "program": (338, 1, 16, 1.2), "datetime": (338, 1, 16, 1.2),
    "related": (338, 2, 16, 1.2), "summary": (454, 6, 18, 1.6),
    "pair_label": (372, 1, 21, 1.2), "pair_program": (328, 1, 16, 1.2), "pair_summary": (355, 6, 18, 1.2),
}
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
    left, top, width, height = box
    ok = []
    for p in paths[:3]:
        try:
            ok.append(prepared_image(p))
        except Exception as exc:
            warns.append(f"그림 삽입 실패({Path(p).name}): {exc}")
    gap = 6
    n = len(ok)
    for i, (buf, (iw, ih)) in enumerate(ok):
        if n == 1:
            bx, by, bw, bh = left, top, width, height
        elif n == 2:
            bh = (height - gap) / 2
            bx, by, bw = left, top + i * (bh + gap), width
        else:
            if i == 0:
                bx, by, bw, bh = left, top, width, (height - gap) * 0.58
            else:
                bw, bh = (width - gap) / 2, (height - gap) * 0.42
                bx, by = left + (i - 1) * (bw + gap), top + height - bh
        scale = min(bw / iw, bh / ih)
        w, h = iw * scale, ih * scale
        slide.shapes.add_picture(buf, Pt(bx + (bw - w) / 2), Pt(by + (bh - h) / 2), Pt(w), Pt(h))


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
    # 표지: 1줄 방송사명, 2줄 '자체심의 참고사항'(둘 다 표지 제목 서식). 괄호 부제 줄은 두지 않는다.
    set_text(shape(cover, MAP["cover"]["title"]), [station, "자체심의 참고사항"])

    audit = {"schema_version": "2.0", "template": str(tpl), "output": str(out), "station": station, "slides": []}
    sec_no = 0
    for s in spec["slides"]:
        kind = s.get("type", "case")
        if kind == "section":
            sec_no += 1
            slide = duplicate(prs, protos["section"])
            title = s["title"] if re.match(r"^\d+\.", s["title"]) else f"{sec_no}. {s['title']}"
            set_text(shape(slide, MAP["section"]["title"]), [title])
            set_text(shape(slide, MAP["section"]["subtitle"]), [s.get("subtitle", "")])
            audit["slides"].append({"type": "section", "title": title})
        elif kind == "pair":
            _, w = build_pair(prs, protos["pair"], s)
            audit["slides"].append({"type": "pair", "title": s["title"], "review_warnings": w})
        else:
            _, w = build_case(prs, protos["case"], s, spec_path.parent)
            audit["slides"].append({"type": "case", "title": s.get("title"), "program": s.get("program"),
                                    "broadcast_datetime": s.get("broadcast_datetime"),
                                    "related_provisions": s.get("related_provisions"),
                                    "images": s.get("images", []), "review_warnings": w,
                                    "source_content": s.get("source_content", ""),
                                    "source_opinion": s.get("source_opinion", "")})
    delete_slides(prs, [sl for sl in originals if sl is not cover])
    prs.save(str(out))
    audit["slide_count"] = len(prs.slides)
    audit["warning_count"] = sum(len(x.get("review_warnings", [])) for x in audit["slides"])
    out.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {out} slides={audit['slide_count']} warnings={audit['warning_count']}")
    for x in audit["slides"]:
        if x.get("review_warnings"):
            print(f"  [{x['type']}] {x['title']}: {x['review_warnings']}")



if __name__ == "__main__":
    main()
