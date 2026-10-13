# -*- coding: utf-8 -*-
"""
회의록 PDF → md 기계 변환  v1.0 (2026-10-13)  AGENTS.md 6.7 절차용

- pdftotext(poppler)로 쪽마다 추출하고 쪽 앞에 <!-- p.N --> 주석을 붙인다.
- 내용은 요약·수정하지 않는다(줄 끝 공백 제거, 폼피드 제거만 함).
- 출력 파일명 = 원본 파일명에서 확장자만 .md. 같은 이름이 있으면 건너뛴다(덮어쓰지 않음).
- 점검값(쪽 수, 글자 수, 깨진 글자 U+FFFD 수, 빈 쪽 수)을 표준출력으로 낸다.

사용법: python3 convert_minutes_pdf.py <출력폴더> <원본PDF> [<원본PDF> ...]
"""
import os
import subprocess
import sys


def pages(pdf):
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def page_text(pdf, n):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-f", str(n), "-l", str(n), pdf, "-"],
                       capture_output=True)
    t = r.stdout.decode("utf-8", errors="replace").replace("\f", "")
    return "\n".join(l.rstrip() for l in t.splitlines()).strip()


def convert(pdf, outdir):
    name = os.path.splitext(os.path.basename(pdf))[0] + ".md"
    dst = os.path.join(outdir, name)
    if os.path.exists(dst):
        return name, "SKIP(exists)"
    n = pages(pdf)
    parts, empty = [], 0
    for i in range(1, n + 1):
        t = page_text(pdf, i)
        if not t:
            empty += 1
        parts.append(f"<!-- p.{i} -->\n{t}\n")
    body = f"<!-- source: {os.path.basename(pdf)} | 변환: pdftotext (convert_minutes_pdf.py v1.0) -->\n\n" + "\n".join(parts)
    os.makedirs(outdir, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    return name, f"pages={n} chars={len(body)} fffd={body.count(chr(0xFFFD))} empty_pages={empty}"


if __name__ == "__main__":
    outdir = sys.argv[1]
    for pdf in sys.argv[2:]:
        name, info = convert(pdf, outdir)
        print(f"{name}\t{info}")
