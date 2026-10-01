"""2026.9.29. 제정 「정보통신에 관한 심의규정」(방송미디어통신심의위원회규칙 제12호) 조 번호 변경에 따른 위키 조문 페이지 이름 변경과 링크 치환.
AGENTS.md 3.1절(v1.20). 사용자 승인 2026-09-30 "진행해"(방송 쪽과 같은 방식).
MAP: [(구 번호, 구 제목, 신 번호, 신 제목)]  (구: 제164호, 신: 제12호). 1회용: 이미 적용된 위키에서는 중단한다.
치환 규칙: 통신심의규정 조문 페이지 안은 현행 이름, 쟁점 페이지는 [[현행]](구 제n조), 그 밖은 [[현행|구 표기]]. log.md, Clippings, _Inbox, _templates 제외.
"""
import os,re,sys
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','0 wiki')
LAW='통신심의규정'
MAP=[["제1조", "목적", "제1조", "목적"], ["제2조", "정의", "제2조", "정의"], ["제3조", "적용범위", "제3조", "적용범위"], ["제4조", "심의의 기본원칙", "제4조", "심의의 기본원칙"], ["제5조", "국제 평화 질서 위반 등", "제5조", "국제 평화 질서 위반 등"], ["제6조", "헌정질서 위반 등", "제6조", "헌정질서 위반 등"], ["제7조", "범죄 기타 법령 위반", "제7조", "범죄 기타 법령 위반"], ["제8조", "선량한 풍속 기타 사회질서 위반 등", "제8조", "선량한 풍속 기타 사회질서 위반 등"], ["제8조의2", "아동·청소년 보호", "제9조", "아동ㆍ청소년 보호"], ["제9조", "광고·선전 등의 제한", "제10조", "광고ㆍ선전 등의 제한"], ["제10조", "심의의 개시 등", "제11조", "심의의 개시 등"], ["제11조", "자료제출 요구", "제12조", "자료제출 요구"], ["제12조", "심의결정", "제13조", "심의결정"], ["제13조", "심의중지", "제14조", "심의중지"], ["제14조", "심의결정 통지 등", "제15조", "심의결정 통지 등"], ["제15조", "시정요구", "제16조", "시정요구"], ["제16조", "이의신청", "제17조", "이의신청"], ["제17조", "제재조치", "제18조", "제재조치"], ["제18조", "당사자등의 의견진술", "제19조", "당사자등의 의견진술"], ["제19조", "시정요구 이행 등 정지", "제20조", "시정요구 이행 등 정지"], ["제20조", "청소년유해매체물의 심의 등", "제21조", "청소년유해매체물의 심의 등"], ["제21조", "청소년유해매체물의 결정취소", "제22조", "청소년유해매체물의 결정취소"], ["제22조", "청소년유해매체물 준용규정", "제23조", "청소년유해매체물 준용규정"], ["제23조", "심의자료의 공개 등", "제24조", "심의자료의 공개 등"], ["제24조", "자료의 보존기간", "제25조", "자료의 보존기간"], ["제25조", "시행에 필요한 세부사항", "제26조", "시행에 필요한 세부사항"]]
SKIP_DIRS={'@clippings','@Inbox','@templates','_clippings','Clippings','_Inbox','_templates','.obsidian'}
def main(dry=False):
    art=os.path.join(ROOT,'조문')
    if os.path.exists(os.path.join(art,LAW+' 제26조.md')):
        print('이미 적용됨. 다시 실행하지 않는다.'); return
    cur={f'{LAW} {o}':f'{LAW} {n}' for o,ot,n,nt in MAP if o!=n}
    exist={f[:-3] for f in os.listdir(art) if f.endswith('.md')}
    moves=[(o,n) for o,n in cur.items() if o in exist]
    if not dry:
        for o,n in moves: os.rename(os.path.join(art,o+'.md'),os.path.join(art,o+'.__tmp__'))
        for o,n in moves: os.rename(os.path.join(art,o+'.__tmp__'),os.path.join(art,n+'.md'))
    pat=re.compile(r'\[\[('+LAW+r' 제\d+조(?:의\d+)?)(#[^\]|]*)?(\|[^\]]*)?\]\]')
    nf=nl=0
    for dp,dn,fn in os.walk(ROOT):
        dn[:]=[d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            if not f.endswith('.md') or f=='log.md': continue
            p=os.path.join(dp,f); t=open(p,encoding='utf-8').read()
            folder=os.path.basename(dp); ctx='cur' if (folder=='조문' and f.startswith(LAW+' ')) else ('issue' if folder=='쟁점' else 'other')
            c=[0]
            def sub(m):
                name,anc,disp=m.group(1),m.group(2) or '',m.group(3)
                if name not in cur: return m.group(0)
                c[0]+=1
                if disp is None and ctx=='issue': return '[['+cur[name]+anc+']](구 '+name.split(' ',1)[1]+')'
                if disp is None and ctx=='other': disp='|'+name
                return '[['+cur[name]+anc+(disp or '')+']]'
            t2=pat.sub(sub,t)
            if c[0]:
                nf+=1; nl+=c[0]
                if not dry: open(p,'w',encoding='utf-8').write(t2)
    print('renamed',len(moves),'files',nf,'links',nl)
if __name__=='__main__': main('--dry' in sys.argv)
