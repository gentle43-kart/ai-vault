# -*- coding: utf-8 -*-
"""
update_stats_2026.py v1.1 (2026-11-12, Claude Sonnet 5.5; v1.0 2026-11-10)
  v1.1: --apply를 '복구 가능한 순서'로 바꿨다. v1.0은 2026_잠정.csv를 먼저 덮어쓴 뒤 registry를 고쳐서, 검증이 실패하면
        덮어쓰기 전 잠정본이 남지 않았다. 지금은 ① registry 새 내용을 메모리에서 만들어 검증 → ② CSV·registry를 자료창고 밖
        백업 폴더에 보관 → ③ registry 쓰기 → ④ CSV 교체 → ⑤ 어느 단계에서든 예외가 나면 둘 다 백업본으로 되돌린다.
        log.md 항목에 새 파일 sha256·기준일·실행 옵션 한 줄을 더했다. dry-run 동작과 종료 코드 2는 v1.0과 같다.

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
  1. SOURCE_REGISTRY.yaml 새 내용을 메모리에서 만들고 검증한다(YAML 파싱·id 중복·path 존재). 여기서 실패하면 아무 파일도 안 바뀐다.
  2. 백업: 현재 2026_잠정.csv와 SOURCE_REGISTRY.yaml을 J:\\MCP\\ai-vault-mcp\\data\\stats_backup\\{날짜_시각}\\ 에 복사하고 해시를 대조한다
     (data/는 gitignore 대상, 자료창고 밖). registry는 AGENTS.md 2.1절에 따라 Claude outputs/schema_backup/에도 한 부 둔다.
  3. registry 쓰기(같은 폴더 임시 파일에 쓴 뒤 os.replace).
  4. CSV 교체(같은 폴더 임시 파일에 복사한 뒤 os.replace → 중간 상태의 반쪽짜리 CSV가 생기지 않는다).
  5. 디스크의 registry를 다시 검증하고 CSV의 sha256이 새 파일과 같은지 확인한다. 3~5 중 어디서든 예외가 나면 CSV와 registry를
     백업본으로 함께 되돌리고 종료 코드 1로 끝난다. 이때 log 항목과 reindex.request는 만들지 않는다.
  6. 0 wiki/log.md 맨 아래에 schema 항목 추가(새 파일 sha256·기준일·실행 옵션 포함). 이 단계 예외도 5와 같이 되돌린다.
  7. J:\\MCP\\ai-vault-mcp\\data\\reindex.request 생성(같은 폴더에 reindex.failed가 있으면 만들지 않고 알림).
  검색 DB(search.db)에는 직접 쓰지 않는다.
  쳇지피팅용 병합_csv의 이전 △ 파일은 지우지 않는다(보고만).
  위키 페이지의 기존 수치는 다시 계산하지 않는다(AGENTS_통계기준.md 7.1).

종료 코드: 0 정상(dry-run 포함), 1 중단 또는 --apply 실패(되돌림 완료), 2 현 잠정본의 의결번호가 새 파일에서 빠짐.

사용
  python update_stats_2026.py "..\\2 data_csv\\통계_csv\\방송\\쳇지피팅용 병합_csv\\△26.01-11.csv"
  python update_stats_2026.py "…\\△26.01-11.csv" --apply
"""
import argparse
import collections
import csv
import datetime
import glob
import hashlib
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
STATS_BACKUP_ROOT = os.path.join(REINDEX_DIR, "stats_backup")   # v1.1: 자료창고 밖(AGENTS.md 2.1·74행: Claude outputs에는 데이터 사본을 두지 않는다)
REG_ID = "stats_2026_recent"
NCOL = 14          # 기존 열 수(순번~민원 총건수)
KEY = "의결번호"

csv.field_size_limit(10 ** 9)


class ApplyError(Exception):
    """--apply 중 검증 실패. main이 잡아서 되돌린다(또는 쓰기 전이면 그냥 종료)."""


def norm_h(c):
    return re.sub(r"\s+", "", c or "")


def norm_v(c):
    return (c or "").replace("\r\n", "\n").strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


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


