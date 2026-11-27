# -*- coding: utf-8 -*-
"""
vault_check.py v1.0 (2026-11-27, Claude Opus 5.5)
목적: 자료창고의 자료 쪽 규칙을 AI 없이 매번 같게 점검한다(위키 페이지 점검은 wiki_lint.py가 한다).
  G1 레지스트리: SOURCE_REGISTRY.yaml 파싱, id 중복, path·raw_source·scan_dirs 존재, duplicate_of가 가리키는 id 존재
  G2 기준본 CSV 지문: registry에서 2 data_csv/ 아래 canonical 항목(stats_2026_recent 제외)의 파일별 크기·sha1·줄 수를
     기준값 파일과 비교한다(바뀜·새 파일·사라진 파일을 보고). 기준본은 바뀌면 안 되는 자료이다(AGENTS_통계기준.md).
  G3 검증값 실행 모음: 기존 집계 스크립트의 --verify와 서버의 check_decision_parse.py를 실행해 종료 코드를 모은다
     (통계기준의 '스크립트·검증값'. 각 스크립트는 불일치면 종료 코드 1).
  옛 폴더명: 2026-11-26 이름 변경 전의 폴더명 4개가 규칙·스킬·스크립트·위키 본문에 다시 쓰였는지 찾는다
     (log·@clippings·schema_backup·registry notes는 과거 기록이라 뺀다).
입력: 자료창고 루트(--vault, 기본 J:\\AI 자료), 검색 서버 폴더(--server, 기본 J:\\MCP\\ai-vault-mcp)
출력: 표준출력에 JSON. 자료창고 파일은 고치지 않는다(읽기 전용, 자동 수정 없음).
      --baseline을 줄 때만 <서버>\\data\\maintenance\\csv_baseline.json을 만든다(기존 파일은 csv_baseline_{YYYYMMDD-HHMMSS}.json으로 남김).
      기준값 갱신은 기준본이 바뀐 이유를 사용자가 확인한 뒤 사용자 지시로만 한다.
종료 코드: 위반(registry·csv·verify·old_names 중 하나라도)이나 기준값 없음이면 1, 모두 없으면 0.
검증값: 2026-11-27 첫 실행 — registry id 87개·위반 0, 검증 스크립트 6개 모두 종료 0, 옛 폴더명 0건.
사용: python -X utf8 vault_check.py [--baseline] [--skip-verify] [--vault ...] [--server ...]
수정할 때 알아둘 곳: 검증 스크립트 목록은 VERIFY_CMDS, 옛 이름은 OLD_NAMES, 옛 이름 검색 범위는 old_name_targets().
"""
import argparse, datetime, glob, hashlib, json, os, subprocess, sys, time
import yaml

sys.stdout.reconfigure(encoding="utf-8")   # cp949 콘솔에서도 출력이 죽지 않게

ap = argparse.ArgumentParser()
ap.add_argument("--vault", default=r"J:\AI 자료")
ap.add_argument("--server", default=r"J:\MCP\ai-vault-mcp")
ap.add_argument("--baseline", action="store_true", help="CSV 지문 기준값을 새로 만든다(사용자 지시가 있을 때만)")
ap.add_argument("--skip-verify", action="store_true", help="G3을 건너뛴다(빠른 확인용)")
A = ap.parse_args()
V, SRV = A.vault, A.server
OUT_DIR = os.path.join(SRV, "data", "maintenance")
BASELINE = os.path.join(OUT_DIR, "csv_baseline.json")
CO = os.path.join(V, "Claude outputs")

