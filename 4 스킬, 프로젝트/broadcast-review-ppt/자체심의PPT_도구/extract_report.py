#!/usr/bin/env python3
# broadcast-review-ppt toolkit version: 2026-10-26
"""모니터 보고서(HWPX/HWP/DOCX/TXT/MD/PDF)를 사례 단위 JSON으로 추출한다.

출력은 '원자료 추출본'이며 요약·제목은 만들지 않는다(제목·요약은 Claude가 작성).
usage: python3 extract_report.py REPORT -o extracted.json --img-dir images/
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote

PREFIX = r"^\s*(?:[■□●○▪▶◦·\-]|\d{1,2}[.)])*\s*"
# 라벨 뒤에는 공백·콜론·줄끝만 허용한다('의견을 수렴' 같은 본문 문장을 라벨로 오인하지 않도록).
_LABELS = [
    ("ignore", r"심의규정\s*위반사항\s*및\s*특이사항"),
    ("program", r"(?:프로그램\s*(?:명칭|명)|프로그램\s*\(등급\)|프\s*로\s*그\s*램\s*(?:명|\(등급\))?)"),
    ("date", r"방송\s*(?:일자|일시|일)"),
    ("span", r"방송\s*시간"),
    ("time", r"(?:방송\s*시각|시\s*각)"),
    ("related", r"(?:심의\s*규정|심\s*의\s*규\s*정|관련\s*조항|관련\s*규정|위반\s*조항)"),
    ("content", r"방송\s*내용(?:\s*-\s*특이사항)?"),
    ("opinion", r"(?:(?:문제\s*제기\s*및\s*)?의견|검토\s*의견|모니터\s*의견)"),
    ("images", r"방송\s*화면(?:\s*\(필요시\s*첨부\))?"),
    ("ignore", r"(?:프로그램\s*(?:유형|종류|장르|성격|형태)|방송\s*(?:지역|구분|형태|분야|시점)|방\s*송\s*광\s*고|필\s*러|특\s*이\s*사\s*항)"),
    ("station", r"(?:방송사\s*명칭|방송사명|방송사|채널명|채\s*널)"),
]
LABELS = [(k, re.compile(PREFIX + p + r"(?=$|[\s:：])\s*[:：]?\s*(.*)$")) for k, p in _LABELS]
STATION_RE = re.compile(r"(대구\s*MBC|안동\s*MBC|포항\s*MBC|TBC|KBS\s*대구|대구\s*KBS|KBS|MBC|SBS|EBS|대구\s*CBS|CBS|TBN|BBS|PBC|YTN|JTBC|MBN|TV조선|채널A)")
IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def clean(text: str) -> str:
    text = (text or "").replace("\r", "").replace("\t", " ")
    text = re.sub(r"[\x00\x0b\x0c]", " ", text)
    text = re.sub(r"[ \u00a0\u3000]+", " ", text)
    return text.strip()


# ---------- readers: 모두 [(text, [image_path...]), ...] 블록 목록을 돌려준다 ----------

def read_hwpx(path: Path, img_dir: Path) -> list[tuple[str, list[str]]]:
    from lxml import etree

    blocks: list[tuple[str, list[str]]] = []
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        items: dict[str, str] = {}
        for man in [n for n in names if n.lower().endswith("content.hpf")]:
            root = etree.fromstring(zf.read(man))
            base = str(Path(man).parent)
            for it in root.iter("{*}item"):
                iid, href = it.get("id"), it.get("href")
                if not iid or not href:
                    continue
                href = unquote(href)
                for cand in (href, f"{base}/{href}".lstrip("./")):
                    if cand in names:
                        items[iid] = cand
                        break
        copied: dict[str, str] = {}

        def export(member: str) -> str | None:
            if Path(member).suffix.lower() not in IMG_EXT | {".wmf", ".emf"}:
                return None
            if member not in copied:
                img_dir.mkdir(parents=True, exist_ok=True)
                out = img_dir / f"{len(copied) + 1:03d}_{Path(member).name}"
                out.write_bytes(zf.read(member))
                copied[member] = str(out)
            return copied[member]

        sections = sorted(
            [n for n in names if re.search(r"(^|/)section\d+\.xml$", n, re.I)],
            key=lambda n: int(re.search(r"section(\d+)", n, re.I).group(1)),
        )
        for sec in sections:
            root = etree.fromstring(zf.read(sec))
            for p in root.iter("{*}p"):
                # 이 문단에 직접 속한 텍스트·그림만 취한다(표 안 문단은 따로 순회되므로 중복 방지)
                texts, imgs = [], []
                for node in p.iter("{*}t", "{*}img"):
                    owner = next((a for a in node.iterancestors() if etree.QName(a).localname == "p"), None)
                    if owner is not p:
                        continue
                    if etree.QName(node).localname == "t":
                        texts.append("".join(node.itertext()))
                    else:
                        ref = node.get("binaryItemIDRef") or node.get("binaryItemID") or node.get("idRef")
                        member = items.get(ref) if ref else None
                        if member is None and ref:
                            member = next((n for n in names if Path(n).stem == ref), None)
                        exported = export(member) if member else None
                        if exported and exported not in imgs:
                            imgs.append(exported)
                txt = clean("".join(texts))
                if txt or imgs:
                    blocks.append((txt, imgs))
    return blocks


def read_hwp(path: Path, img_dir: Path) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """바이너리 HWP: 텍스트는 hwp5txt, 그림은 BinData 일괄 추출(사례 매핑 불가)."""
    notes = []
    exe = shutil.which("hwp5txt")
    if not exe:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "pyhwp"], check=False)
        exe = shutil.which("hwp5txt")
    if not exe:
        raise SystemExit("HWP 읽기 실패: pyhwp 설치 불가. 한글에서 HWPX로 저장해 다시 첨부해 달라고 요청할 것.")
    res = subprocess.run([exe, str(path)], capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        raise SystemExit(f"HWP 읽기 실패({res.stderr.strip()[:200]}). 배포용·암호 문서일 수 있음. HWPX 저장본을 요청할 것.")
    blocks = [(clean(line), []) for line in res.stdout.splitlines() if clean(line)]
    try:
        import olefile, zlib

        ole = olefile.OleFileIO(str(path))
        bins = [e for e in ole.listdir() if e and e[0] == "BinData"]
        img_dir.mkdir(parents=True, exist_ok=True)
        for e in bins:
            raw = ole.openstream(e).read()
            for fn in (lambda b: zlib.decompress(b, -15), lambda b: b):
                try:
                    data = fn(raw)
                    break
                except Exception:
                    continue
            (img_dir / e[-1]).write_bytes(data)
        if bins:
            notes.append(f"HWP 원본에서 그림 {len(bins)}개를 추출했으나 사례별 위치는 알 수 없음(unassigned_images). 사례 매핑이 필요하면 HWPX 저장본을 요청하거나 그림을 직접 확인해 배정할 것.")
    except Exception as exc:  # 그림 추출 실패는 치명적이지 않음
        notes.append(f"HWP 그림 추출 실패: {exc}")
    return blocks, notes


def read_docx(path: Path, img_dir: Path) -> list[tuple[str, list[str]]]:
    from lxml import etree

    blocks = []
    with zipfile.ZipFile(path) as zf:
        rels = etree.fromstring(zf.read("word/_rels/document.xml.rels"))
        rmap = {r.get("Id"): "word/" + r.get("Target").lstrip("/").replace("word/", "") for r in rels}
        root = etree.fromstring(zf.read("word/document.xml"))
        n = 0
        for p in root.iter("{*}p"):
            txt = clean("".join(t.text or "" for t in p.iter("{*}t")))
            imgs = []
            for blip in p.iter("{*}blip"):
                rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                member = rmap.get(rid)
                if member and member in zf.namelist():
                    n += 1
                    img_dir.mkdir(parents=True, exist_ok=True)
                    out = img_dir / f"{n:03d}_{Path(member).name}"
                    out.write_bytes(zf.read(member))
                    imgs.append(str(out))
            if txt or imgs:
                blocks.append((txt, imgs))
    return blocks


def read_plain(path: Path) -> list[tuple[str, list[str]]]:
    if path.suffix.lower() == ".pdf":
        text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    else:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    return [(clean(l), []) for l in text.splitlines() if clean(l)]


# ---------- parser ----------

def fix_split_labels(blocks):
    """'심/의/규/정'처럼 한 글자씩 줄바꿈된 라벨을 합친다."""
    out, i = [], 0
    while i < len(blocks):
        merged = False
        for n in (4, 3, 2):
            seg = blocks[i:i + n]
            if len(seg) == n and all(len(t) == 1 and not im for t, im in seg):
                word = "".join(t for t, _ in seg)
                if word in {"심의규정", "특이사항", "프로그램", "방송일시", "관련조항", "방송내용"}:
                    out.append((word, []))
                    i += n
                    merged = True
                    break
        if not merged:
            out.append(blocks[i])
            i += 1
    return out


def new_case(station=""):
    return {"station": station, "program": "", "date": "", "span": "", "time": "", "related": "",
            "content": "", "opinion": "", "images": []}


def parse(blocks):
    cases, cur, active = [], new_case(), None
    for text, imgs in fix_split_labels(blocks):
        hit = None
        for line in [text]:
            for key, pat in LABELS:
                m = pat.match(line)
                if m:
                    hit = (key, m.group(1).strip())
                    break
        if hit:
            key, rest = hit
            if key in {"program", "station"} and cur["program"] and (cur["content"] or cur["opinion"]):
                cases.append(cur)
                cur = new_case(cur["station"])
            active = key
            if key not in {"images", "ignore"}:
                cur[key] = rest
        elif text and active and active not in {"images", "ignore"}:
            if active == "station" and cur["station"]:
                active = None  # 방송사는 한 줄 필드: 값이 이미 있으면 이어지는 줄을 붙이지 않음
            elif not (active == "program" and text == "(등급)"):
                cur[active] = f"{cur[active]}\n{text}".strip()
        for im in imgs:
            if im not in cur["images"]:
                cur["images"].append(im)
    if cur["program"] or cur["content"] or cur["opinion"]:
        cases.append(cur)
    return cases


def warnings_for(c):
    w = []
    for key, label in (("program", "프로그램명"), ("date", "방송일"), ("related", "관련조항"), ("content", "방송내용")):
        if not c[key].strip():
            w.append(f"{label} 누락(확인 필요)")
    if re.search(r"법|시행령|시행규칙", c["related"]):
        w.append("외부 법령 인용: 법령·조문 최신성 확인 필요")
    if re.match(r"^\s*\d{1,2}\s*[./-]\s*\d{1,2}", c["date"]):
        w.append("방송일 연도 미기재(확인 필요)")
    m = re.match(r"^\s*(20\d{2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})", c["date"])
    if m and tuple(map(int, m.groups())) >= (2026, 9, 29) and c["related"].strip():
        w.append("2026.9.29. 시행 방송심의 규칙(방미심위규칙 제8~11호) 적용 시기: 조 번호가 현행 규칙과 맞는지 확인 필요")
    if not c["images"]:
        w.append("방송화면 미추출")
    if len(c["images"]) > 3:
        w.append(f"방송화면 {len(c['images'])}장: 슬라이드에는 최대 3장, 선별 필요")
    if any(Path(p).suffix.lower() in {".wmf", ".emf"} for p in c["images"]):
        w.append("WMF/EMF 그림은 자동 삽입 불가")
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("extracted.json"))
    ap.add_argument("--img-dir", type=Path, default=Path("report_images"))
    a = ap.parse_args()
    ext = a.report.suffix.lower()
    notes, unassigned = [], []
    if ext == ".hwpx":
        blocks = read_hwpx(a.report, a.img_dir)
    elif ext == ".hwp":
        blocks, notes = read_hwp(a.report, a.img_dir)
        unassigned = sorted(str(p) for p in a.img_dir.glob("*")) if a.img_dir.exists() else []
    elif ext == ".docx":
        blocks = read_docx(a.report, a.img_dir)
    elif ext in {".txt", ".md", ".pdf"}:
        blocks = read_plain(a.report)
    else:
        raise SystemExit("지원 형식: HWPX, HWP, DOCX, TXT, MD, PDF")

    cases = parse(blocks)
    full = "\n".join(t for t, _ in blocks)
    m = STATION_RE.search(full[:400]) or STATION_RE.search(a.report.stem)
    guess = re.sub(r"\s+", "", m.group(1)) if m else ""
    for i, c in enumerate(cases, 1):
        c["case_no"] = i
        if not c["station"]:
            c["station"] = guess
        c["review_warnings"] = warnings_for(c)
    payload = {"schema_version": "2.0", "source": str(a.report), "station_guess": guess,
               "case_count": len(cases), "notes": notes, "unassigned_images": unassigned, "cases": cases}
    if not cases:
        payload["notes"].append("'프로그램명/방송내용/의견' 구조를 찾지 못함. raw_text를 직접 읽고 사례를 나눌 것.")
        payload["raw_text"] = full
    a.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"cases={len(cases)} images={sum(len(c['images']) for c in cases)} unassigned={len(unassigned)} -> {a.output}")
    for c in cases:
        print(f"  #{c['case_no']} {c['program'][:30]!r} imgs={len(c['images'])} warn={c['review_warnings']}")


if __name__ == "__main__":
    main()
