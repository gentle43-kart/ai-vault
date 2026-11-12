# -*- coding: utf-8 -*-
"""
open_items_classify.py v1.0 (2026-11-12, Claude Opus 5.5)
목적: 위키 페이지 "추가 확인 필요" 절의 열린 항목(미완료 체크박스)을 검토 유형별로 기계 분류하고,
      같은 문장이 반복되는 항목을 묶어 일괄 처리 후보로 보여 준다(AGENTS_절차.md 6.6절 "추가 확인 필요" 미해결 항목).
입력: 자료창고 루트(기본값: 이 파일의 상위 폴더). wiki_lint.py를 실행해 그 JSON의 _open_items를 쓴다(읽기 전용).
분류: 항목 문장에서 "(근거: …)" 앞부분을 먼저 보고, 맞는 유형이 없으면 근거 부분까지 본다. 아래 RULES 순서대로 처음 맞는 유형 하나에만 넣는다.
      키워드 기계 분류이므로 경계 항목은 사람이 다시 볼 수 있다(유형은 처리 순서를 정하기 위한 것이며 내용 판단이 아니다).
출력: 표준출력에 마크다운. 기본은 유형×페이지 종류 표와 반복 문장 묶음(3개 이상).
      --list "A" 처럼 유형 기호를 주면 그 유형의 전체 항목을 페이지별로 출력한다. --json이면 분류 결과 JSON.
검증값(2026-11-12, wiki_lint v1.6): 열린 항목 731개(389쪽). A 121, B 56, C 112, D 133, E 208, F 101(합계 731). 반복 문장 묶음 최대 68개(E).
"""
import os, re, sys, json, subprocess, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:]]
if args and not args[0].startswith('--'):
    ROOT = args.pop(0)

RULES = [
    ('A', '현행 법령·조문 대조', r'현행|국가법령정보센터|시행 예정|개정 여부|조 번호 변동|시행일|effective_from|법령 MCP|등재'),
    ('B', '판결·소송·후속 결정', r'판결|소송|환송|항소|상고|헌재|헌법재판|후속 결정|후속 조치|재심|행정심판'),
    ('C', '집계·통계 근거', r'CSV|csv|통계|건수|집계|\d+행|비율|빈도|분포'),
    ('D', '개정 연혁·개정 이유', r'개정 이유|신설 이유|개정 사유|연혁|제정|개정 전|삭제 이유|이유서|개정 경위|문언|개정 이력|개정 내용'),
    ('E', '회의록·의결 사례 조사', r'회의록|의결서|사례|적용한 예|적용 예|의결'),
]
OTHER = ('F', '해석·기준·기타')
NAMES = dict([(c, n) for c, n, _ in RULES] + [OTHER])


def classify(text):
    m = re.search(r'\(근거:', text)
    head, tail = (text[:m.start()], text[m.start():]) if m else (text, '')
    for part in (head, tail):
        for code, _, pat in RULES:
            if re.search(pat, part):
                return code
    return OTHER[0]


def norm(x):
    x = re.sub(r'\(근거:.*$', '', x).strip()
    x = re.sub(r'제\d+(조|호|항)(의\d+)?', r'제N\1', x)
    x = re.sub(r'\d{4}\.\s?\d{1,2}\.\s?\d{1,2}\.', 'YYYY.M.D.', x)
    return re.sub(r'\d+', 'N', x)


def load():
    lint = os.path.join(ROOT, 'Claude outputs', 'wiki_lint.py')
    r = subprocess.run([sys.executable, lint, ROOT], capture_output=True, text=True, encoding='utf-8')
    if r.returncode not in (0, 1):
        sys.exit(f'wiki_lint 실행 실패(종료 {r.returncode}): {r.stderr[-300:]}')
    return json.loads(r.stdout)['_open_items']


def main():
    oi = load()
    rows = [(k, x, classify(x)) for k, v in oi.items() for x in v['open']]
    if '--json' in args:
        print(json.dumps([dict(page=k, item=x, type=c) for k, x, c in rows], ensure_ascii=False, indent=1))
        return
    if '--list' in args:
        want = args[args.index('--list') + 1]
        by = collections.defaultdict(list)
        for k, x, c in rows:
            if c == want:
                by[k].append(x)
        print(f'## {want} {NAMES.get(want, "")} ({sum(len(v) for v in by.values())}개, {len(by)}쪽)\n')
        for k in sorted(by):
            print(f'- [[{os.path.basename(k)[:-3]}]]')
            for x in by[k]:
                print(f'  - {x}')
        return
    kinds = ['조문', '쟁점', '사례', '문서', '분석']
    tab = collections.Counter((c, k.split('/')[0]) for k, _, c in rows)
    print(f'열린 항목 {len(rows)}개, {len(oi)}쪽\n')
    print('| 유형 | ' + ' | '.join(kinds) + ' | 합계 |')
    print('|---|' + '---:|' * (len(kinds) + 1))
    for code in [c for c, _, _ in RULES] + [OTHER[0]]:
        vals = [tab[(code, kd)] for kd in kinds]
        print(f'| {code} {NAMES[code]} | ' + ' | '.join(str(v) for v in vals) + f' | {sum(vals)} |')
    print('\n반복 문장 묶음(3개 이상, 조·호·날짜·숫자를 N으로 바꿔 비교):\n')
    cnt = collections.Counter(norm(x) for _, x, _ in rows)
    for t, n in cnt.most_common():
        if n < 3:
            break
        code = collections.Counter(c for _, x, c in rows if norm(x) == t).most_common(1)[0][0]
        print(f'- {n}개 ({code}): {t}')


if __name__ == '__main__':
    main()
