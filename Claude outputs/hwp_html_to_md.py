# 목적: hwp5html(pyhwp)로 만든 index.xhtml을 md 변환본으로 기계 변환한다(AGENTS_절차.md 6.7).
#       hwp5txt는 표 내용을 버리므로(<표>만 남음), 별표처럼 표가 핵심인 HWP는 이 경로로 변환한다.
# 입력: index.xhtml 경로, 출력 md 경로, 원본 경로(머리 주석용)
# 출력: 문단은 한 줄씩, 표는 마크다운 표(셀 안 줄바꿈은 <br>, rowspan/colspan은 첫 칸에만 글자를 넣고 나머지는 빈칸)
# 검증: 변환 뒤 표 개수와 원문 핵심 문구(예: 배점 합계 표기) 존재 여부를 확인한다. 내용은 요약·수정하지 않는다.
# 사용: python3 hwp_html_to_md.py index.xhtml out.md "3 source_raw/....hwp"
import sys, re
from bs4 import BeautifulSoup, NavigableString


def own_text(p):
    """문단 안에 들어 있는 표(hwp5html은 표를 문단 안에 둔다)의 글자를 빼고 문단 자체의 글자만 돌려준다."""
    import copy
    q = copy.copy(p)
    for t in q.find_all('table'):
        t.decompose()
    return re.sub(r'\s+', ' ', q.get_text('')).strip()

def text_of(el):
    parts = []
    for p in el.find_all(['p'], recursive=True) or [el]:
        t = p.get_text('')
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            parts.append(t)
    return parts

def table_md(tbl):
    rows = []
    for tr in tbl.find_all('tr'):
        if tr.find_parent('table') is not tbl:
            continue
        cells = []
        for td in tr.find_all(['td', 'th']):
            if td.find_parent('tr') is not tr:
                continue
            inner = []
            for child in td.find_all(['p', 'table']):
                if child.name == 'table' and child.find_parent('td') is td:
                    inner.append('[표] ' + ' / '.join(' ; '.join(own_text(q) for q in c.find_all('p') if q.find_parent('td') is c) for c in child.find_all('td') if c.find_parent('table') is child))
                elif child.name == 'p' and child.find_parent('table') is tbl:
                    t = own_text(child)
                    if t:
                        inner.append(t)
            cell = '<br>'.join(inner).replace('|', '\\|')
            cells.append(cell)
            for _ in range(int(td.get('colspan', 1)) - 1):
                cells.append('')
        if any(c.strip() for c in cells):
            rows.append(cells)
    if not rows:
        return ''
    w = max(len(r) for r in rows)
    rows = [r + [''] * (w - len(r)) for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * w]
    out += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return '\n'.join(out)

def main(src, dst, raw):
    soup = BeautifulSoup(open(src, encoding='utf-8').read(), 'html.parser')
    body = soup.body
    lines = [f'<!-- 원본: {raw} / 변환: pyhwp hwp5html + Claude outputs/hwp_html_to_md.py (기계 변환, 내용 수정 없음) -->', '']
    ntab = 0
    for el in body.find_all(['p', 'table']):
        if el.name == 'table':
            if el.find_parent('table'):
                continue
            md = table_md(el)
            if md:
                ntab += 1
                lines += ['', md, '']
        else:
            if el.find_parent('table'):
                continue
            t = own_text(el)
            lines.append(t)
    txt = '\n'.join(lines)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    open(dst, 'w', encoding='utf-8').write(txt.strip() + '\n')
    print('tables', ntab, 'chars', len(txt))

if __name__ == '__main__':
    main(*sys.argv[1:4])
