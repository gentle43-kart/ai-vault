# -*- coding: utf-8 -*-
"""
maintenance_check.py v1.1 (2026-11-12, Claude; v1.1: wiki_lint v1.6 대응 — 요약에 broken_links_log(log 기록의 끊긴 링크, 참고)를 따로 표시하고 lint 종료 1의 사유를 적는다. lint 출력이 JSON이 아니면 '실행 실패'로 기록한다; v1.0 2026-11-11)
목적: AGENTS_절차.md 6.8절 A 단계(무인 기계 점검). 토큰을 쓰지 않고 자료창고 상태를 점검해 B(월간 정비)·C(승인 후 처리)가 읽을 결과만 만든다.
입력: 자료창고 루트(기본 J:\\AI 자료), 검색 서버 폴더(기본 J:\\MCP\\ai-vault-mcp), SOURCE_REGISTRY.yaml, 0 wiki, 2 data_csv, git 저장소 2개, 이전 실행 결과(run_history.log, 이전 날짜의 *_check.json).
출력: <서버 폴더>\\data\\maintenance\\{YYYY-MM-DD}_check.json, {YYYY-MM-DD}_요약.md (같은 날 다시 실행하면 덮어쓴다).
      run_history.log는 run_maintenance_check.bat이 붙인다(이 스크립트는 읽기만 한다).
쓰기 범위: 위 두 파일뿐. 위키·스키마·통계 파일·search.db는 고치지 않는다. git은 읽기 명령만(--no-optional-locks) 쓴다.
점검: ① wiki_lint.py 실행(종료 0·1은 정상 실행. 1은 broken_sources·broken_links·yaml_error·sources_bad 중 하나라도 있다는 뜻이며 사유를 요약에 적는다. 그 밖의 값이나 JSON이 아닌 출력은 '실행 실패') ② @Inbox 대기 수, @clippings 새 파일 수
      ③ 새 △ 통계 파일(registry stats_2026_recent의 period·notes에 파일명이 없는 것) ④ log.md 분할 필요
      ⑤ 두 저장소의 미커밋 파일·미push 커밋·가장 오래된 미push 커밋 경과일 ⑥ reindex.failed, 이번 달 B 보고서 ⑦ 직전 실행 실패·8일 넘는 공백
재현성: '@clippings 새 파일'의 기준 시각은 '오늘보다 이전 날짜의 가장 최근 *_check.json'의 실행 시각이므로 같은 날 다시 실행해도 같은 값이 나온다.
        (이전 JSON이 없으면 기준 없음으로 보고 새 파일 수는 null)
검증값(2026-11-12 기준, lint v1.6): broken_links 0, broken_links_log 38, broken_sources 0. 2026-11-11 lint 보고 12절 수치와 대조.
종료 코드: 0 점검 완료(경고가 있어도 0), 1 점검 자체 실패(예외).
사용: python maintenance_check.py [--vault "J:\\AI 자료"] [--server "J:\\MCP\\ai-vault-mcp"]
"""
import argparse, datetime, glob, json, os, re, subprocess, sys, traceback

ap = argparse.ArgumentParser()
ap.add_argument('--vault', default=r'J:\AI 자료')
ap.add_argument('--server', default=r'J:\MCP\ai-vault-mcp')
a = ap.parse_args()

VAULT, SERVER = a.vault, a.server
OUT = os.path.join(SERVER, 'data', 'maintenance')
NOW = datetime.datetime.now().replace(microsecond=0)
TODAY = NOW.strftime('%Y-%m-%d')
THIS_MONTH = NOW.strftime('%Y-%m')
os.makedirs(OUT, exist_ok=True)
env = dict(os.environ, PYTHONIOENCODING='utf-8')


def run(cmd, cwd=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout, env=env, encoding='utf-8', errors='replace')


# ---------- 직전 실행 기준 ----------
def prev_check():
    best = None
    for p in glob.glob(os.path.join(OUT, '*_check.json')):
        d = os.path.basename(p)[:10]
        if d < TODAY and (best is None or d > best[0]):
            best = (d, p)
    if not best:
        return None, None
    try:
        j = json.load(open(best[1], encoding='utf-8'))
        return datetime.datetime.fromisoformat(j['run_at']), best[0]
    except Exception:
        return None, best[0]


prev_at, prev_date = prev_check()

# ---------- 실행 이력(직전 실패·공백) ----------
hist = {'last_line': None, 'last_rc': None, 'last_at': None, 'gap_days': None, 'last_failed': False, 'gap_over_8': False}
hp = os.path.join(OUT, 'run_history.log')
if os.path.exists(hp):
    lines = [l.strip() for l in open(hp, encoding='utf-8', errors='replace') if l.strip()]
    for l in reversed(lines):
        m = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\d+)$', l)
        if m:
            hist.update(last_line=l, last_at=m.group(1), last_rc=int(m.group(2)))
            t = datetime.datetime.fromisoformat(m.group(1))
            hist['gap_days'] = (NOW - t).days
            hist['last_failed'] = int(m.group(2)) != 0
            hist['gap_over_8'] = (NOW - t).days > 8
            break
