# -*- coding: utf-8 -*-
"""
update_stats_2026.py v1.0 (2026-11-10, Claude Sonnet 5.5)

목적
  사용자가 넣은 새 △ 파일(예: 쳇지피팅용 병합_csv/△26.01-11.csv)로 2026년 방송심의 잠정본
  (2 data_csv/통계_csv/방송/제미나이 노트북용 분할_csv/2026_잠정.csv, registry stats_2026_recent)을 매월 갱신한다.
  기본은 dry-run(보고만). --apply를 줘야 파일을 바꾼다.

검사(dry-run과 --apply 공통)
  1. '순번' 헤더 행을 앞 8행 안에서 찾는다.
  2. 기존 14열(순번~민원 총건수)의 헤더가 현 잠정본과 같은지 본다.
  3. 현 잠정본의 의결번호가 새 파일에 모두 있는지 본다. 하나라도 빠지면 중단한다(종료 코드 2).
  4. 월별 행 수, 추가된 행, 내용이 바뀐 행(순번 제외 앞 14열 중 나머지 13열 비교), 순번이 바뀐 행 수를 보고한다.
  완료 기준 출력: 현재 △26.01-10.csv로 실행하면 "누락 0, 추가 0, 변경 0".

--apply 순서(검사 통과 + 추가·변경이 1행 이상일 때만)
  1. 새 파일을 2026_잠정.csv에 덮어쓴다(바이트 그대로 복사).
  2. SOURCE_REGISTRY.yaml: 백업(Claude outputs/schema_backup/SOURCE_REGISTRY_v{판}_{YYYYMMDD}[_순번].yaml, AGENTS.md 2.1절) →
     stats_2026_recent의 period(기준일·행 수)와 notes 이력 갱신, version +0.01, updated 갱신 → YAML 파싱·id 중복·path 존재 검증.
  3. 0 wiki/log.md 맨 아래에 schema 항목 추가.
  4. J:\\MCP\\ai-vault-mcp\\data\\reindex.request 생성(같은 폴더에 reindex.failed가 있으면 만들지 않고 알림).
  검색 DB(search.db)에는 직접 쓰지 않는다.
  쳇지피팅용 병합_csv의 이전 △ 파일은 지우지 않는다(보고만).
  위키 페이지의 기존 수치는 다시 계산하지 않는다(AGENTS_통계기준.md 7.1).

사용
  python update_stats_2026.py "..\\2 data_csv\\통계_csv\\방송\\쳇지피팅용 병합_csv\\△26.01-11.csv"
  python update_stats_2026.py "…\\△26.01-11.csv" --apply
"""
import argparse
import collections
import csv
import datetime
import glob
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.environ.get("AI_VAULT", os.path.join(HERE, ".."))
CUR = os.path.join(VAULT, "2 data_csv", "통계_csv", "방송", "제미나이 노트북용 분할_csv", "2026_잠정.csv")
DROP_DIR = os.path.join(VAULT, "2 data_csv", "통계_csv", "방송", "쳇지피팅용 병합_csv")
REGISTRY = os.path.join(VAULT, "SOURCE_REGISTRY.yaml")
LOG = os.path.join(VAULT, "0 wiki", "log.md")
BACKUP_DIR = os.path.join(HERE, "schema_backup")
REINDEX_DIR = os.environ.get("AI_VAULT_DATA", r"J:\MCP\ai-vault-mcp\data")
REG_ID = "stats_2026_recent"
NCOL = 14          # 기존 열 수(순번~민원 총건수)
KEY = "의결번호"

csv.field_size_limit(10 ** 9)


def norm_h(c):
    return re.sub(r"\s+", "", c or "")


def norm_v(c):
    return (c or "").replace("\r\n", "\n").strip()


