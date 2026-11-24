#!/usr/bin/env python3
"""스킬 카탈로그와 양식 구조 문서를 만든다.

목적: 스킬 정본·설치본·양식의 버전과 일치 여부를 한 장으로 확인한다.
입력: `4 스킬, 프로젝트/` 아래 두 단계까지의 폴더 중 CHANGELOG.md가 있는 폴더(SKILL.md가 없으면 양식 전용), 설치된 스킬.
출력: `4 스킬, 프로젝트/_스킬_카탈로그.md`, 양식이 있는 항목의 `양식_구조.md`.
검증값: broadcast-review-ppt는 버전 2026-11-19, 템플릿 4장, 설치본·부록 스크립트 일치.
사용: python skill_catalog.py [--check]  (--check는 파일을 쓰지 않고, 문제가 있으면 exit 1)
표준 라이브러리만 쓴다. 출력에 실행 시각을 넣지 않아 내용이 바뀔 때만 git 변경이 생긴다.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import posixpath
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

VAULT = Path(__file__).resolve().parents[1]
ROOT = VAULT / "4 스킬, 프로젝트"
CATALOG = ROOT / "_스킬_카탈로그.md"
FORM_EXT = {".pptx", ".potx", ".xlsx", ".xltx", ".hwpx"}
EXCLUDE = ("테스트결과",)
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def norm(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def text_sha(path: Path) -> str:
    return sha(norm(path.read_text(encoding="utf-8-sig")).encode("utf-8"))


def version_of(text: str) -> str:
    m = re.search(r"toolkit version:\s*([0-9-]+)", text)
    return m.group(1) if m else ""


def changelog_version(path: Path) -> str:
    m = re.search(r"^##\s*(\d{4}-\d{2}-\d{2})", path.read_text(encoding="utf-8-sig"), re.M)
    return m.group(1) if m else ""


def changelog_meta(path: Path) -> dict:
    """CHANGELOG 줄머리의 `버전:`, `정본:`(4 스킬, 프로젝트 기준 경로), `주의:`를 읽는다."""
    text = path.read_text(encoding="utf-8-sig")
    ver = re.search(r"^버전:\s*(.+?)\s*$", text, re.M)
    title = re.search(r"^이름:\s*(.+?)\s*$", text, re.M)
    return {
        "name": title.group(1) if title else "",
        "version": ver.group(1) if ver else "",
        "docs": re.findall(r"^정본:\s*(.+?)\s*$", text, re.M),
        "notes": re.findall(r"^주의:\s*(.+?)\s*$", text, re.M),
    }


def installed_paths(name: str) -> list[Path]:
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
    patterns = [
        str(home / ".claude/skills" / name / "SKILL.md"),
        str(local / "Claude-Data/*/rpm/*/*/*/skills" / name / "SKILL.md"),
    ]
    return sorted({Path(p) for pat in patterns for p in glob.glob(pat)})


def script_mismatches(skill_text: str, folder: Path) -> tuple[int, list[str]]:
    blocks = re.findall(r"^## 부록 [A-Z]\. tools/(\S+)\s*\n+```python\n(.*?)\n```", skill_text, re.S | re.M)
    bad = []
    for fname, code in blocks:
        hits = list(folder.rglob(fname))
        if not hits or norm(hits[0].read_text(encoding="utf-8-sig")) != norm(code):
            bad.append(fname)
    return len(blocks), bad


def pptx_structure(path: Path) -> list[str]:
    lines = []
    with zipfile.ZipFile(path) as z:
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels.iter(PR + "Relationship")}
        ids = pres.find(P + "sldIdLst")
        for no, sid in enumerate(list(ids) if ids is not None else [], 1):
            member = posixpath.normpath(posixpath.join("ppt", targets[sid.get(R + "id")].lstrip("/")))
            root = ET.fromstring(z.read(member))
            lines.append(f"\n### 슬라이드 {no}\n")
            for el in root.iter():
                if el.tag not in (P + "sp", P + "pic"):
                    continue
                c = el.find(f".//{P}cNvPr")
                name = c.get("name", "") if c is not None else ""
                text = " / ".join(
                    "".join(t.text or "" for t in para.iter(A + "t")).strip()
                    for para in el.iter(A + "p")
                ).strip(" /")
                text = re.sub(r"\s+", " ", text)[:40].replace("|", "\\|")
                kind = "그림" if el.tag == P + "pic" else "도형"
                lines.append(f"- {kind} `{name}`" + (f": {text}" if text else ""))
    return lines


def short(text: str, size: int = 40) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:size].replace("|", "\\|")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def xlsx_structure(path: Path) -> list[str]:
    lines = []
    with zipfile.ZipFile(path) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
                strings.append("".join(t.text or "" for t in si.iter() if local(t.tag) == "t"))
        book = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels.iter(PR + "Relationship")}
        for sheet in (e for e in book.iter() if local(e.tag) == "sheet"):
            target = targets[sheet.get(R + "id")]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            root = ET.fromstring(z.read(member))
            dim = next((e.get("ref", "") for e in root.iter() if local(e.tag) == "dimension"), "")
            lines.append(f"\n### 시트 {sheet.get('name')} ({dim})\n")
            for row in (e for e in root.iter() if local(e.tag) == "row"):
                cells = []
                for c in (e for e in row if local(e.tag) == "c"):
                    value = next((e.text for e in c if local(e.tag) == "v"), None)
                    if c.get("t") == "s" and value is not None:
                        value = strings[int(value)]
                    elif c.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in c.iter() if local(t.tag) == "t")
                    if value:
                        cells.append(short(value, 20))
                if cells:
                    lines.append("- 첫 내용 행: " + " / ".join(cells[:12]))
                    break
    return lines


def hwpx_structure(path: Path) -> list[str]:
    lines = []
    with zipfile.ZipFile(path) as z:
        sections = sorted(
            (n for n in z.namelist() if re.search(r"(^|/)section\d+\.xml$", n, re.I)),
            key=lambda n: int(re.search(r"section(\d+)", n, re.I).group(1)),
        )
        for no, member in enumerate(sections, 1):
            root = ET.fromstring(z.read(member))
            paras = [e for e in root.iter() if local(e.tag) == "p"]
            tables = sum(1 for e in root.iter() if local(e.tag) == "tbl")
            lines.append(f"\n### 구역 {no} (문단 {len(paras)}, 표 {tables})\n")
            shown = 0
            for p in paras:
                text = short("".join(t.text or "" for t in p.iter() if local(t.tag) == "t"))
                if text:
                    lines.append(f"- {text}")
                    shown += 1
                if shown == 10:
                    break
    return lines


def form_structure(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xltx"}:
        return xlsx_structure(path)
    if ext == ".hwpx":
        return hwpx_structure(path)
    return pptx_structure(path)


def forms_of(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.rglob("*")
        if p.suffix.lower() in FORM_EXT and not p.name.startswith("~$") and not any(x in p.name for x in EXCLUDE)
    )


def structure_doc(folder: Path, forms: list[Path]) -> str:
    out = ["# 양식 구조", "", "`Claude outputs/skill_catalog.py`가 만든 문서이다. 직접 고치지 않는다.", ""]
    for f in forms:
        out += [f"## {f.relative_to(folder).as_posix()}", "", f"- 지문: `{sha(f.read_bytes())}`"]
        out += form_structure(f)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def uncommitted(paths: list[Path]) -> list[str]:
    if not paths:
        return []
    args = ["git", "-c", "core.autocrlf=true", "-c", "core.quotepath=false", "-C", str(VAULT),
            "status", "--porcelain", "--"] + [str(p) for p in paths]
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    return [Path(line[3:].strip('"')).name for line in res.stdout.splitlines()]


def skill_name(text: str, folder: Path) -> str:
    m = re.search(r'^name:\s*"?([^"\r\n]+?)"?\s*$', text[:600], re.M)
    return m.group(1) if m else folder.name


def managed_folders() -> list[Path]:
    found = {p.parent for pattern in ("*/CHANGELOG.md", "*/*/CHANGELOG.md") for p in ROOT.glob(pattern)}
    return sorted(found, key=lambda p: p.relative_to(ROOT).as_posix())


def inspect(folder: Path) -> tuple[dict, str]:
    skill = folder / "SKILL.md"
    is_skill = skill.exists()
    text = skill.read_text(encoding="utf-8-sig") if is_skill else ""
    name = skill_name(text, folder)
    forms = forms_of(folder)
    doc = structure_doc(folder, forms) if forms else ""
    doc_path = folder / "양식_구조.md"
    installs = installed_paths(name) if is_skill else []
    src_hash = text_sha(skill) if is_skill else ""
    same = [p for p in installs if text_sha(p) == src_hash]
    total, bad = script_mismatches(text, folder)
    log_version = changelog_version(folder / "CHANGELOG.md")
    meta = changelog_meta(folder / "CHANGELOG.md")
    name = meta["name"] or name
    toolkit = version_of(text)
    version = toolkit or meta["version"] or log_version
    docs = [ROOT / d for d in meta["docs"]]
    extras = sorted({
        f.relative_to(p.parent).as_posix()
        for p in installs for f in p.parent.rglob("*")
        if f.is_file() and f != p and not (folder / f.relative_to(p.parent)).exists()
    })
    problems = []
    if is_skill and not installs:
        problems.append("설치본 없음")
    elif len(same) != len(installs):
        problems.append("설치본 불일치")
    if bad:
        problems.append("스크립트 불일치: " + ", ".join(bad))
    if toolkit and toolkit != log_version:
        problems.append(f"CHANGELOG 버전 다름({log_version or '없음'})")
    missing = [d.name for d in docs if not d.is_file()]
    if missing:
        problems.append("정본 문서 없음: " + ", ".join(missing))
    problems += meta["notes"]
    dirty = uncommitted([folder] + [d for d in docs if d.is_file()])
    info = {"name": name, "folder": folder, "is_skill": is_skill, "version": version, "forms": forms, "docs": docs,
            "installs": len(installs), "same": len(same), "scripts": total, "bad": bad, "extras": extras,
            "problems": problems, "dirty": dirty, "doc_path": doc_path}
    return info, doc


def catalog(items: list[dict]) -> str:
    out = ["# 스킬 카탈로그", "", "`Claude outputs/skill_catalog.py`가 만든 문서이다. 직접 고치지 않는다.", "",
           "| 항목 | 버전 | 정본 위치 | 정본 문서 | 설치본 | 부록 스크립트 | 양식 | 정본에 없는 부속 파일 | 상태 | 미커밋 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for i in items:
        forms = "<br>".join(f.relative_to(ROOT).as_posix() for f in i["forms"]) or "-"
        docs = "<br>".join(d.name for d in i["docs"]) or "-"
        scripts = f"{i['scripts'] - len(i['bad'])}/{i['scripts']} 일치" if i["scripts"] else "-"
        installs = f"{i['same']}/{i['installs']} 일치" if i["is_skill"] else "해당 없음"
        extras = "<br>".join(i["extras"]) or "-"
        status = "; ".join(i["problems"]) or "정상"
        where = i["folder"].relative_to(ROOT).as_posix()
        out.append(f"| {i['name']} | {i['version'] or '-'} | {where} | {docs} | {installs} | {scripts} | {forms} | {extras} | {status} | {len(i['dirty'])}개 |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    results = [inspect(f) for f in managed_folders()]
    items = [r[0] for r in results]
    failed = False
    for info, doc in results:
        current = info["doc_path"].read_text(encoding="utf-8") if info["doc_path"].exists() else ""
        if not doc:
            continue
        if args.check and current != doc:
            info["problems"].append("양식_구조 갱신 필요")
        elif not args.check and current != doc:
            info["doc_path"].write_text(doc, encoding="utf-8", newline="\n")
        failed = failed or bool(info["problems"])
    if not args.check:
        # 양식_구조.md를 새로 쓴 뒤의 git 상태로 카탈로그를 만든다.
        for info in items:
            info["dirty"] = inspect(info["folder"])[0]["dirty"]
        CATALOG.write_text(catalog(items), encoding="utf-8", newline="\n")
    for i in items:
        print(f"{i['name']}: v{i['version']} install {i['same']}/{i['installs']} scripts {i['scripts'] - len(i['bad'])}/{i['scripts']} forms {len(i['forms'])} problems={i['problems']} dirty={i['dirty']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