else:
    hist['note'] = 'run_history.log 없음(첫 실행)'

# ---------- ① lint ----------
lint = {}
lp = os.path.join(VAULT, 'Claude outputs', 'wiki_lint.py')
r = run([sys.executable, '-X', 'utf8', lp, VAULT])
lint['exit'] = r.returncode
L = None
if r.returncode in (0, 1):
    try:
        L = json.loads(r.stdout)
    except ValueError:   # lint가 예외로 죽어도 파이썬은 1을 내므로 JSON 여부로 다시 구분한다
        L = None
if L is not None:
    oi = L.get('_open_items', {})
    lint.update(
        broken_sources=len(L.get('broken_sources') or []),
        broken_sources_list=L.get('broken_sources') if isinstance(L.get('broken_sources'), list) else sorted(L.get('broken_sources', {}).keys()),
        conflict_marks_pages=len(L.get('conflict_marks', {})),
        conflict_marks_total=sum(L.get('conflict_marks', {}).values()),
        open_items_total=sum(len(v.get('open', [])) for v in oi.values()),
        open_items_pages=sum(1 for v in oi.values() if v.get('open')),
        external_wait=L.get('external_wait', {}),
        yaml_error=len(L.get('yaml_error', {})), broken_links=len(L.get('broken_links', {})), broken_links_log=len(L.get('broken_links_log', {})),
        exit_reasons=L.get('exit_reasons', []),
        orphans=len(L.get('orphans', [])), index_missing=len(L.get('index_missing', [])),
        sources_bad=len(L.get('sources_bad') or []), internal_suspect=len(L.get('internal_suspect') or []),
        stray_root_files=len(L.get('stray_root_files') or []), articles_total=L.get('articles_total'),
        articles_no_verified=L.get('articles_no_verified'), pages=L.get('counts', {}).get('pages'))
else:
    lint['error'] = (r.stderr or r.stdout or 'JSON이 아닌 출력')[-500:]

# ---------- ② 수신함·클리핑 ----------
inbox = 0
ibd = os.path.join(VAULT, '0 wiki', '@Inbox')
for p in glob.glob(os.path.join(ibd, '**', '*.md'), recursive=True):
    head = open(p, encoding='utf-8', errors='replace').read(4000)
    m = re.match(r'^---\n(.*?)\n---', head, re.S)
    if m and re.search(r'^status:\s*대기\s*$', m.group(1), re.M):
        inbox += 1
clip_new = None
cd = os.path.join(VAULT, '0 wiki', '@clippings')
clip_total = 0
if os.path.isdir(cd):
    files = glob.glob(os.path.join(cd, '**', '*.md'), recursive=True)
    clip_total = len(files)
    if prev_at:
        ts = prev_at.timestamp()
        clip_new = sum(1 for f in files if os.stat(f).st_ctime > ts)   # Windows: st_ctime = 생성 시각

# ---------- ③ 새 △ 통계 파일 ----------
new_tri = []
tri_all = []
try:
    import yaml
    reg = yaml.safe_load(open(os.path.join(VAULT, 'SOURCE_REGISTRY.yaml'), encoding='utf-8'))
    items = next(v for v in reg.values() if isinstance(v, list))
    ent = next(i for i in items if i.get('id') == 'stats_2026_recent')
    txt = str(ent.get('period', '')) + '\n' + str(ent.get('notes', ''))
    d = os.path.join(VAULT, '2 data_csv', '통계_csv', '방송', '쳇지피팅용 병합_csv')
    for f in sorted(os.listdir(d)):
        if f.startswith('△') and f.lower().endswith('.csv'):
            tri_all.append(f)
            if f not in txt and os.path.splitext(f)[0] not in txt:
                new_tri.append(f)
except Exception as e:
    new_tri = None
    tri_err = str(e)

# ---------- ④ log 분할 ----------
log_first = None
lg = os.path.join(VAULT, '0 wiki', 'log.md')
with open(lg, encoding='utf-8') as f:
    for line in f:
        m = re.match(r'^## \[(\d{4}-\d{2})-\d{2}\]', line)
        if m:
            log_first = m.group(1)
            break
log_split_needed = bool(log_first and log_first < THIS_MONTH)