# ── apply (v1.1: 메모리에서 만들기 → 백업 → 쓰기 → 검증, 실패하면 되돌리기) ──────────
def build_registry_text(basis_date, nrows, fname, nadd, nchg):
    """registry의 새 내용을 문자열로만 만든다(파일은 건드리지 않는다). → (새 내용, 옛 판, 새 판)"""
    with open(REGISTRY, encoding="utf-8", newline="") as f:
        t = f.read()
    mv = re.search(r'^version: "(\d+)\.(\d+)"$', t, re.M)
    if not mv or len(re.findall(r'^version: ', t, re.M)) != 1:
        raise ApplyError("SOURCE_REGISTRY.yaml version 줄을 한 곳에서 찾지 못했습니다")
    old_ver = f"{mv.group(1)}.{mv.group(2)}"
    new_ver = f"{mv.group(1)}.{int(mv.group(2)) + 1}"
    # stats_2026_recent 블록만 잘라서 수정(바꿀 문장이 한 번만 있는지 확인)
    s = t.find(f"  - id: {REG_ID}\n")
    if s < 0:
        raise ApplyError(f"SOURCE_REGISTRY.yaml에서 id {REG_ID}를 찾지 못했습니다")
    e = t.find("\n  - id: ", s + 5)
    e = len(t) if e < 0 else e
    blk = t[s:e]
    last_month = basis_date[5:7]
    pat = re.compile(r'^(    period: )"[^"\n]*"$', re.M)
    if len(pat.findall(blk)) != 1:
        raise ApplyError("stats_2026_recent의 period 줄을 한 곳에서 찾지 못했습니다")
    blk = pat.sub(lambda m: f'{m.group(1)}"2026.01~{last_month}(잠정, 기준일 {basis_date}, {nrows}행)"', blk)
    pat = re.compile(r'^(    notes: "[^\n]*)"$', re.M)
    if len(pat.findall(blk)) != 1:
        raise ApplyError("stats_2026_recent의 notes 줄을 한 곳에서 찾지 못했습니다")
    today = datetime.date.today().isoformat()
    hist = f" → {today} {fname}({nrows}행, 기준일 {basis_date}, 추가 {nadd}행·내용 변경 {nchg}행)"
    blk = pat.sub(lambda m: m.group(1) + hist + '"', blk)
    t = t[:s] + blk + t[e:]
    t = t.replace(mv.group(0), f'version: "{new_ver}"', 1)
    t, k = re.subn(r"^updated: .*$", f"updated: {today}", t, count=1, flags=re.M)
    if k != 1:
        raise ApplyError("updated 줄을 찾지 못했습니다")
    return t, old_ver, new_ver


def validate_registry_text(t):
    """registry 내용(문자열)을 검증한다: id 중복 없음, YAML 파싱, stats_2026_recent.path 존재. → True/False"""
    try:
        import yaml
    except ImportError:
        print("주의: PyYAML이 없어 YAML 파싱 검증을 건너뜁니다(id 중복·path는 확인)")
        yaml = None
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


