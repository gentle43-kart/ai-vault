# -*- coding: utf-8 -*-
"""
목적: 방송심의규정 제150호(2020.12.28.)와 제8호(2026.9.29. 시행) 변환본을 조 단위로 자동 대조한다.
      조 제목으로 구·신 조를 대응시키고(구 제69조→제80조, 구 제60조→제71조는 제목이 달라 수동 지정),
      띄어쓰기·가운뎃점(ㆍ/·)·따옴표·개정 주석(<개정 …>)을 지운 뒤 문자 단위 차이를 출력한다.
입력: 1 documents_md/법령_md/방송_md/ 의 제150호·제8호 변환본(.md)
출력: 표준출력. 내용이 다른 조마다 "=== 구제n조 → 신제m조 (제목) ratio=…"와 차이 조각 목록
검증값: 구 규정 실질 조 81개(삭제 조 제24조·제29조의2·제56~58조 제외)가 신 규정 81개 조와 모두 대응(미대응 0).
        같은 조 수와 대응은 [[조문 시기 대응표]] 2A절(renumber_2026.py MAP)과 일치(2026-10-06 확인).
한계: 구 변환본의 쪽머리("방송심의에 관한 규정", "법제처 n 국가법령정보센터")와 ⑯ 같은 원문자 누락이
      차이로 잡힐 수 있다. 판정은 출력 결과를 원문과 대조해 사람이 한다.
사용: python compare_bangsim_150_8.py  (작업 폴더와 무관하게 이 파일 위치 기준으로 자료를 찾는다)
작성: 2026-10-06 Claude Opus 5.5
"""
import re, difflib, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "1 documents_md", "법령_md", "방송_md")
OLD = "방송심의에 관한 규정(방송통신심의위원회규칙)(제150호)(20201228).md"
NEW = "방송심의에 관한 규정(규칙 제8호, 2026. 9. 21. 제정, 2026. 9. 29. 시행).md"
PAT = re.compile(r'^[ \t#\-\*]*(제\d+조(?:의\d+)?)\s*(\(|삭제)', re.M)
MANUAL = {"제69조": "제80조", "제60조": "제71조"}

def split(t):
    ms = list(PAT.finditer(t)); arts = {}; order = []
    for i, m in enumerate(ms):
        k = m.group(1)
        if k in arts:
            continue
        end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
        arts[k] = t[m.start():end]; order.append(k)
    return arts, order

def title(s):
    m = re.match(r'[ \t#\-\*]*제\d+조(?:의\d+)?\s*\(([^)]*)\)', s)
    return m.group(1) if m else 'DEL'

def norm(s):
    s = re.sub(r'<[^>]*>', '', s)
    s = re.sub(r'\[[^\]]*(신설|개정|삭제|전문|본조|제목)[^\]]*\]', '', s)
    s = s.replace('ㆍ', '·').replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    s = re.sub(r'^[ \t#\-\*]+', '', s, flags=re.M)
    s = re.sub(r'\s+', '', s)
    s = re.sub(r'^제\d+조(의\d+)?\([^)]*\)', '', s)
    s = re.sub(r'법제처\d+국가법령정보센터', '', s)
    s = re.sub(r'제\d+장.{0,20}$|제\d+절.{0,20}$', '', s)
    return s

def tnorm(x):
    return re.sub(r'\s', '', x.replace('ㆍ', '·'))

def build_map(A, oa, B, ob):
    nt = {tnorm(title(B[k])): k for k in ob}
    mp = []
    for k in oa:
        if title(A[k]) == 'DEL':
            continue
        mp.append((k, nt.get(tnorm(title(A[k]))) or MANUAL.get(k)))
    return mp

def main():
    A, oa = split(open(os.path.join(BASE, OLD), encoding='utf-8').read())
    B, ob = split(open(os.path.join(BASE, NEW), encoding='utf-8').read())
    mp = build_map(A, oa, B, ob)
    print(f"대응 {len(mp)}개, 미대응 {[m for m in mp if m[1] is None]}, 신 규정 조 {len(ob)}개")
    for k, n in mp:
        if n is None:
            continue
        a, b = norm(A[k]), norm(B[n])
        if a == b:
            continue
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        print(f"=== 구{k} → 신{n} ({title(B[n])}) ratio={sm.ratio():.3f}")
        for t, i1, i2, j1, j2 in sm.get_opcodes():
            if t != 'equal':
                print(f"  [{t}] -「{a[i1:i2]}」 +「{b[j1:j2]}」")

if __name__ == "__main__":
    main()