# ---------- ⑤ git ----------
def git_state(path):
    g = ['git', '--no-optional-locks', '-c', 'core.autocrlf=true', '-c', 'core.quotepath=false']
    s = {'path': path}
    st = run(g + ['status', '--porcelain'], cwd=path)
    s['uncommitted'] = len([l for l in st.stdout.splitlines() if l.strip()]) if st.returncode == 0 else None
    up = run(g + ['rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], cwd=path)
    if up.returncode != 0:
        s.update(upstream=None, unpushed=None, oldest_unpushed_days=None, note='upstream 없음')
        return s
    s['upstream'] = up.stdout.strip()
    lg_ = run(g + ['log', '@{u}..HEAD', '--format=%ct'], cwd=path)
    cts = [int(x) for x in lg_.stdout.split()]
    s['unpushed'] = len(cts)
    s['oldest_unpushed_days'] = (NOW - datetime.datetime.fromtimestamp(min(cts))).days if cts else None
    s['push_advised'] = bool(cts) and (len(cts) >= 10 or s['oldest_unpushed_days'] > 7)
    return s


git = {'vault': git_state(VAULT), 'server': git_state(SERVER)}

# ---------- ⑥ reindex.failed, B 보고서 ----------
reindex_failed = os.path.exists(os.path.join(SERVER, 'data', 'reindex.failed'))
b_reports = sorted(os.path.basename(p) for p in glob.glob(os.path.join(VAULT, '0 wiki', '분석', THIS_MONTH + '-* lint 보고.md')))

# ---------- 결과 ----------
res = dict(version='1.1', run_at=NOW.isoformat(), baseline_prev_check=prev_date, history=hist, lint=lint,
           inbox_waiting=inbox, clippings_total=clip_total, clippings_new_since_prev=clip_new,
           stats_tri_files=tri_all, stats_tri_new=new_tri, log_first_month=log_first, log_split_needed=log_split_needed,
           git=git, reindex_failed=reindex_failed, b_report_this_month=b_reports)
with open(os.path.join(OUT, TODAY + '_check.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)

# ---------- 요약 ----------
S = []
warn = []
if hist['last_failed']:
    warn.append(f"직전 실행 실패: {hist['last_line']} (종료코드 {hist['last_rc']})")
if hist['gap_over_8']:
    warn.append(f"실행 공백 {hist['gap_days']}일(마지막 {hist['last_at']})")
S.append(f'# AI 자료창고 정기 점검(A) {TODAY}')
S.append('')
S.append('## 경고' if warn else '## 경고 없음(직전 실행 정상, 8일 넘는 공백 없음)')
S += [f'- {w}' for w in warn]
S.append('')
S.append('## 요약')
if 'error' in lint:
    S.append(f"- **lint 실행 실패**(종료 {lint['exit']}): {lint['error'][-200:]}")
else:
    bs = f"**깨진 출처 {lint['broken_sources']}건**: {lint['broken_sources_list']}" if lint['broken_sources'] else '깨진 출처 0'
    S.append(f"- lint(종료 {lint['exit']}{'; 사유: ' + ', '.join(lint['exit_reasons']) if lint['exit_reasons'] else ''}): {bs} · 〔충돌〕 {lint['conflict_marks_total']}곳({lint['conflict_marks_pages']}쪽) · 열린 항목 {lint['open_items_total']}({lint['open_items_pages']}쪽) · 깨진 링크 {lint['broken_links']}(log 기록 {lint['broken_links_log']}, 참고) · 고립 {lint['orphans']} · 색인 누락 {lint['index_missing']} · 머리말 오류 {lint['yaml_error']}")
S.append(f"- 수신함 대기 {inbox}건 · 클리핑 새 파일 {clip_new if clip_new is not None else '기준 없음'}건(전체 {clip_total}, 기준 {prev_date or '없음'})")
S.append('- 새 △ 파일: ' + ('감지 못함(점검 실패)' if new_tri is None else ('**' + ', '.join(new_tri) + '** → C: stats-monthly-update' if new_tri else '없음')))
S.append(f"- log.md 첫 항목 {log_first}: " + ('**분할 필요**(C: split_log.py)' if log_split_needed else '분할 불필요'))
for k, nm in (('vault', 'J:\\AI 자료'), ('server', 'J:\\MCP\\ai-vault-mcp')):
    g = git[k]
    if g.get('upstream') is None:
        S.append(f"- git {nm}: 미커밋 {g['uncommitted']}개 · upstream 없음(미push 계산 불가)")
    else:
        old = f"{g['oldest_unpushed_days']}일" if g['unpushed'] else '-'
        S.append(f"- git {nm}: 미커밋 {g['uncommitted']}개 · 미push {g['unpushed']}개(가장 오래된 {old})" + (' → **push 권고**' if g['push_advised'] else ''))
S.append('- reindex.failed: ' + ('**있음** → data\\index_failed.txt 확인' if reindex_failed else '없음'))
S.append(f"- 이번 달 B 보고서: " + (', '.join(b_reports) if b_reports else '없음' + ('(B는 첫째 주 수요일 14:13 실행)' )))
S.append('')
S.append('결과 파일: ' + os.path.join(OUT, TODAY + '_check.json'))
with open(os.path.join(OUT, TODAY + '_요약.md'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(S) + '\n')
print('\n'.join(S))