def schema_backup_registry(ver):
    """AGENTS.md 2.1절: 스키마 파일은 고치기 전에 Claude outputs/schema_backup/에 백업한다."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.date.today().strftime("%Y%m%d")
    base = os.path.join(BACKUP_DIR, f"SOURCE_REGISTRY_v{ver}_{stamp}")
    dst, i = base + ".yaml", 1
    while os.path.exists(dst):
        i += 1
        dst = f"{base}_{i}.yaml"
    shutil.copyfile(REGISTRY, dst)
    return dst


def make_backup():
    """CSV·registry를 자료창고 밖 stats_backup\\{날짜_시각}\\ 에 복사하고 해시로 대조한다. → (폴더, {이름: (원본 경로, 백업 경로, sha)})"""
    d = os.path.join(STATS_BACKUP_ROOT, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    i = 1
    while os.path.exists(d + ("" if i == 1 else f"_{i}")):
        i += 1
    d = d + ("" if i == 1 else f"_{i}")
    os.makedirs(d)
    items = {}
    for name, src in (("2026_잠정.csv", CUR), ("SOURCE_REGISTRY.yaml", REGISTRY)):
        dst = os.path.join(d, name)
        shutil.copyfile(src, dst)
        a, b = sha256(src), sha256(dst)
        if a != b:
            raise ApplyError(f"백업 해시 불일치: {name}")
        items[name] = (src, dst, a)
    return d, items


def atomic_copy(src, dst):
    """같은 폴더의 임시 파일에 복사한 뒤 os.replace로 바꾼다(교체는 한 번에 일어난다)."""
    tmp = dst + ".tmp_update"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def atomic_write_text(path, text):
    tmp = path + ".tmp_update"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def restore(items):
    """백업본으로 CSV·registry를 함께 되돌리고 해시로 확인한다. → 성공 여부"""
    ok = True
    for name, (src, bak, sha) in items.items():
        try:
            atomic_copy(bak, src)
            if sha256(src) != sha:
                raise ApplyError("복원 뒤 해시 불일치")
        except Exception as ex:   # noqa: BLE001
            ok = False
            print(f"★ 복원 실패({name}): {ex}  → 백업본으로 직접 되돌리세요: {bak}")
    return ok


def append_log(old_ver, new_ver, schema_bk, basis_date, nrows, fname, res, mc, new_sha, options):
    today = datetime.date.today().isoformat()
    with open(LOG, encoding="utf-8", newline="") as f:
        t = f.read()
    nl = "\r\n" if "\r\n" in t else "\n"
    lines = [
        f"## [{today}] schema | 2026년 방송심의 잠정본 월별 갱신({fname}, {nrows}행, 기준일 {basis_date}), SOURCE_REGISTRY.yaml v{old_ver} → v{new_ver} | Claude Sonnet 5.5",
        f"- 실행: update_stats_2026.py v1.1 --apply. 입력 `쳇지피팅용 병합_csv/{fname}`, 결과 `제미나이 노트북용 분할_csv/2026_잠정.csv`",
        f"- 검사: 누락 {len(res['missing'])}, 추가 {len(res['added'])}, 내용 변경 {len(res['changed'])}, 순번 변경 {res['seq_changed']}행. 월별 " + ", ".join(f"{m} {v}" for m, v in sorted(mc.items())),
        f"- SOURCE_REGISTRY.yaml: {REG_ID}의 period(기준일·행 수)와 notes 이력만 갱신, 보안 필드는 바꾸지 않음. 백업 Claude outputs/schema_backup/{os.path.basename(schema_bk)}",
        f"- 무결성: 새 파일 sha256 {new_sha}, 기준일 {basis_date}, 실행 옵션 {options}",
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


def apply(new_path, res, basis):
    """반영 본체. 성공하면 True. 쓰기 단계에서 실패하면 되돌린 뒤 종료 코드 1로 끝낸다."""
    fname = os.path.basename(new_path)
    nrows = len(res["new"])
    mc = collections.Counter(month(r, res["di"]) for r in res["new"])
    new_sha = sha256(new_path)
    options = "--apply"

    # ① 메모리에서 만들어 검증(여기서 실패하면 아무것도 안 바뀐다)
    try:
        new_text, old_v, new_v = build_registry_text(basis, nrows, fname, len(res["added"]), len(res["changed"]))
    except ApplyError as ex:
        sys.exit(f"중단: {ex}. 아무 파일도 바꾸지 않았습니다.")
    print("1) registry 새 내용 검증 (메모리)")
    if not validate_registry_text(new_text):
        sys.exit("중단: 새 registry 검증 실패. 아무 파일도 바꾸지 않았습니다.")

    # ② 백업
    try:
        schema_bk = schema_backup_registry(old_v)
        bdir, items = make_backup()
    except Exception as ex:   # noqa: BLE001  백업 실패 = 아직 아무것도 안 바꿈
        sys.exit(f"중단: 백업 실패({ex}). 아무 파일도 바꾸지 않았습니다.")
    print(f"2) 백업 완료: {bdir}")

    # ③~⑥ 쓰기. 어디서든 예외가 나면 둘 다 되돌린다.
    try:
        atomic_write_text(REGISTRY, new_text)
        print(f"3) SOURCE_REGISTRY.yaml v{old_v} → v{new_v} 쓰기 완료")
        atomic_copy(new_path, CUR)
        print("4) 2026_잠정.csv 교체 완료")
        with open(REGISTRY, encoding="utf-8", newline="") as f:
            if not validate_registry_text(f.read()):
                raise ApplyError("디스크의 registry 재검증 실패")
        if sha256(CUR) != new_sha:
            raise ApplyError("교체한 2026_잠정.csv의 sha256이 새 파일과 다릅니다")
        print("5) 디스크 재검증 OK (registry 파싱·CSV sha256 일치)")
        append_log(old_v, new_v, schema_bk, basis, nrows, fname, res, mc, new_sha, options)
        print("6) log.md 항목 추가 완료")
    except BaseException as ex:   # noqa: BLE001  Ctrl-C 포함
        print(f"★ 실패: {type(ex).__name__}: {ex}")
        ok = restore(items)
        print("되돌림 " + ("완료: CSV·registry가 실행 전과 같습니다." if ok else "일부 실패: 위 안내를 따르세요.")
              + " log·reindex는 만들지 않았습니다.")
        sys.exit(1)
    request_reindex(f"stats 잠정본 월별 갱신({fname})")
    print("끝. 다음: reindex_last.log의 exit=0 확인, wiki_lint.py 실행")
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
    apply(new_path, res, basis)


if __name__ == "__main__":
    main()
