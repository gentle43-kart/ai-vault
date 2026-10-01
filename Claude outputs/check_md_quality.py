# -*- coding: utf-8 -*-
"""
변환본(1 documents_md) 품질 점검  v1.0 (2026-09-21) - 파일을 읽기만 한다.

점검 항목
  1. 빈 파일(100바이트 미만)
  2. 가운뎃점 띄어쓰기: '방송은·사실을'처럼 한글 사이 가운뎃점(·)이 공백보다 많이 쓰인 비율
  3. 깨진 글자(U+FFFD), NULL 문자
  4. 그림 텍스트 주석(<!-- End of picture text -->) 5개 이상
  5. 한 글자짜리 줄 비율(세로쓰기 탭·옆면 표기가 섞인 징후)
  6. 레지스트리 상태(기준본/중복본, 색인 여부)

사용법:  python check_md_quality.py        → data\\md_quality_report.md 생성
"""
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_index import Registry, DEFAULT_VAULT, read_text, norm  # noqa: E402

VAULT = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VAULT
MIDOT_RE = re.compile(r"[가-힣]·[가-힣]")
LIMITS = {"midot": 0.10, "single": 0.05}


def check(path):
    size = os.path.getsize(path)
    if size < 100:
        return {"size": size, "empty": True}
    text, enc = read_text(path)
    spaces = text.count(" ")
    midot = len(MIDOT_RE.findall(text))
    lines = [l for l in text.splitlines() if l.strip()]
    single = sum(1 for l in lines if len(l.strip()) == 1)
    return {
        "size": size, "empty": False, "enc": enc,
        "midot_ratio": midot / (spaces + midot) if (spaces + midot) else 0.0,
        "fffd": text.count("�"), "nul": text.count("\x00"),
        "pic": text.count("End of picture text"),
        "single_ratio": single / len(lines) if lines else 0.0,
    }


def main():
    reg = Registry(os.path.join(VAULT, "SOURCE_REGISTRY.yaml"))
    rows = []
    for dp, _, fs in os.walk(os.path.join(VAULT, "1 documents_md")):
        for fn in sorted(fs):
            if not fn.lower().endswith((".md", ".txt")):
                continue
            full = os.path.join(dp, fn)
            rel = norm(os.path.relpath(full, VAULT))
            e = reg.match(rel)
            r = check(full)
            r["rel"] = rel
            r["reg"] = e["id"] if e else "(미등록)"
            r["searchable"] = bool(e and e.get("searchable", True) and e.get("canonical", True) is not False)
            flags = []
            if r["empty"]:
                flags.append("빈 파일")
            else:
                if r["midot_ratio"] >= LIMITS["midot"]:
                    flags.append(f"가운뎃점 {r['midot_ratio']:.0%}")
                if r["fffd"]:
                    flags.append(f"깨진 글자 {r['fffd']}")
                if r["nul"]:
                    flags.append(f"NULL {r['nul']}")
                if r["pic"] >= 5:
                    flags.append(f"그림주석 {r['pic']}")
                if r["single_ratio"] >= LIMITS["single"]:
                    flags.append(f"한 글자 줄 {r['single_ratio']:.0%}")
            r["flags"] = flags
            rows.append(r)

    flagged = [r for r in rows if r["flags"]]
    out = [f"# 변환본 품질 점검 ({datetime.now():%Y-%m-%d %H:%M})", "",
           f"- 점검 파일: {len(rows)}개 / 문제 표시: {len(flagged)}개",
           f"- 기준: 가운뎃점 비율 ≥ {LIMITS['midot']:.0%}, 한 글자 줄 비율 ≥ {LIMITS['single']:.0%}, 빈 파일 < 100바이트", "",
           "## 문제 표시 파일 (색인 대상 먼저)", "",
           "| 색인 | registry_id | 파일 | 크기(KB) | 문제 |", "|---|---|---|---|---|"]
    for r in sorted(flagged, key=lambda r: (not r["searchable"], r["rel"])):
        out.append(f"| {'예' if r['searchable'] else '아니오'} | {r['reg']} | `{r['rel']}` | {r['size']/1024:,.0f} | {', '.join(r['flags'])} |")
    rep = os.path.join(HERE, "data", "md_quality_report.md")
    os.makedirs(os.path.dirname(rep), exist_ok=True)
    with open(rep, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out[:4]))
    print(f"보고서: {rep}")


if __name__ == "__main__":
    main()