OLD_NAMES = ["제미나이 노트북용 분할_csv", "쳇지피팅용 병합_csv", "제미나이 노트북용 분할본_md", "챗지피티용_md"]
VERIFY_CMDS = [  # (이름, 스크립트 경로, 인자)
    ("stats_articles", os.path.join(CO, "stats_articles.py"), ["--verify"]),
    ("sanction_results", os.path.join(CO, "sanction_results.py"), ["--verify"]),
    ("sangpan_articles", os.path.join(CO, "sangpan_articles.py"), ["--verify"]),
    ("grade_articles", os.path.join(CO, "grade_articles.py"), ["--verify"]),
    ("telecom_stats", os.path.join(CO, "telecom_stats.py"), ["--verify"]),
    ("check_decision_parse", os.path.join(SRV, "check_decision_parse.py"), []),
]
EXCLUDE_IDS = {"stats_2026_recent"}   # 매월 덮어쓰는 잠정본. 행 감소는 update_stats_2026.py가 막는다
TEXT_EXT = (".md", ".py", ".bat", ".yaml", ".yml", ".json", ".txt")

R = {"version": "1.0", "run_at": datetime.datetime.now().isoformat(timespec="seconds")}


def P(rel):
    return os.path.join(V, rel.replace("/", os.sep))


# ---------- G1 레지스트리 ----------
reg_v = []
try:
    reg = yaml.safe_load(open(os.path.join(V, "SOURCE_REGISTRY.yaml"), encoding="utf-8"))
    S = reg["sources"]
except Exception as ex:
    reg, S = None, []
    reg_v.append({"위치": "SOURCE_REGISTRY.yaml", "내용": f"YAML 파싱 실패: {ex}"})
ids = {}
for i in S:
    ids.setdefault(i.get("id"), []).append(i)
for k, v in ids.items():
    if len(v) > 1:
        reg_v.append({"위치": f"id {k}", "내용": f"id 중복 {len(v)}개"})
for i in S:
    pid = i.get("id")
    if not i.get("path"):
        reg_v.append({"위치": f"id {pid}", "내용": "path 없음"})
    elif not os.path.exists(P(i["path"])):
        reg_v.append({"위치": f"id {pid}", "내용": f"path가 없는 경로: {i['path']}"})
    rs = i.get("raw_source")
    for r in (rs if isinstance(rs, list) else [rs] if rs else []):
        if isinstance(r, str) and not os.path.exists(P(r)):
            reg_v.append({"위치": f"id {pid}", "내용": f"raw_source가 없는 경로: {r}"})
    d = i.get("duplicate_of")
    if d and d not in ids:
        reg_v.append({"위치": f"id {pid}", "내용": f"duplicate_of가 없는 id를 가리킴: {d}"})
for s in (reg or {}).get("scan_dirs") or []:
    if not os.path.exists(P(s)):
        reg_v.append({"위치": "scan_dirs", "내용": f"없는 경로: {s}"})
R["registry"] = {"ids": len(ids), "violations": reg_v}


# ---------- G2 기준본 CSV 지문 ----------
def fingerprint(path):
    h, n, size = hashlib.sha1(), 0, 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk); n += chunk.count(b"\n"); size += len(chunk)
    return {"size": size, "sha1": h.hexdigest(), "lines": n}


excl_paths = {os.path.normcase(P(i["path"])) for i in S if i.get("id") in EXCLUDE_IDS}
targets = {}
for i in S:
    p = str(i.get("path", ""))
    if not p.startswith("2 data_csv/") or i.get("canonical") is False or i.get("id") in EXCLUDE_IDS:
        continue
    full = P(p)
    files = [full] if os.path.isfile(full) else [f for f in glob.glob(os.path.join(full, "**", "*"), recursive=True) if os.path.isfile(f)]
    for f in files:
        if os.path.normcase(f) not in excl_paths:
            targets[os.path.relpath(f, V).replace(os.sep, "/")] = i["id"]
