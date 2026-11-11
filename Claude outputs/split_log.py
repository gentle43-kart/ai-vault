#!/usr/bin/env python3
# split_log.py v1.0 (2026-11-11)
# 목적: 0 wiki/log.md의 지난 달 항목을 0 wiki/log/YYYY-MM.md로 바이트 그대로 옮긴다(AGENTS.md 10절).
# 입력: <vault>/0 wiki/log.md. 항목은 줄 처음의 `## [YYYY-MM-DD]`로 시작한다. 그 앞은 머리말(log.md에 남김).
# 출력: <vault>/0 wiki/log/YYYY-MM.md (항목 바이트 그대로), 새 log.md(머리말 + keep-month 이후 항목).
# 규칙: 항목 월이 줄어드는 순서가 나오면 중단한다. 대상 조각 파일이 이미 있으면 중단한다.
#       검증: 원본 == 머리말 + 조각들(월 순서) + 새 log.md 본문(바이트 비교). 실패하면 아무것도 쓰지 않는다.
# 사용: python split_log.py [--vault "J:\AI 자료"] [--keep YYYY-MM] [--apply]   (기본: 점검만, 파일 변경 없음)
#       --keep 기본값은 오늘이 속한 달. 그 달 이전 항목을 조각으로 옮긴다.
# 검증값(2026-11-11 최초 실행 전): 576,642바이트, 2026-09 203개·2026-10 81개·2026-11 11개, 줄바꿈 LF, BOM 없음.
import argparse, datetime, os, re, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument('--vault', default=r'J:\AI 자료')
ap.add_argument('--keep', default=datetime.date.today().strftime('%Y-%m'))
ap.add_argument('--apply', action='store_true')
a = ap.parse_args()

wiki = os.path.join(a.vault, '0 wiki')
logp = os.path.join(wiki, 'log.md')
outd = os.path.join(wiki, 'log')
orig = open(logp, 'rb').read()

pat = re.compile(rb'^## \[(\d{4}-\d{2})-\d{2}\]', re.M)
ms = list(pat.finditer(orig))
if not ms:
    sys.exit('항목을 찾지 못했다')
header = orig[:ms[0].start()]
bounds = [m.start() for m in ms] + [len(orig)]
groups = []                    # (month, bytes) 연속 구간
count = {}
prev = ''
for i, m in enumerate(ms):
    mon = m.group(1).decode()
    if mon < prev:
        sys.exit(f'항목 월이 거꾸로 간다: {prev} 다음 {mon} (바이트 {m.start()})')
    prev = mon
    count[mon] = count.get(mon, 0) + 1
    seg = orig[bounds[i]:bounds[i + 1]]
    if groups and groups[-1][0] == mon:
        groups[-1][1].append(seg)
    else:
        groups.append((mon, [seg]))

old = [(mon, b''.join(s)) for mon, s in groups if mon < a.keep]
rest = b''.join(b''.join(s) for mon, s in groups if mon >= a.keep)
newlog = header + rest

# 검증: 원본 == 머리말 + 조각(월 순서) + 나머지
assert header + b''.join(b for _, b in old) + rest == orig, '이어 붙인 결과가 원본과 다르다'
print(f'원본 {len(orig):,}바이트, 항목 월별 {count}, keep={a.keep}')
for mon, b in old:
    print(f'  → log/{mon}.md {len(b):,}바이트 ({count[mon]}개)')
print(f'  log.md 새 크기 {len(newlog):,}바이트')
if not old:
    sys.exit('옮길 항목 없음')
for mon, _ in old:
    if os.path.exists(os.path.join(outd, mon + '.md')):
        sys.exit(f'log/{mon}.md가 이미 있다. 덮어쓰지 않는다')
if not a.apply:
    sys.exit('점검만 했다(--apply로 실제 적용)')

os.makedirs(outd, exist_ok=True)
for mon, b in old:
    with open(os.path.join(outd, mon + '.md'), 'wb') as f:
        f.write(b)
fd, tmp = tempfile.mkstemp(dir=wiki, suffix='.tmp')
with os.fdopen(fd, 'wb') as f:
    f.write(newlog)
os.replace(tmp, logp)
# 다시 읽어 확인
re_old = b''.join(open(os.path.join(outd, mon + '.md'), 'rb').read() for mon, _ in old)
re_new = open(logp, 'rb').read()
hl = len(header)
assert re_new[:hl] + re_old + re_new[hl:] == orig, '적용 후 재검증 실패'
print('적용 완료, 바이트 검증 일치')
