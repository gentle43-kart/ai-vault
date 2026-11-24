#!/usr/bin/env python3
"""스킬 카탈로그와 양식 구조 문서를 만든다.

목적: 스킬 정본·설치본·양식의 버전과 일치 여부를 한 장으로 확인한다.
입력: `4 스킬, 프로젝트/<스킬>/` 중 SKILL.md와 CHANGELOG.md가 모두 있는 폴더, 설치된 스킬.
출력: `4 스킬, 프로젝트/_스킬_카탈로그.md`, 각 스킬의 `양식_구조.md`.
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
FORM_EXT = {".pptx", ".potx"}
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


def forms_of(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.rglob("*")
        if p.suffix.lower() in FORM_EXT and not p.name.startswith("~$") and not any(x in p.name for x in EXCLUDE)
    )


def structure_doc(folder: Path, forms: list[Path]) -> str:
    out = ["# 양식 구조", "", "`Claude outputs/skill_catalog.py`가 만든 문서이다. 직접 고치지 않는다.", ""]
    for f in forms:
        out += [f"## {f.relative_to(folder).as_posix()}", "", f"- 지문: `{sha(f.read_bytes())}`"]
        out += pptx_structure(f)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def uncommitted(paths: list[Path]) -> list[str]:
    if not paths:
        return []
    args = ["git", "-c", "core.autocrlf=true", "-c", "core.quotepath=false", "-C", str(VAULT),
            "status", "--porcelain", "--"] + [str(p) for p in paths]
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    return [Path(line[3:].strip('"')).name for line in res.stdout.splitlines()]


def inspect(folder: Path) -> tuple[dict, str]:
    skill = folder / "SKILL.md"
    text = skill.read_text(encoding="utf-8-sig")
    forms = forms_of(folder)
    doc = structure_doc(folder, forms)
    doc_path = folder / "양식_구조.md"
    installs = installed_paths(folder.name)
    src_hash = text_sha(skill)
    same = [p for p in installs if text_sha(p) == src_hash]
    total, bad = script_mismatches(text, folder)
    version, log_version = version_of(text), changelog_version(folder / "CHANGELOG.md")
    problems = []
    if not installs:
        problems.append("설치본 없음")
    elif len(same) != len(installs):
        problems.append("설치본 불일치")
    if bad:
        problems.append("스크립트 불일치: " + ", ".join(bad))
    if version != log_version:
        problems.append(f"CHANGELOG 버전 다름({log_version or '없음'})")
    dirty = uncommitted([folder])
    info = {"name": folder.name, "version": version, "forms": forms, "installs": len(installs), "same": len(same),
            "scripts": total, "bad": bad, "problems": problems, "dirty": dirty, "doc_path": doc_path}
    return info, doc


def catalog(items: list[dict]) -> str:
    out = ["# 스킬 카탈로그", "", "`Claude outputs/skill_catalog.py`가 만든 문서이다. 직접 고치지 않는다.", "",
           "| 스킬 | 버전 | 설치본 | 부록 스크립트 | 양식 | 상태 | 미커밋 |", "|---|---|---|---|---|---|---|"]
    for i in items:
        forms = "<br>".join(f.relative_to(ROOT).as_posix() for f in i["forms"]) or "-"
        scripts = f"{i['scripts'] - len(i['bad'])}/{i['scripts']} 일치"
        status = "; ".join(i["problems"]) or "정상"
        out.append(f"| {i['name']} | {i['version'] or '-'} | {i['same']}/{i['installs']} 일치 | {scripts} | {forms} | {status} | {len(i['dirty'])}개 |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    folders = sorted(p.parent for p in ROOT.glob("*/SKILL.md") if (p.parent / "CHANGELOG.md").exists())
    results = [inspect(f) for f in folders]
    items = [r[0] for r in results]
    failed = False
    for info, doc in results:
        current = info["doc_path"].read_text(encoding="utf-8") if info["doc_path"].exists() else ""
        if args.check and current != doc:
            info["problems"].append("양식_구조 갱신 필요")
        elif not args.check and current != doc:
            info["doc_path"].write_text(doc, encoding="utf-8", newline="\n")
        failed = failed or bool(info["problems"])
    if not args.check:
        # 양식_구조.md를 새로 쓴 뒤의 git 상태로 카탈로그를 만든다.
        for info in items:
            info["dirty"] = inspect(ROOT / info["name"])[0]["dirty"]
        CATALOG.write_text(catalog(items), encoding="utf-8", newline="\n")
    for i in items:
        print(f"{i['name']}: v{i['version']} install {i['same']}/{i['installs']} scripts {i['scripts'] - len(i['bad'])}/{i['scripts']} forms {len(i['forms'])} problems={i['problems']} dirty={i['dirty']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