def read_table(path):
    """→ (헤더, 데이터 행 목록). 헤더 위의 제목·총계 행은 버리고, 순번이 비었거나 숫자가 아닌 행(합계 등)은 데이터로 보지 않는다."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    h = next((i for i, r in enumerate(rows[:8]) if r and r[0].strip() == "순번"), None)
    if h is None:
        sys.exit(f"중단: '순번' 헤더 행을 앞 8행에서 찾지 못했습니다: {path}")
    hdr = [norm_h(c) for c in rows[h]]
    data = [r for r in rows[h + 1:] if r and r[0].strip().isdigit()]
    return hdr, data


def month(r, idx):
    m = re.match(r"\s*(\d{4})-(\d{2})-\d{2}", r[idx])
    return f"{m.group(1)[2:]}.{m.group(2)}" if m else "의결일불명"


def index_rows(data, ki, label):
    d, dup = {}, []
    for r in data:
        k = r[ki].strip() if len(r) > ki else ""
        if not k or k in d:
            dup.append(k)
            continue
        d[k] = r
    if dup:
        print(f"주의: {label}에 의결번호가 비었거나 중복인 행 {len(dup)}행 {dup[:5]} — 비교에서 제외")
    return d


def compare(new_path):
    h_new, new = read_table(new_path)
    h_cur, cur = read_table(CUR)
    if len(h_new) < NCOL or h_new[:NCOL] != h_cur[:NCOL]:
        sys.exit("중단: 새 파일의 앞 14열 헤더가 현 잠정본과 다릅니다.\n  새 파일: %s\n  현 잠정본: %s" % (h_new[:NCOL], h_cur[:NCOL]))
    ki = h_cur.index(norm_h(KEY))
    di = h_cur.index("의결일")
    c, n = index_rows(cur, ki, "현 잠정본"), index_rows(new, ki, "새 파일")
    missing = [k for k in c if k not in n]
    added = [k for k in n if k not in c]
    changed, seq_changed = [], 0
    cmp_cols = range(1, NCOL)   # 순번(0) 제외
    for k in c:
        if k in n:
            a, b = c[k], n[k]
            if any(norm_v(a[i] if i < len(a) else "") != norm_v(b[i] if i < len(b) else "") for i in cmp_cols):
                changed.append(k)
            if norm_v(a[0]) != norm_v(b[0]):
                seq_changed += 1
    return dict(h=h_cur, ki=ki, di=di, cur=cur, new=new, c=c, n=n, missing=missing, added=added,
                changed=changed, seq_changed=seq_changed)


def report(res, new_path):
    mc = collections.Counter(month(r, res["di"]) for r in res["new"])
    dates = sorted(r[res["di"]].strip() for r in res["new"] if re.match(r"\d{4}-\d{2}-\d{2}", r[res["di"]].strip()))
    print(f"새 파일: {new_path}")
    print(f"행 수: 현 잠정본 {len(res['cur']):,} → 새 파일 {len(res['new']):,}  (의결일 {dates[0]} ~ {dates[-1]})")
    print("월별 행 수(새 파일):", ", ".join(f"{m} {v}" for m, v in sorted(mc.items())))
    if res["added"]:
        ac = collections.Counter(month(res["n"][k], res["di"]) for k in res["added"])
        print("추가 행 월별:", ", ".join(f"{m} {v}" for m, v in sorted(ac.items())))
    if res["changed"]:
        print("내용이 바뀐 의결번호(최대 10):", res["changed"][:10])
    print(f"순번이 바뀐 행: {res['seq_changed']}행")
    if res["missing"]:
        print("누락 의결번호(최대 10):", res["missing"][:10])
    print(f"누락 {len(res['missing'])}, 추가 {len(res['added'])}, 변경 {len(res['changed'])}")
    return dates[-1]


# ── apply ───────────────────────────────────────────────
def backup_registry(ver):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    base = os.path.join(BACKUP_DIR, f"SOURCE_REGISTRY_v{ver}_{stamp}")
    dst, i = base + ".yaml", 1
    while os.path.exists(dst):
        i += 1
        dst = f"{base}_{i}.yaml"
    shutil.copyfile(REGISTRY, dst)
    return dst


def update_registry(basis_date, nrows, fname, nadd, nchg):
    with open(REGISTRY, encoding="utf-8", newline="") as f:
        t = f.read()
    mv = re.search(r'^version: "(\d+)\.(\d+)"$', t, re.M)
    if not mv or len(re.findall(r'^version: ', t, re.M)) != 1:
        sys.exit("중단: SOURCE_REGISTRY.yaml version 줄을 한 곳에서 찾지 못했습니다")
    old_ver = f"{mv.group(1)}.{mv.group(2)}"
    new_ver = f"{mv.group(1)}.{int(mv.group(2)) + 1}"
    bk = backup_registry(old_ver)
    # stats_2026_recent 블록만 잘라서 수정(바꿀 문장이 한 번만 있는지 확인)
    s = t.index(f"  - id: {REG_ID}\n")
    e = t.find("\n  - id: ", s + 5)
    e = len(t) if e < 0 else e
    blk = t[s:e]
    last_month = basis_date[5:7]
    pat = re.compile(r'^(    period: )"[^"\n]*"$', re.M)
    if len(pat.findall(blk)) != 1:
        sys.exit("중단: stats_2026_recent의 period 줄을 한 곳에서 찾지 못했습니다")
    blk = pat.sub(lambda m: f'{m.group(1)}"2026.01~{last_month}(잠정, 기준일 {basis_date}, {nrows}행)"', blk)
    pat = re.compile(r'^(    notes: "[^\n]*)"$', re.M)
    if len(pat.findall(blk)) != 1:
        sys.exit("중단: stats_2026_recent의 notes 줄을 한 곳에서 찾지 못했습니다")
    today = datetime.date.today().isoformat()
    hist = f" → {today} {fname}({nrows}행, 기준일 {basis_date}, 추가 {nadd}행·내용 변경 {nchg}행)"
    blk = pat.sub(lambda m: m.group(1) + hist + '"', blk)
    t = t[:s] + blk + t[e:]
    t = t.replace(mv.group(0), f'version: "{new_ver}"', 1)
    t, k = re.subn(r"^updated: .*$", f"updated: {today}", t, count=1, flags=re.M)
    if k != 1:
        sys.exit("중단: updated 줄을 찾지 못했습니다")
    with open(REGISTRY, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    return old_ver, new_ver, bk


def validate_registry():
    try:
        import yaml
    except ImportError:
        print("주의: PyYAML이 없어 YAML 파싱 검증을 건너뜁니다(id 중복·path는 확인)")
        yaml = None
    with open(REGISTRY, encoding="utf-8") as f:
        t = f.read()
    ids = re.findall(r"^  - id: (\S+)", t, re.M)
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    ok = not dup
    if yaml:
        try:
            y = yaml.safe_load(t)
            ents = y.get("sources") or y.get("entries") or []
            if not ents:
                ents = [v for v in y.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]][0]
            e = next(x for x in ents if x.get("id") == REG_ID)
            p = os.path.join(VAULT, e["path"])
            print(f"  YAML 파싱 OK, id {len(ids)}개 중복 {len(dup)}, {REG_ID}.path 존재: {os.path.exists(p)}")
            ok = ok and os.path.exists(p)
        except Exception as ex:   # noqa: BLE001
            print("  YAML 검증 실패:", ex)
            ok = False
    else:
        print(f"  id {len(ids)}개 중복 {len(dup)}, path 존재: {os.path.exists(CUR)}")
        ok = ok and os.path.exists(CUR)
    return ok


def append_log(old_ver, new_ver, bk, basis_date, nrows, fname, res, mc):
    today = datetime.date.today().isoformat()
    with open(LOG, encoding="utf-8", newline="") as f:
        t = f.read()
    nl = "\r\n" if "\r\n" in t else "\n"
    lines = [
        f"## [{today}] schema | 2026년 방송심의 잠정본 월별 갱신({fname}, {nrows}행, 기준일 {basis_date}), SOURCE_REGISTRY.yaml v{old_ver} → v{new_ver} | Claude Sonnet 5.5",
        f"- 실행: update_stats_2026.py --apply. 입력 `쳇지피팅용 병합_csv/{fname}`, 결과 `제미나이 노트북용 분할_csv/2026_잠정.csv`",
        f"- 검사: 누락 {len(res['missing'])}, 추가 {len(res['added'])}, 내용 변경 {len(res['changed'])}, 순번 변경 {res['seq_changed']}행. 월별 " + ", ".join(f"{m} {v}" for m, v in sorted(mc.items())),
        f"- SOURCE_REGISTRY.yaml: {REG_ID}의 period(기준일·행 수)와 notes 이력만 갱신, 보안 필드는 바꾸지 않음. 백업 Claude outputs/schema_backup/{os.path.basename(bk)}",
        "- 위키 페이지의 기존 수치는 다시 계산하지 않음(AGENTS_통계기준.md 7.1). 검색 DB는 reindex.request로만 요청",
    ]
    add = nl.join(lines) + nl
    with open(LOG, "w", encoding="utf-8", newline="") as f:
        f.write(t + ("" if t.endswith(("\n", "\r\n")) else nl) + nl + add)


def request_reindex(reason):
    if os.path.exists(os.path.join(REINDEX_DIR, "reindex.failed")):
        print("★ 알림: reindex.failed가 있어 reindex.request를 만들지 않았습니다. 원인을 먼저 확인하세요:", REINDEX_DIR)
        return False
    if not os.path.isdir(REINDEX_DIR):
        print("★ 알림: 색인 폴더를 찾지 못해 reindex.request를 만들지 않았습니다:", REINDEX_DIR)
        return False
    with open(os.path.join(REINDEX_DIR, "reindex.request"), "w", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {reason}\n")
    print("reindex.request 생성:", REINDEX_DIR)
    return True


def main():
    ap = argparse.ArgumentParser(description="2026 방송심의 잠정본 월별 갱신(기본 dry-run)")
    ap.add_argument("new_file", help="새 △ 파일 경로")
    ap.add_argument("--apply", action="store_true", help="실제로 덮어쓰고 registry·log·reindex 처리")
    a = ap.parse_args()
    new_path = os.path.abspath(a.new_file)
    if not os.path.isfile(new_path):
        sys.exit(f"중단: 파일이 없습니다: {new_path}")
    res = compare(new_path)
    basis = report(res, new_path)
    others = [os.path.basename(p) for p in glob.glob(os.path.join(DROP_DIR, "△*")) if os.path.abspath(p) != new_path]
    if others:
        print(f"참고: 쳇지피팅용 병합_csv에 다른 △ 파일이 있습니다 {others}. 이 스크립트는 지우지 않습니다(정리 여부는 사용자가 결정).")
    if res["missing"]:
        print("중단: 현 잠정본의 의결번호가 새 파일에서 빠졌습니다. 잠정본을 바꾸지 않습니다.")
        sys.exit(2)
    if not a.apply:
        print("dry-run: 아무것도 바꾸지 않았습니다. 반영하려면 --apply")
        return
    if not res["added"] and not res["changed"]:
        print("추가·변경이 없어 --apply를 건너뜁니다(파일·registry·log·reindex 모두 그대로).")
        return
    fname = os.path.basename(new_path)
    nrows = len(res["new"])
    mc = collections.Counter(month(r, res["di"]) for r in res["new"])
    shutil.copyfile(new_path, CUR)
    print("1) 2026_잠정.csv 덮어쓰기 완료")
    old_v, new_v, bk = update_registry(basis, nrows, fname, len(res["added"]), len(res["changed"]))
    print(f"2) SOURCE_REGISTRY.yaml v{old_v} → v{new_v}, 백업 {bk}")
    if not validate_registry():
        sys.exit(f"검증 실패: 백업({bk})으로 복원하고 원인을 확인하세요. log·reindex는 만들지 않았습니다.")
    append_log(old_v, new_v, bk, basis, nrows, fname, res, mc)
    print("3) log.md 항목 추가 완료")
    request_reindex(f"stats 잠정본 월별 갱신({fname})")
    print("끝. 다음: reindex_last.log의 exit=0 확인, wiki_lint.py 실행")


if __name__ == "__main__":
    main()