t0 = time.time()
now = {rel: dict(fingerprint(P(rel)), id=rid) for rel, rid in sorted(targets.items())}
csv_v, csv_info = [], {"files": len(now), "seconds": round(time.time() - t0, 1)}
if A.baseline:
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(BASELINE):
        keep = BASELINE.replace(".json", "_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
        os.replace(BASELINE, keep); csv_info["previous_kept"] = keep
    json.dump({"made_at": R["run_at"], "files": now}, open(BASELINE, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    csv_info["baseline_written"] = BASELINE
elif not os.path.exists(BASELINE):
    csv_info["baseline_missing"] = BASELINE
else:
    base = json.load(open(BASELINE, encoding="utf-8"))
    csv_info["baseline_made_at"] = base.get("made_at")
    bf = base["files"]
    for rel in sorted(set(bf) | set(now)):
        a, b = bf.get(rel), now.get(rel)
        if a and not b:
            csv_v.append({"파일": rel, "내용": "기준값에 있는 파일이 사라짐"})
        elif b and not a:
            csv_v.append({"파일": rel, "내용": f"기준값에 없는 새 파일(id {b['id']}, {b['lines']:,}줄)"})
        elif a["sha1"] != b["sha1"]:
            csv_v.append({"파일": rel, "내용": f"내용이 바뀜: 크기 {a['size']:,}→{b['size']:,}, 줄 {a['lines']:,}→{b['lines']:,}"})
csv_info["violations"] = csv_v
R["csv"] = csv_info


# ---------- G3 검증값 실행 모음 ----------
ver = []
if not A.skip_verify:
    for name, script, args in VERIFY_CMDS:
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", script] + args, cwd=os.path.dirname(script),
                               capture_output=True, encoding="utf-8", errors="replace", timeout=600)
            last = [l for l in (r.stdout or "").splitlines() if l.strip()][-1:] or [""]
            ver.append({"이름": name, "exit": r.returncode, "마지막 줄": last[0][:120],
                        "오류": (r.stderr or "").strip()[-300:] if r.returncode else "", "seconds": round(time.time() - t0, 1)})
        except Exception as ex:
            ver.append({"이름": name, "exit": None, "오류": str(ex)[:300]})
R["verify"] = {"skipped": A.skip_verify, "results": ver, "failed": [x["이름"] for x in ver if x.get("exit") != 0]}


# ---------- 옛 폴더명 ----------
def old_name_targets():
    roots = [os.path.join(V, "0 wiki"), CO, os.path.join(V, "4 스킬, 프로젝트"), os.path.join(V, ".claude", "skills"), SRV]
    skip_dirs = {"@clippings", "log", "schema_backup", "__pycache__", ".git", "data", "data_reading", "_to_delete"}
    for root in roots:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in skip_dirs]
            for fn in fns:
                f = os.path.join(dp, fn)
                if fn.lower().endswith(TEXT_EXT) and not (dp == os.path.join(V, "0 wiki") and fn == "log.md") \
                        and os.path.abspath(f) != os.path.abspath(__file__) and os.path.getsize(f) < 5_000_000:
                    yield f
    for fn in os.listdir(V):
        if fn.startswith(("AGENTS", "CLAUDE")) and fn.endswith(".md"):
            yield os.path.join(V, fn)


old_v = []
for f in old_name_targets():
    try:
        lines = open(f, encoding="utf-8").read().splitlines()
    except (UnicodeDecodeError, OSError):
        continue
    for n, line in enumerate(lines, 1):
        for t in OLD_NAMES:
            if t in line:
                old_v.append({"파일": os.path.relpath(f, V) if f.startswith(V) else f, "줄": n, "내용": t})


def walk_yaml(x, path=""):   # registry는 notes(변경 이력)를 빼고 값만 본다
    if isinstance(x, dict):
        for k, v in x.items():
            if k != "notes":
                yield from walk_yaml(v, f"{path}.{k}" if path else str(k))
    elif isinstance(x, list):
        for j, v in enumerate(x):
            yield from walk_yaml(v, f"{path}[{j}]")
    elif isinstance(x, str):
        yield path, x


for where, s in walk_yaml(reg or {}):
    for t in OLD_NAMES:
        if t in s:
            old_v.append({"파일": "SOURCE_REGISTRY.yaml", "줄": where, "내용": t})
R["old_names"] = old_v

# ---------- 종료 ----------
reasons = [k for k, bad in (("registry", reg_v), ("csv", csv_v), ("verify", R["verify"]["failed"]), ("old_names", old_v),
                            ("csv_baseline_missing", "baseline_missing" in csv_info)) if bad]
R["exit_reasons"] = reasons
print(json.dumps(R, ensure_ascii=False, indent=1))
sys.exit(1 if reasons else 0)
