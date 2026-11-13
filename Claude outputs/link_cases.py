#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_cases.py v0.2 (2026-11-13: 사용자 확정 목록 --approvals 추가)

목적
  통계 CSV(2018~2025)의 '전체회의 형식 의결번호'(제YYYY-NN-NNNN호) 행을
  방송소위 회의결과 정제본의 '소위 의결번호'(제YYYY-방송-NN-NNNN호) 안건과 연결한다.
  연결은 방송사(채널)·프로그램명·방송일·시작 시각의 정규화 값으로 결정적으로 한다.
  모호한 건은 candidate로 남기며, candidate를 confirmed로 올리는 것은 사용자 승인 뒤 사람이 한다.

입력
  2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/18-25_part01~13.csv (NUL 문자는 읽을 때 제거)
  1 documents_md/회의록_md/방송소위_md/연도별_방송소위_회의결과_정제본/방송소위_회의결과_{2018..2024,2026}_정제.md

출력 (--out 경로, UTF-8 BOM CSV. 자료창고 밖에 둔다. 기본 저장 위치는 사용자 승인 뒤 정함)
  열: full_no, full_no_raw, decision_date, broadcaster, program, broadcast_dt,
      match_type(confirmed|candidate|none), decided_by(script|user), tier, sub_no(확정 또는 후보를 ';'로 이음),
      n_candidates, note
  match_type 정의
    confirmed : 강한 단계(T1: 채널+프로그램+방송일+시작시각, T2: 프로그램+방송일+시작시각 + 채널 일부 일치)에서
                소위 안건이 정확히 1건이고, 소위 회의일 <= 전체회의 의결일이며, 역방향(그 소위 안건을 고른 다른 번호)이 없음
    (사용자 확정: --approvals 목록에 있는 candidate만 confirmed/decided_by=user로 올린다)
    candidate : 후보가 있으나 위 조건을 모두 만족하지 못함 (후보 둘 이상, 단계가 약함, 날짜 순서 불일치, 역방향 충돌)
    none      : 후보 없음
  LLM·사람은 candidate의 선택만 제안하고 확정은 사용자 승인 뒤에 한다 (2026-11-13 결정).

검증값 (실행 때 출력으로 확인)
  CSV 전체회의 형식 번호 행 수(2018~2025), 정제본 안건 수(1460건은 2019년 값, AGENTS 7절)
  시험 측정(2026-11-13, 단순 '정규화 프로그램명+방송일' 일치): 1,531행 중 확정 499 / 후보 107 / 못 찾음 925.
  이 스크립트의 confirmed는 그보다 높아야 한다.
  알려진 연결: 제2019-방송-76-0882호 <-> 제2020-02-0004호 (박철의 빵빵한 라디오)

사용법
  python link_cases.py --out <결과.csv> [--sample N --seed S]   # sample은 confirmed 표본 출력
