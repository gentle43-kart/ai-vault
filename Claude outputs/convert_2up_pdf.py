# -*- coding: utf-8 -*-
"""
2쪽 모아찍기(가로 A4에 인쇄 쪽 2개) PDF를 md 변환본으로 바꾼다  v1.0 (2026-10-08, Claude Opus 5.5)

목적  : 「구 규정 연혁」 1~8, 「방송심의 연혁」처럼 가로 쪽 하나에 인쇄 쪽 두 개가 들어 있는 PDF를
        AGENTS.md 6.7절에 따라 기계적으로 변환한다. 세로 쪽은 그대로 한 쪽으로 추출한다.
방법  : pdftotext -layout 으로 쪽별 추출. 가로 쪽(폭 > 높이)은 폭을 반으로 나눠 왼쪽 → 오른쪽 순서로 추출한다.
        쪽 구분 주석: 가로 쪽은 <!-- p.N 왼쪽 --> / <!-- p.N 오른쪽 -->, 세로 쪽은 <!-- p.N -->.
        내용은 고치지 않는다. 줄 끝 공백만 지우고, 빈 줄이 3줄 이상 이어지면 2줄로 줄인다.
입력  : PDF 경로들
출력  : --out 폴더에 원본 파일명의 확장자만 .md로 바꾼 파일. 같은 이름이 있으면 건너뛴다(덮어쓰지 않음).
점검  : 쪽 수, 깨진 글자(U+FFFD) 수, 글자가 거의 없는(20자 미만) 반쪽 수를 표준출력에 적는다.
검증값: 「방송심의 연혁」 10쪽 → 반쪽 20개, 깨진 글자 0 (2026-10-08)
사용법: python3 convert_2up_pdf.py --out "<폴더>" a.pdf b.pdf ...
"""
import argparse, os, re, subprocess, sys

def page_sizes(pdf):
    out = subprocess.run(["pdfinfo", "-f", "1", "-l", "100000", pdf], capture_output=True, text=True).stdout
    sizes = {}
    for m in re.finditer(r"Page\s+(\d+) size:\s+([\d.]+) x ([\d.]+)", out):
        sizes[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    return sizes

def extract(pdf, p, crop=None):
    cmd = ["pdftotext", "-layout", "-enc", "UTF-8", "-f", str(p), "-l", str(p)]
    if crop:
        x, y, w, h = crop
        cmd += ["-x", str(x), "-y", str(y), "-W", str(w), "-H", str(h)]
    cmd += [pdf, "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.replace("\f", "")

def tidy(t):
    t = "\n".join(l.rstrip() for l in t.splitlines())
    t = re.sub(r"\n{4,}", "\n\n\n", t)
    return t.strip("\n")

def convert(pdf, outdir):
    name = os.path.splitext(os.path.basename(pdf))[0] + ".md"
    dst = os.path.join(outdir, name)
    if os.path.exists(dst):
        print(f"SKIP(이미 있음) {name}"); return
    sizes = page_sizes(pdf)
    parts, halves, thin, landscape = [], 0, 0, 0
    for p in sorted(sizes):
        w, h = sizes[p]
        if w > h:
            landscape += 1
            half = w / 2
            for label, x in (("왼쪽", 0), ("오른쪽", half)):
                t = tidy(extract(pdf, p, (int(x), 0, int(half) + 1, int(h) + 1)))
                halves += 1
                if len(re.sub(r"\s", "", t)) < 20: thin += 1
                parts.append(f"<!-- p.{p} {label} -->\n{t}")
        else:
            t = tidy(extract(pdf, p))
            halves += 1
            if len(re.sub(r"\s", "", t)) < 20: thin += 1
            parts.append(f"<!-- p.{p} -->\n{t}")
    text = "\n\n".join(parts) + "\n"
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    bad = text.count("�")
    print(f"OK {name} | PDF {len(sizes)}쪽(가로 {landscape}) | 추출 단위 {halves} | 깨진 글자 {bad} | 글자 거의 없는 단위 {thin} | {len(text.splitlines())}행")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("pdfs", nargs="+")
    a = ap.parse_args()
    for pdf in a.pdfs:
        convert(pdf, a.out)
