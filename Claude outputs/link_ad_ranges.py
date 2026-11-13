#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_ad_ranges.py v0.2 (2026-11-13)

목적
  광고소위 원본 회의록에서 보고자가 연도·차수 없이 말하는 호수 범위("519호부터 532호까지")를
  통계 CSV의 완전한 의결번호(제YYYY-광고-NN-NNNN호 등)로 풀어, 회의록 위치(파일·줄)와 연결한다.
  의결번호의 마지막 번호(NNNN)는 연도 안에서 일련번호이므로 (연도, 일련번호)로 CSV 행을 찾는다.
  같은 일련번호가 광고 번호와 방송 번호에 모두 있으면 범위 뒤에 따옴표로 인용된 광고·프로그램 이름이
  CSV 행의 프로그램명·의결 내용에 있는지로 가른다. 가르지 못하면 candidate로 남긴다.
  판단은 하지 않고 결정적으로 연결하며, candidate의 확정은 사용자 승인 뒤에 한다(2026-11-13 결정).

입력
  1 documents_md/회의록_md/광고소위_md/연도별 광고소위 회의록 md파일 원본_md/*.md (파일명의 연도 사용, 2012년 이후)
  2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/18-25_part*.csv, 2026_잠정.csv
  2 data_csv/통계_csv/방송/2012-2017 방송심의 통계(보정).csv
출력 (--out, UTF-8 BOM CSV, 자료창고 밖에 둔다)
  file, line, year, text, a, b, match_type(confirmed|candidate|none), ns(광고|방송), n_resolved, labels, reason
  labels: 풀린 완전한 의결번호를 ';'로 이음
검증값 (실행 때 출력)
  범위 추출 수, match_type 분포. 시험 측정(2026-11-13): 연도 없는 범위 약 250개 중 광고 번호로 전부 풀리는 것 약 160개.
알려진 한계
  - 줄바꿈으로 끊긴 호 표기는 줄을 이어 붙여 읽는다. 'N호부터 M호까지' 형태만 본다("N호와 M호", "N~M호"는 보지 않는다).
  - 범위 길이 120 이상은 건너뛴다.
  - 2012년 이전 연도에는 CSV가 없어 풀지 않는다.
"""
import argparse
import bisect
import collections
import csv
import glob
import io
import os
import re
import sys

ROOT = "J:/AI 자료"
MIN_DIR = ROOT + "/1 documents_md/회의록_md/광고소위_md/연도별 광고소위 회의록 md파일 원본_md"
CSV_DIR = ROOT + "/2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv"
CSV_1217 = ROOT + "/2 data_csv/통계_csv/방송/2012-2017 방송심의 통계(보정).csv"

LAB_RE = re.compile(r"(\d{4})\s*-\s*(광고|방송)\s*-\s*(\d{1,2})\s*-\s*(\d{3,4})")
RANGE_RE = re.compile(r"(\d{1,4})\s*호\s*(?:부터|에서|~|～|-)\s*(?:제\s*)?(\d{1,4})\s*호?")
QUOTE_RE = re.compile(r"[‘'“\"]\s*([^’'”\"]{2,40}?)\s*[’'”\"]")


def norm(s):
    return re.sub(r"[\s·∙・ㆍ\-_.,:;!?'\"‘’“”<>《》〈〉「」『』\[\]()~]", "", s or "").lower()


def load_labels():
    """(연도, 'ns', 일련번호) -> {'labels': set, 'text': 정규화된 프로그램명·의결내용}"""
    m = {}
    files = glob.glob(CSV_DIR + "/18-25_part*.csv") + [CSV_DIR + "/2026_잠정.csv", CSV_1217]
    for f in files:
        t = open(f, encoding="utf-8-sig").read().replace("\0", "")
        for r in csv.reader(io.StringIO(t)):
            head = " ".join(r[:3])
            for lm in LAB_RE.finditer(head):
                y, ns, nn, seq = int(lm[1]), lm[2], int(lm[3]), int(lm[4])
                key = (y, ns, seq)
                e = m.setdefault(key, {"labels": set(), "text": ""})
                e["labels"].add("제%d-%s-%02d-%04d호" % (y, ns, nn, seq))
                e["text"] += norm(" ".join(r[3:8]))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lab = load_labels()
    rows = []
    for f in sorted(glob.glob(MIN_DIR + "/*.md")):
        ym = re.search(r"(\d{4})년", os.path.basename(f))
        if not ym or int(ym[1]) < 2012:
            continue
        y = int(ym[1])
        lines = open(f, encoding="utf-8").read().split("\n")
        flat, starts, pos = [], [], 0
        for ln in lines:
            s = ln.strip()
            starts.append(pos)
            flat.append(s)
            pos += len(s)
        flat = "".join(flat)
        for m in RANGE_RE.finditer(flat):
            pre = flat[max(0, m.start() - 14):m.start()]
            if re.search(r"(광고|방송)\s*-\s*\d{1,2}\s*-\s*$", pre) or re.search(r"\d{4}\s*-\s*\d{1,2}\s*-\s*$", pre):
                continue   # 이미 '제YYYY-광고-NN-' 접두어가 붙은 범위
            x, z = int(m[1]), int(m[2])
            if not (x < z < x + 120):
                continue
            line = bisect.bisect_right(starts, m.start())   # 1부터 시작하는 줄 번호
            tail = flat[m.end():m.end() + 160]
            quotes = [norm(q) for q in QUOTE_RE.findall(tail)[:2]
                      if len(norm(q)) >= 3 and "심의" not in q and "안건" not in q]   # 일반 문구 제외
            seqs = range(x, z + 1)
            res = {}
            for ns in ("광고", "방송"):
                ok = [s for s in seqs if (y, ns, s) in lab]
                names = [s for s in ok if any(q in lab[(y, ns, s)]["text"] for q in quotes)] if quotes else []
                res[ns] = (ok, names)
            full = [ns for ns in ("광고", "방송") if len(res[ns][0]) == len(seqs)]
            ns_pick, mt, reason = "", "none", ""
            if len(full) == 1 and (full[0] == "광고" or res[full[0]][1]):
                ns_pick, mt = full[0], "confirmed"
                reason = "광고 번호로만 전부 풀림" if len(full) == 1 and not res[full[0]][1] else "인용 이름 일치"
            elif len(full) == 2:
                withname = [ns for ns in full if res[ns][1]]
                if len(withname) == 1:
                    ns_pick, mt, reason = withname[0], "confirmed", "광고·방송 번호 모두 존재, 인용 이름으로 가름"
                else:
                    ns_pick, mt, reason = "광고", "candidate", "광고·방송 번호 모두 존재, 인용 이름으로 못 가름"
            elif len(full) == 1:
                ns_pick, mt, reason = full[0], "candidate", "방송 번호만 풀리고 인용 이름 불일치"
            else:
                part = [ns for ns in ("광고", "방송") if res[ns][0]]
                if part:
                    ns_pick, mt, reason = part[0], "candidate", "일부 번호만 풀림(%d/%d)" % (len(res[part[0]][0]), len(seqs))
                else:
                    reason = "CSV에 해당 번호 없음"
            labels = []
            if ns_pick:
                for s in seqs:
                    if (y, ns_pick, s) in lab:
                        labels += sorted(lab[(y, ns_pick, s)]["labels"])
            if mt == "confirmed" and len(labels) != len(seqs):
                mt, reason = "candidate", "같은 일련번호에 번호 둘 이상"
            rows.append([os.path.basename(f), line, y, flat[max(0, m.start() - 6):m.end() + 6],
                         x, z, mt, ns_pick, len(labels), ";".join(labels), reason])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "line", "year", "text", "a", "b", "match_type", "ns", "n_resolved", "labels", "reason"])
        w.writerows(rows)
    print("범위 추출:", len(rows), " 분포:", dict(collections.Counter(r[6] for r in rows)))
    print("연도별:", {y: dict(collections.Counter(r[6] for r in rows if r[2] == y)) for y in sorted({r[2] for r in rows})})
    print("사유:", dict(collections.Counter((r[6], r[10][:14]) for r in rows)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