"""
import argparse
import csv
import glob
import io
import os
import random
import re
import sys
from collections import defaultdict, Counter

ROOT = r"J:\AI 자료"
CSV_DIR = os.path.join(ROOT, "2 data_csv", "통계_csv", "방송", "제미나이 노트북용 분할_csv")
SUB_DIR = os.path.join(ROOT, "1 documents_md", "회의록_md", "방송소위_md",
                       "연도별_방송소위_회의결과_정제본")

DT_RE = re.compile(r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?[^,\d]{0,12}?[,\s]*(\d{1,2})\s*:\s*(\d{2})")
FULL_NO_RE = re.compile(r"^\s*제?\s*(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{3,4})\s*호?")
SUB_NO_RE = re.compile(r"^제(\d{4})-방송-(\d{1,2})-(\d{4})호")


def norm(s):
    s = re.sub(r"[\s·∙・ㆍ\-_.,:;!?'\"‘’“”<>《》〈〉「」『』\[\]()~·]", "", s or "")
    return s.lower()


def norm_prog(s):
    s = re.sub(r"\(\s*\d{1,3}\s*초\s*\)", "", s or "")
    return norm(s)


def parse_dt(text):
    """첫 방송일시 -> (YYYY-MM-DD, HH:MM, 매치 시작 위치) 또는 None"""
    m = DT_RE.search(text or "")
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return "%04d-%02d-%02d" % (y, mo, d), "%02d:%02d" % (h, mi), m.start()


def load_csv_rows():
    rows = []
    for f in sorted(glob.glob(os.path.join(CSV_DIR, "18-25_part*.csv"))):
        t = open(f, encoding="utf-8-sig").read().replace("\0", "")
        for r in csv.reader(io.StringIO(t)):
            if len(r) > 5 and r[0].strip().isdigit():
                rows.append((os.path.basename(f), r))
    return rows


def load_sub_items():
    items = []
    for f in sorted(glob.glob(os.path.join(SUB_DIR, "방송소위_회의결과_*_정제.md"))):
        text = open(f, encoding="utf-8").read()
        meeting_date = ""
        cur = None
        for line in text.split("\n"):
            m = re.match(r"^## .*회의 결과 — (\d{4}-\d{2}-\d{2})", line)
            if m:
                meeting_date = m.group(1)
                continue
            if line.startswith("### 제"):
                if cur:
                    items.append(cur)
                parts = [p.strip() for p in line[4:].split("|", 2)]
                nm = SUB_NO_RE.match(parts[0])
                cur = None
                if nm and len(parts) == 3:
                    cur = dict(no=parts[0], chan=parts[1], prog=parts[2], meeting=meeting_date,
                               dt=None, result="", file=os.path.basename(f))
                continue
            if cur is not None:
                if line.startswith("- 방송일시:") and cur["dt"] is None:
                    cur["dt"] = parse_dt(line)
                elif line.startswith("- 소위 논의결과:"):
                    cur["result"] = line.split(":", 1)[1].strip()
        if cur:
            items.append(cur)
    return items


def split_program(raw):
    """CSV '프로그램명 (방송일시)' 칸 -> (프로그램명, 일자, 시각)"""
    p = parse_dt(raw)
    if not p:
        return raw.strip(), "", ""
    date, tm, pos = p
    name = raw[:pos].rstrip().rstrip("(（").strip()
    return name, date, tm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--approvals", default="J:/MCP/ai-vault-mcp/data/case_link_approvals.csv",
                    help="사용자가 확정한 candidate 목록(열: full_no, sub_no, approved_at, note). 없으면 무시")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    items = load_sub_items()
    print("정제본 안건 수:", len(items), " 방송일시 파싱 실패:", sum(1 for i in items if not i["dt"]))
    by_t1 = defaultdict(list)   # chan,prog,date,time
    by_t2 = defaultdict(list)   # prog,date,time
    by_t4 = defaultdict(list)   # prog,date (시각 없이)
    by_ct = defaultdict(list)   # chan,date,time (프로그램명 부분일치 보조)
    for it in items:
        if not it["dt"]:
            continue
        d, t, _ = it["dt"]
        it["_c"] = norm(it["chan"])
        it["_p"] = norm_prog(it["prog"])
        by_t1[(it["_c"], it["_p"], d, t)].append(it)
        by_t2[(it["_p"], d, t)].append(it)
        by_t4[(it["_p"], d)].append(it)
        by_ct[(it["_c"], d, t)].append(it)

    rows = load_csv_rows()
    recs = []
    for fn, r in rows:
        m = FULL_NO_RE.match(r[2])
        if not m or "방송" in r[2] or "광고" in r[2]:
            continue
        y, n1, n2 = m.groups()
        full_no = "제%s-%02d-%04d호" % (y, int(n1), int(n2))
        pname, d, t = split_program(r[5])
        recs.append(dict(full_no=full_no, raw=r[2].strip(), date=r[1][:10], chan=r[4], bc=r[3],
                         prog=pname, d=d, t=t, rawprog=r[5], file=fn))
    print("CSV 전체회의 형식 번호 행:", len(recs))

    def strip_dup(cands):
        return list({c["no"]: c for c in cands}.values())

    for rec in recs:
        c = norm(rec["chan"])
        p = norm_prog(rec["prog"])
        rec["tier"], cands = "", []
        if rec["d"] and rec["t"]:
            cands = by_t1.get((c, p, rec["d"], rec["t"]), [])
            if cands:
                rec["tier"] = "T1"
            else:
                cands = [x for x in by_t2.get((p, rec["d"], rec["t"]), [])
                         if x["_c"][:2] == c[:2] or x["_c"] in c or c in x["_c"]]
                if cands:
                    rec["tier"] = "T2"
                else:
                    cands = by_t2.get((p, rec["d"], rec["t"]), [])
                    if cands:
                        rec["tier"] = "T3"
        if not cands and rec["d"] and rec["t"]:
            cands = [x for x in by_ct.get((c, rec["d"], rec["t"]), [])
                     if p and (p in x["_p"] or x["_p"] in p)]
            if cands:
                rec["tier"] = "T6"
        if not cands and rec["d"]:
            cands = [x for x in by_t4.get((p, rec["d"]), []) if x["_c"] == c]
            if cands:
                rec["tier"] = "T4"
            else:
                cands = by_t4.get((p, rec["d"]), [])
                if cands:
                    rec["tier"] = "T5"
        rec["cands"] = strip_dup(cands)

    # 역방향 충돌: 같은 소위 안건을 서로 다른 전체회의 번호가 강한 단계에서 고르는 경우
    rev = defaultdict(set)
    for rec in recs:
        if rec["tier"] in ("T1", "T2") and len(rec["cands"]) == 1:
            rev[rec["cands"][0]["no"]].add(rec["full_no"])

    for rec in recs:
        cs = rec["cands"]
        note = []
        if not cs:
            rec["mt"] = "none"
        else:
            ok_date = [x for x in cs if x["meeting"] and x["meeting"] <= rec["date"]]
            if rec["tier"] in ("T1", "T2") and len(cs) == 1:
                x = cs[0]
                if not (x["meeting"] and x["meeting"] <= rec["date"]):
                    note.append("소위회의일>전체회의의결일")
                    rec["mt"] = "candidate"
                elif len(rev[x["no"]]) > 1:
                    note.append("소위 안건을 고른 전체회의 번호 둘 이상")
                    rec["mt"] = "candidate"
                else:
                    rec["mt"] = "confirmed"
            else:
                rec["mt"] = "candidate"
                if len(cs) > 1:
                    note.append("후보 %d건" % len(cs))
                if rec["tier"] in ("T3", "T4", "T5", "T6"):
                    note.append("약한 단계")
                if not rec["d"] or not rec["t"]:
                    note.append("방송일시 일부 없음")
        rec["note"] = "; ".join(note)

    # 사용자 승인 반영: (full_no, sub_no)가 승인 목록에 있고 후보에 포함되면 confirmed(decided_by=user)로 올린다.
    # 스크립트가 스스로 candidate를 승격하는 일은 없다.
    appr = {}
    if os.path.exists(a.approvals):
        with open(a.approvals, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                appr[(r["full_no"].strip(), r["sub_no"].strip())] = r.get("approved_at", "")
    used = 0
    for rec in recs:
        rec["by"] = "script"
        if rec["mt"] == "candidate":
            hit = [x for x in rec["cands"] if (rec["full_no"], x["no"]) in appr]
            if hit:
                rec["cands"], rec["mt"], rec["by"] = hit[:1], "confirmed", "user"
                rec["note"] = ("사용자 확정 " + appr[(rec["full_no"], hit[0]["no"])] + "; 이전: " + rec["note"]).strip()
                used += 1
    if appr:
        print("사용자 확정 반영: %d / 승인 목록 %d" % (used, len(appr)))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["full_no", "full_no_raw", "decision_date", "broadcaster", "program", "broadcast_dt",
                    "match_type", "decided_by", "tier", "sub_no", "n_candidates", "note"])
        for rec in recs:
            w.writerow([rec["full_no"], rec["raw"], rec["date"], rec["chan"], rec["prog"],
                        (rec["d"] + " " + rec["t"]).strip(), rec["mt"], rec["by"], rec["tier"],
                        ";".join(x["no"] for x in rec["cands"]), len(rec["cands"]), rec["note"]])

    cnt = Counter(r["mt"] for r in recs)
    print("match_type 분포:", dict(cnt), " 합계", len(recs))
    print("단계별:", dict(Counter((r["mt"], r["tier"]) for r in recs)))
    # 같은 전체회의 번호(여러 채널)가 일부 confirmed·일부 none인 경우 참고
    byno = defaultdict(set)
    for r in recs:
        byno[r["full_no"]].add(r["mt"])
    print("번호 단위 distinct:", len(byno))

    # 알려진 연결 확인
    for r in recs:
        if r["full_no"] == "제2020-02-0004호":
            print("검증 제2020-02-0004호 ->", r["mt"], [x["no"] for x in r["cands"]])

    if a.sample:
        conf = [r for r in recs if r["mt"] == "confirmed"]
        random.Random(a.seed).shuffle(conf)
        for r in conf[:a.sample]:
            x = r["cands"][0]
            print("--", r["full_no"], r["date"], r["chan"], "|", r["prog"], r["d"], r["t"])
            print("   ", x["no"], x["chan"], "|", x["prog"], x["dt"][0], x["dt"][1], x["meeting"], x["result"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
