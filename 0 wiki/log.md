---
type: log
---

# 작업 이력

형식과 규칙은 AGENTS.md 9절을 따른다. 맨 아래에 추가만 한다.

## [2026-11-02] ingest | 지각·조퇴·외출 휴가 반영 기준 관련 세부내용 변환·문서 페이지 | Claude Opus 5.5
- 사용자 지시: "소스 폴더 법령-일반 하위 폴더에 내용 추가했어. 확인 후 위키 반영". 3 source_raw/법령 등_raw/일반_raw/에서 2026-10-30 이후 추가 파일은 1건(하위 폴더 없음). 변환본이 없어 6.7 변환을 포함해 처리
- 원본: 3 source_raw/법령 등_raw/일반_raw/지각·조퇴·외출 휴가 반영 기준 관련 세부내용.pdf(7쪽, 텍스트 PDF). 붙임(p.1~3)과 직원 안내문 "(참고)"(p.4~7). 노사합의에 따른 복무 기준, 2026.11.1. 시행. 작성일·문서번호 없음
- 변환본 추가(6.7): 1 documents_md/법령_md/일반_md/지각·조퇴·외출 휴가 반영 기준 관련 세부내용.md. 도구 pdftotext(쪽 단위, 기본 모드), 쪽마다 `<!-- p.N -->`. 점검: 쪽 7/7, 대체문자 0, 공백 제거 후 pdftotext -layout 추출본과 2,804자 일치
- registry: `law_general`(폴더 단위, public·원격 허용·ingest wiki) 범위라 SOURCE_REGISTRY.yaml은 고치지 않음. 노사합의 관련 자료이나 사용자 기본값(public, 2026-10-16 결정)에 따름
- 생성: [[지각·조퇴·외출 휴가 반영 기준 관련 세부내용]](doc_kind 기타, domain 제도·조직, base_date 시행일 2026-11-01)
- 갱신: [[안_「방송미디어통신심의위원회 사무처 취업세칙」 제정안]] 2절(제27조 제4항 병가 미사용 가산이 종전에 없는 신설 조항이고 이 기준이 그 시행 전을 전제함), 4절(관련 링크, "제27조 제4항 미대조" 문구 정정), sources 추가. 문서/_index.md
- 대조: 종전 취업세칙(규정집(2024) 기준본 변환본 9985행~, 제20조 10065행·제21조 10069행·제22조 10071행·제27조 10093~10118행·제29조 10120·10126행)과 제정안(변환본 130~144·166~176·200~211행). 종전 제27조에 병가 미사용 가산 없음("병가를 사용하지" 0건)
- 〔추론〕으로 기록: 붙임 p.2의 "병가 미사용에 따른 다음 연도 연차휴가 추가 부여 대상에서 제외"(현재형)와 안내문 p.6의 "향후 … 추가 부여제도 시행 시"의 표현 차이 → 제정안 제27조 제4항 시행을 전제한 항목으로 봄. 누계 병가일수가 제29조 제3항(연간 6일 초과 공제)에 들어가는지와 진단서 예외 적용은 원본에 없음
- 파급 갱신 검토: 위키에서 "지각·조퇴·병가"를 다루는 페이지는 취업세칙 제정안 외에 없음(소송 현황 페이지의 일치는 무관한 낱말). 2022 단협 변환본(internal, ingest none)은 대조하지 않음
- 확인하지 못함: 노사합의서·시행 공문, 취업세칙 제정안의 시행 여부
- lint: wiki_lint.py. 새 오류 없음(broken_links 38·sources_bad 6·broken_sources 4는 기존 건과 같음)
- 색인: reindex.request 생성
- 커밋: 하지 않음(코워크와 같은 방식). 커밋 대상: 1 documents_md/법령_md/일반_md/지각·조퇴·외출 휴가 반영 기준 관련 세부내용.md, 0 wiki/문서/지각·조퇴·외출 휴가 반영 기준 관련 세부내용.md, 0 wiki/문서/안_「방송미디어통신심의위원회 사무처 취업세칙」 제정안.md, 0 wiki/문서/_index.md, 0 wiki/log.md, 3 source_raw/법령 등_raw/일반_raw/지각·조퇴·외출 휴가 반영 기준 관련 세부내용.pdf(사용자 추가 원본, .gitignore 대상이면 제외)
- 커밋 메시지 초안: wiki: 지각·조퇴·외출 휴가 반영 기준(2026.11.1. 시행) 변환·문서 페이지 작성, 취업세칙 제정안 제27조 제4항 연결

## [2026-11-03] fix | 수신함 파일 이동: 검토 메모 2건 @clippings → @Inbox, 스크랩.md @clippings → 1 documents_md/노션_md | Claude Opus 5.5
- 사용자 지시: "옵시디언 자료 중 반영 안 된 것 반영해줘". 이동은 Claude가 제안한 목록을 사용자가 선택지로 승인함(2026-11-03, "@Inbox로 옮겨 반영", "노션_md로 옮겨 검색 전용")
- 이동(2.2절, 내용 수정 없음, 목적지에 같은 이름 없음 확인):
  - 0 wiki/@clippings/방미통심위 심의를 거치지 않는 온라인 불법정보 삭제·차단 분야.md → 0 wiki/@Inbox/같은 이름 (기사가 아니라 챗지피티 검토 메모. 수신함 템플릿, status 대기)
  - 0 wiki/@clippings/보건복지부 자살예방정보 삭제 권한 관련.md → 0 wiki/@Inbox/같은 이름 (같은 이유)
  - 0 wiki/@clippings/스크랩.md → 1 documents_md/노션_md/스크랩.md (노션 내보내기 기사 스크랩 아카이브, 1.3MB·7,457줄. 위키 ingest 하지 않고 검색·인용만)
- 위키 sources 영향: 세 파일 경로를 적은 위키 페이지 없음(이동 전 grep 확인)
- 보안등급 영향: 스크랩.md는 news_clippings(public·원격 허용)에서 notion_notes(classification internal, ingest search_only) 범위로 옮겨짐. SOURCE_REGISTRY.yaml은 고치지 않음(폴더 단위 항목 범위)
- 참고: git에는 이전 이름 `0 wiki/@clippings/스크랩 60a981da1d104962bb341cff6c998e12.md`가 추적 중이며 작업 트리에서는 삭제(D) 상태임(사용자가 이름을 바꾼 것으로 보임)

## [2026-11-03] ingest | 기사 4건(5·18 '폭동' 항소심, KBS 홈쇼핑 연계편성, 방미통위 회피위원 정족수, 음성권 무단 녹음)과 수신함 메모 4건(의약품·건강기능식품, KBS 수신료 등록 면제, 심의 없는 삭제·차단 경로, 자살유발정보) | Claude Opus 5.5
- 사용자 지시: "지금 옵시디언 자료 중 반영 안 된 것 반영해줘"
- 미반영 판정: @clippings는 위키 sources·분석/기사 반영 기록에 경로가 없는 파일, @Inbox는 status 대기 파일
- 기사 반영(6.3, 기사별 문서 페이지 없음):
  - 5·18 '폭동' 항소심 무죄(연합뉴스 2026-10-16) → [[5·18민주화운동 허위사실정보(통신심의)]] 4절 관련 보도, 7절 항목
  - KBS 연계편성(미디어오늘 2026-10-10) → [[방송심의규정 제56조]] 3.2절 신설
  - 회피위원 정족수(연합뉴스 2026-09-23) → [[법제처 해석례 26-0621(2026.9.15.) 방미통위법 제13조제2항 의사정족수·의결정족수 산정]] 관련 보도
  - 음성권 무단 녹음(미디어오늘 idxno=211053, 게재일 미확인) → [[방송심의규정 제19조]] 3절 관련 보도, 7절 항목
  - [[기사 반영 기록]] 3~6절 누적
- 수신함 반영(status 대기 → 완료, 본문 수정 없음. 보안등급 public 2건, unknown 2건은 6.3에 따라 public으로 봄):
  - 의약품과 건강기능식품의 차이 → [[방송심의규정 제50조]] 2절 "현행 정의 대조"(약사법 제2조 제4호, 건강기능식품법 제3조 제1호·제2호). 해설집 표기 "약사법 제2조제2호"는 현행 약사(藥師) 정의임을 적음
  - KBS 수신료 면제 요건과 방미심위 해당 여부 → [[방송위원회·방통심의위의 국가기관성과 시정요구의 처분성]] 2-4절 신설
  - 방미통심위 심의를 거치지 않는 삭제·차단 분야, 보건복지부 자살예방정보 삭제 권한 → 새 쟁점 [[위원회 심의를 거치지 않는 정부기관의 삭제·차단 요청(통신심의)]] 생성(메모 related의 페이지 이름을 aliases에 넣음), [[자살유발정보(통신심의)]] 1절·5절·7절 갱신, [[지식재산권 침해정보(통신심의)]]·[[디지털성범죄정보(통신심의)]]·[[통신심의 절차와 소속 위원회]] 5절에 연결 1줄씩, 쟁점/_index 등재
- 원문 확인(법령·판례 MCP get_law_text·get_decision_text, 국가법령정보센터 웹 화면과의 동일성은 별도 확인하지 않음): 자살예방법 MST 279695 efYd 20261112(제2조의2·제19조의4·제19조의5, 법률 제21113호), 저작권법 MST 285693(제133조의2, 시행 2026.10.29.), 공직선거법 MST 285629(제82조의4), 성폭력처벌법 MST 289993(제23조의2), 산업표준화법 MST 289543 efYd 20270316(제21조의3), 약사법 MST 285341(제2조), 건강기능식품법 MST 285331(제3조), 대법원 2023두39724(판례일련번호 237561). 로컬 대조: 방송법 시행령 제36687호 변환본 949행(제39조 제19호), 정보통신망법 제21305호 변환본 597~598행(제44조의7 제3항), 현행 설치법 변환본 272행·428행
- 원문 미대조(메모 기재로 표시): 저작권법 제133조의3, 성폭력방지법 제7조의3·시행규칙 제2조의6, 전기통신사업법 제22조의5, 공중위생관리법 제4조의2, 약사법 제61조의2 제5항, 설치법 제3조 제2항·제27조 제4항, 기사 속 판결 원문(대구지법 2026.10.16., 뉴스타파 음성권 소송)
- 반영하지 않음: 메모·기사의 평가·논평(정치인 발언, 연구자 비판)은 성격을 밝힌 범위에서만 요약
- lint: wiki_lint.py. 새 broken_links·sources_bad·broken_sources 없음. broken_sources 4건은 기존 건(`‘노무현 조롱’ 계정, 결국 불법 아닌 ‘유해정보’로 차단 의결.md` 클리핑이 @clippings에 없음)
- 커밋: 하지 않음(코워크와 같은 방식). 커밋 대상: 0 wiki/쟁점/위원회 심의를 거치지 않는 정부기관의 삭제·차단 요청(통신심의).md, 0 wiki/쟁점/5·18민주화운동 허위사실정보(통신심의).md, 0 wiki/쟁점/자살유발정보(통신심의).md, 0 wiki/쟁점/지식재산권 침해정보(통신심의).md, 0 wiki/쟁점/디지털성범죄정보(통신심의).md, 0 wiki/쟁점/통신심의 절차와 소속 위원회.md, 0 wiki/쟁점/방송위원회·방통심의위의 국가기관성과 시정요구의 처분성.md, 0 wiki/쟁점/_index.md, 0 wiki/조문/방송심의규정 제19조.md, 0 wiki/조문/방송심의규정 제50조.md, 0 wiki/조문/방송심의규정 제56조.md, 0 wiki/문서/법제처 해석례 26-0621(2026.9.15.) 방미통위법 제13조제2항 의사정족수·의결정족수 산정.md, 0 wiki/분석/기사 반영 기록.md, 0 wiki/log.md
- 커밋 메시지 초안: wiki: 기사 4건·수신함 메모 4건 반영, 심의 없는 삭제·차단 요청 쟁점 신설, 수신함 파일 이동(메모 2건 @Inbox, 스크랩 노션_md)
- 색인: reindex.request 생성 → reindex_last.log [2026-11-03 11:05:30] exit=0

## [2026-11-03] fix | 누락 클리핑 복구: 미디어오늘 「‘노무현 조롱’ 계정, 결국 불법 아닌 ‘유해정보’로 차단 의결」 | Claude Opus 5.5
- 사용자 지시: "'노무현 조롱' 미디어오늘 기사를 Web Clipper로 다시 저장했어"(직전 세션에서 Claude가 끊긴 sources 4건 해소를 위해 재저장을 권함)
- 확인: 재저장 파일이 0 wiki/@Inbox/에 저장되어 있었음(2026-11-03 02:11). 파일명은 위키 sources 경로의 파일명과 바이트 단위로 같고, 머리말은 클리핑 형식(tags clippings, status 없음), source https://www.mediatoday.co.kr/news/articleView.html?idxno=337286&page=3&total=57, published 2026-09-22, created 2026-11-03(최초 클리핑 2026-09-25와 다름)
- 이동(2.2절, 내용 수정 없음, 목적지에 같은 이름 없음 확인): 0 wiki/@Inbox/‘노무현 조롱’ 계정, 결국 불법 아닌 ‘유해정보’로 차단 의결.md → 0 wiki/@clippings/같은 이름
- 내용 대조: [[기사 반영 기록]] 2.1절에 적은 미디어오늘 요지(2026.9.22. 통신소위, 11개 계정 접속차단, 2026.8.6. 의결보류, 불법정보 아닌 유해정보로 심의, 적용 조항 제8조 제2호 바목·제3호 바목·제4호 바목·제5호, 계정 전체 시정요구)와 재저장본이 일치함. 위키 내용은 고치지 않음
- lint: wiki_lint.py exit=0. broken_sources 4건 → 0건(유해정보(통신심의), 통신심의규정 제8조, 정보통신망법 제44조의7, 기사 반영 기록). 남은 sources_bad 2건은 기존 중복본 지정 건
- 커밋: 하지 않음. 커밋 대상: 0 wiki/@clippings/‘노무현 조롱’ 계정, 결국 불법 아닌 ‘유해정보’로 차단 의결.md, 0 wiki/log.md
- 커밋 메시지 초안: wiki: 누락 클리핑(미디어오늘 '노무현 조롱' 유해정보 차단 의결) 재저장분 복구

## [2026-11-04] query | 선거유형별 선거방송심의위원회 설치 기간 | Claude Opus 5.5
- 사용자 지시: 질의("선거유형별 선거방송심의위원회 구성 기간?") 답변 후 "위 내용 위키에 추가"
- 생성: [[2026-11-04 선거유형별 선거방송심의위원회 설치 기간]]
- 갱신: [[선거방송특별규정 제3조]] 4절에 "관련 분석" 링크만 추가(내용 변경 없음, status 유지), 분석/_index.md 등재
- 근거: 법령 MCP get_law_text로 공직선거법 현행 원문 조회(MST 285629, 2026.4.22. 공포, 제8조의2·제33조·제60조의2). 국가법령정보센터 웹 화면과의 동일성은 별도로 확인하지 않음. 로컬 변환본 「선거_공직선거법(법령단위비교 260602)」의 제8조의2·제60조의2 문언과 일치 확인. 규정집(2024) 「선거방송심의위원회의 구성 및 운영에 관한 규칙」 제3조. 선방위 회의록 분할본 part02·03·05·06·10의 운영기간 보고(제6·7·8회 지방선거, 제20대 총선, 제19대 대선)
- 계산: 선거일 기준 설치 시작·종료일은 Python datetime으로 산출. 제6·7·8회 지방선거와 제20대 총선은 회의록 운영기간과 일치
- 미확인: 2025.10.1. 설치법 개정 이후 선방위 구성·운영 규칙의 새 제정 여부. 제19대 대선(궐위선거) 운영기간 시작일 3.20.이 법문 계산값(3.10.)과 다른 이유
- 커밋: 하지 않음(코워크와 같은 방식). 커밋 대상: 0 wiki/분석/2026-11-04 선거유형별 선거방송심의위원회 설치 기간.md, 0 wiki/분석/_index.md, 0 wiki/조문/선거방송특별규정 제3조.md, 0 wiki/log.md
- 커밋 메시지 초안: wiki: 선거유형별 선거방송심의위원회 설치 기간 분석 페이지 추가

## [2026-11-04] schema | AGENTS.md v1.30 → v1.31: 6.3절 수신함 행에 대조 확인한 부분의 근거 사용 명시 | Claude Opus 5.5
- 6.3절 표 수신함 행의 "수신함 메모는 1.1의 ④에 준하는 미검증 자료로 취급하여 결론의 단독 근거로 쓰지 않는다." 뒤에 추가: "다만 ingest할 때 메모 내용을 공식 원문 또는 ①·② 자료와 대조해 확인한 부분은, 그 확인한 자료를 `sources`에 함께 적고 결론의 근거로 쓸 수 있다. 이 경우에도 메모는 확인 대상을 찾은 경로로만 기록한다(v1.31, 사용자 승인 2026-11-04)." 머리말 개정일·판 번호 갱신
- 등급 ②(규칙 명확화. 메모 자체의 지위는 바꾸지 않음). 승인: 2026-11-04 사용자가 대화에서 제안한 문안을 가리켜 "니 제안대로 AGENTS.md에 수정 반영해줘". 배경 질문: 검증된 정보를 @Inbox에 넣은 경우에도 나중에 ingest하면 결론의 단독 근거로 쓸 수 있는지
- 제안 문안 그대로 반영함. 같은 대화에서 설명한 "메모의 source·본문 근거는 대조 단서, 다시 확인할 수 없는 근거만 있으면 메모 근거임을 밝힘" 부분은 제안 문안에 없어 반영하지 않음(반영 중 넣었다가 승인 범위를 넘어 되돌림)
- 기존 위키 페이지 영향: 없음
- 백업: Claude outputs/schema_backup/AGENTS_v1.30_20261104.md
- 커밋: 하지 않음(코워크와 같은 방식). 커밋 대상: AGENTS.md, Claude outputs/schema_backup/AGENTS_v1.30_20261104.md, 0 wiki/log.md
- 커밋 메시지 초안: schema: AGENTS v1.31 6.3절 수신함 메모 대조 확인 부분의 근거 사용 명시

## [2026-11-04] schema | AGENTS.md v1.31 → v1.32: 6.3절 수신함 행에 메모 근거의 처리 방법 추가 | Claude Opus 5.5
- 6.3절 표 수신함 행의 v1.31 추가 문장 뒤에 추가: "메모 머리말의 `source`나 본문에 적힌 근거(조문 번호, 문서번호, 의결번호, URL 등)는 대조할 대상을 찾는 단서로 쓰고, 다시 확인할 수 없는 근거(구두 답변 등)만 있는 내용은 메모에 근거함을 밝혀 반영한다(v1.32, 사용자 승인 2026-11-04)." 머리말 판 번호 갱신
- 등급 ②. 승인: 2026-11-04 사용자가 v1.31 보고의 "반영하지 않은 부분"을 가리켜 "반영하지 않은 부분도 추가 반영해줘". 사용자 발언: 메모에 넣는 내용 중 근거와 소스가 명확한 내용은 사용자가 따로 적어 두기로 함
- 기존 위키 페이지 영향: 없음
- 백업: Claude outputs/schema_backup/AGENTS_v1.31_20261104.md
- 커밋: 하지 않음(코워크와 같은 방식). 커밋 대상: AGENTS.md, Claude outputs/schema_backup/AGENTS_v1.31_20261104.md, 0 wiki/log.md
- 커밋 메시지 초안: schema: AGENTS v1.32 6.3절 수신함 메모 근거의 처리 방법 추가

## [2026-11-05] query | 화면에 노출된 메모지(연락처·업체 인증정보)의 적용 조항 | Claude Opus 5.5
- 사용자 지시: 식당 POS 화면 스케치 영상에 비밀번호·휴대전화번호가 적힌 포스트잇이 노출된 사안의 적용 조항 질의와 후속 질의(개인사업자 정보, 개인정보 보호법 제58조, 제19조·제39조 동시 적용 여부, 2015고정1144 설명) 뒤 "위 내용서 조사/정리한 내용 위키에 반영해줘"
- 생성: [[2026-11-05 방송 화면에 노출된 메모지(연락처·업체 인증정보)의 적용 조항]]
- 갱신: [[방송심의규정 제19조]] 3절에 "화면 속 연락처·인증정보·업체 정보 노출" 소절 추가, 관련 조문에 제20조·제39조 추가, sources 추가 / [[방송심의규정 제39조]] 3절에 "제19조(사생활 보호)와의 관계" 소절 추가, 관련 조문에 제19조 추가, sources 추가 / [[방송심의규정 제20조]] 3절에 신설 배경 후보(2020-방송-14-0147)와 인증정보 비대상 〔추론〕 추가, 추가 확인 필요 1항목 추가 / 분석/_index.md 등재. 세 조문 페이지 모두 draft였으므로 status 변경 없음
- 근거: 통계 CSV(보정본·분할본·△26.01.-09.csv 2026.07~09 행), 방송심의소위원회 회의록(2018 part1of3 제18차, 2020 part1of2 제15차, 2015 part2of2 제28차), 방송소위 회의결과 2022 정제본, 방송심의사례집(병합 2010-2024). 법령 MCP로 개인정보 보호법 현행 원문(MST 283839, 2026.9.11. 시행) 제2조·제58조·제59조·제71조·제73조·제75조와 판례 2건(서울서부지법 2015고정1144, 대법원 2017도15226) 조회. 국가법령정보센터 웹 화면과의 동일성은 별도로 확인하지 않음. 개인정보보호위원회 해설서의 개인사업자 정보 해석은 기고·보도 2차 인용(〔외부 자료〕)
- 계산: 제19조·제33조(법령의 준수) 동시 적용 행 수. stats_articles.py(v1.3) --verify 모두 일치 확인 뒤, 그 load·bangsim_articles 함수를 불러 쓴 일회성 코드로 12,722행 조회(동시 적용 0행, 제19조 208행·법령의 준수 154행은 조문 페이지 통계와 일치). 일회성 코드는 저장하지 않음
- 제외: 질의 답변의 위반 가능성 등급 등 검토 의견
- 〔충돌〕 표시: 2022-방송-43-0394의 방송일·적용 항(회의결과 정제본 2022.10.11.·제1항 / 통계 CSV 2020.9.9.·제3항)
- lint: wiki_lint.py exit=0. 새 페이지의 broken_links·broken_sources 없음
- 커밋: 하지 않음(코워크와 같은 방식). 커밋 대상: 0 wiki/분석/2026-11-05 방송 화면에 노출된 메모지(연락처·업체 인증정보)의 적용 조항.md, 0 wiki/분석/_index.md, 0 wiki/조문/방송심의규정 제19조.md, 0 wiki/조문/방송심의규정 제39조.md, 0 wiki/조문/방송심의규정 제20조.md, 0 wiki/log.md
- 커밋 메시지 초안: wiki: 화면 속 메모지(연락처·업체 인증정보) 노출의 적용 조항 분석 추가, 제19·20·39조 페이지 보완

## [2026-11-10] schema | 2026년 방송심의 통계를 고정 파일명 잠정본으로 전환(△26.01-10), AGENTS.md v1.32 → v1.33(통계기준 7.1), SOURCE_REGISTRY.yaml v1.48 → v1.49 | Claude Opus 5.5
- 사용자 지시 2026-11-10: "위키 data 폴더에 통계 업데이트분(△26.01.-10) 해서 추가했어. △26.01.-09이랑 제미나이 노트북용 분할 폴더 안에 있는 26.01-06는 불필요해 보이는데 삭제 가능하면 삭제해줘". 처리 방식은 사용자 선택 "기준본 전환 후 삭제", 월별 갱신 방식(고정 파일명·의결번호 인용·연 1회 집계 갱신)과 반영안 ①~⑤는 사용자 승인 "전부 승인"(②등급)
- 새 파일 대조: `쳇지피팅용 병합_csv/△26.01-10.csv` 422행(19열, 기존 14열 뒤에 조항·원처분·재심/판결일·참고·제척기피회피 추가), 의결일 2026-04-20~10-27. 월별 04 30·05 49·06 135·07 46·08 73·09 43·10 46. △26.01.-09(376행)의 의결번호·내용·순번은 모두 같고 10월 46행만 추가. 26.01-06(214행)은 모두 같은 의결번호로 있고 내용이 다른 2행(2026-방송-12-0053 관련조항, 2026-09-0041 의결 내용)은 2026-10-13 기록과 같은 정정
- 파일: `제미나이 노트북용 분할_csv/2026_잠정.csv`(△26.01-10.csv 복사본) 생성. `쳇지피팅용 병합_csv/△26.01.-09.csv`, `제미나이 노트북용 분할_csv/26.01-06.csv` 삭제(사용자 지시). △26.01-10.csv 원본은 사용자 투입본으로 그대로 둠
- SOURCE_REGISTRY.yaml v1.49: stats.period(2012.01~2025.12, 2026년은 stats_2026_recent), stats_2026_recent의 path(분할_csv/2026_잠정.csv)·period(2026.01~10 잠정, 기준일 2026-10-27, 422행)·period_use(2026.01~)·notes(매월 덮어쓰기·파일명 고정·확정본 교체), stats_merged.notes(△ 파일은 사용자 투입본). 보안 필드는 바꾸지 않음
- AGENTS_통계기준.md(7.1 대상 자료): "2026.07 이후 행은 stats_2026_recent의 해당 월 행만 추가" → "2026년 행은 stats_2026_recent(잠정본)를 쓰고 기준일을 적는다. 잠정본이 교체되어도 기존 집계는 다시 계산하지 않고, 재집계는 사용자 요청 시와 확정본 반영 시에만 한다"
- 백업: Claude outputs/schema_backup/AGENTS_v1.32_20261110.md, AGENTS_통계기준_v1.32_20261110.md, SOURCE_REGISTRY_v1.48_20261110.yaml
- 위키 78쪽(조문 75, 분석 2, 문서 1): 대상 자료 문구의 `쳇지피팅용 병합_csv/△26.01.-09.csv`(73건)와 `△26.01.-09.csv`(3건)를 "stats_2026_recent(2026 잠정본, 2026-09-29 기준판)"으로, sources 경로 6건을 `제미나이 노트북용 분할_csv/2026_잠정.csv`로 교체. 수치는 바꾸지 않음(새 파일의 2026.07~09 행은 같은 162행이라 기존 집계가 그대로 재현됨)
- 행 출처 6건 `26.01-06.csv 순번 N` → `2026_잠정.csv 순번 M`(광고심의규정 제5·15·21·26·28·55조). 대응표 Claude outputs/stats_seqmap_2026-11-10.json, 각 페이지의 의결일·의결번호와 일치 확인
- 이력: 이 파일의 이전 기록에 있는 △26.01.-09·26.01-06 표기는 당시 파일 기준이며 고치지 않음
- 미완료(클로드 코드 인계): stats_articles.py는 분할 폴더 csv를 모두 읽으므로 2026_잠정.csv가 기본 집계에 들어가고 --recent는 옛 경로를 가리킴. 수정 전까지 통계 스크립트 실행 금지. refine_subcommittee_results.py 보조 CSV 경로도 교체 필요. 월별 갱신 검증 스크립트 신설
- lint: wiki_lint.py exit=0. broken_sources 0, broken_links 38·sources_bad 2·yaml_error 1은 기존 건
- 커밋: 하지 않음(코워크). 커밋 대상: AGENTS.md, AGENTS_통계기준.md, SOURCE_REGISTRY.yaml, 위 백업 3개, Claude outputs/stats_seqmap_2026-11-10.json, 0 wiki 78쪽, 0 wiki/log.md
- 커밋 메시지 초안: schema: AGENTS v1.33·registry v1.49 2026 통계 잠정본(2026_잠정.csv) 고정 파일명 전환, 위키 출처 표기 교체

## [2026-11-10] fix | 통계 스크립트를 2026_잠정.csv 기준으로 정비, 월별 갱신 스크립트 신설 | Claude Sonnet 5.5
- stats_articles.py v1.3 → v1.4: load()가 2026_잠정.csv를 따로 처리(기본은 의결일 2026-06-30 이하, `--recent`는 07-01 이후 추가, `--until YYYY-MM-DD` 신설, 기본 잠정본 전체). RECENT 상수를 분할_csv/2026_잠정.csv로 교체. 인계메모는 v1.2 → v1.3으로 적었으나 실제 파일은 이미 v1.3(보정본, 2026-10-21)이어서 v1.4로 올림
- `--until` 전달: ad_articles.py v1.4, hyup_articles.py v1.2, section_stats.py v1.2, count_article_item.py v1.2, sanction_results.py v1.2. refine_subcommittee_results.py는 34행 보조 CSV 경로만 2026_잠정.csv로 교체(재실행 안 함)
- 검증: `--verify` 12,560행 모두 일치, `--recent --until 2026-09-30` 12,722행(제46조 1,361·제44조 761·제27조 782·제14조 1,138·제9조 339 기존 확장 검증값과 같음), `--recent` 12,768행
- 광고 검증값: 보정본(v1.30) 기준 `--until 2026-09-30`에서 조 식별 3,317행·제18조 1,540행. 2026-10-13에 적은 3,315·1,538은 보정본 적용 전(분할본 12-17_part, load(split=True)) 값이며 split=True로 재현됨(3,315·1,538). 기준 12,560행은 3,277·1,514(AGENTS_통계기준.md와 같음). 위키의 기존 수치는 바꾸지 않음
- 신설 update_stats_2026.py v1.0: 기본 dry-run, `--apply`는 잠정본 덮어쓰기 → registry stats_2026_recent period·notes 갱신(백업·version+0.01) → log.md → reindex.request. 현재 △26.01-10.csv로 dry-run: "누락 0, 추가 0, 변경 0". --apply는 임시 복사본으로 registry·log 갱신 부분만 시험함(실제 파일에는 적용 안 함)
- lint: wiki_lint.py exit=0, broken_sources 0, broken_links 38·sources_bad 2·yaml_error 1은 기존 건
- 커밋: 작업 1~3(스크립트)과 2026-11-10 schema 항목 대상을 분리해 커밋(push 안 함)

## [2026-11-10] schema | AGENTS.md v1.33 → v1.34(2.1절 ①등급에 stats_2026_recent 월별 period·notes 갱신 추가) | Claude Sonnet 5.5
- 등급: ③(2.1절 자체의 변경). 승인 2026-11-10: 제안 문안을 가리켜 "승인 후 반영"
- 변경: 2.1절 표 ①행 끝에 "`stats_2026_recent`의 `period`·`notes` 이력만 바꾸는 월별 갱신(update_stats_2026.py --apply, path·보안 필드 불변)" 추가. 다른 규칙은 바꾸지 않음
- 백업: Claude outputs/schema_backup/AGENTS_v1.33_20261110.md
- 커밋 대상: AGENTS.md, 위 백업, 0 wiki/log.md

## [2026-11-11] schema | log.md 월별 분할: AGENTS.md v1.34 → v1.35(3절 트리·10절·부록), CLAUDE.md log 규칙 2곳, build_index.py·wiki_lint.py v1.4 정비, split_log.py 신설 | Claude Sonnet 5.5
- 등급 ②(규칙 변경, 승인 범위 A~E). 승인: 2026-11-11 사용자가 제안서(작업 3 log 분할안)를 가리켜 "A~E 승인"
- 분할: 0 wiki/log.md(576,642바이트, 295개) → log/2026-09.md(380,398바이트, 203개), log/2026-10.md(169,797바이트, 81개), 새 log.md(26,447바이트, 2026-11 항목 11개 + 이 항목). 항목 내용은 바이트 그대로 옮겼고, 원본 == 머리말 + 조각 2개 + 새 log.md 본문이 바이트 단위로 일치함(split_log.py 적용 전후 검증)
- AGENTS.md: 3절 폴더 트리에 log/YYYY-MM.md 추가, 10절에 "끝 50줄만 확인·월 바뀔 때 지난 달 이전" 규칙, 부록 개정 이력 위치 표기. 판 번호·개정일 갱신. CLAUDE.md: log 쓰기 규칙(끝 50줄 확인), 코워크 항목 탐색 범위에 직전 달 log/ 포함
- 스크립트: J:\MCP\ai-vault-mcp\build_index.py(WIKI_LOG_DIR 추가, 0 wiki/log/ 색인 제외), Claude outputs/wiki_lint.py v1.4(log/ 조각은 머리말·stray 점검에서 제외, 링크 스캔에는 포함해 고립 판정 유지), Claude outputs/split_log.py v1.0 신설(점검 전용 기본, --apply로 적용, 매월 롤오버에 사용)
- 검증: wiki_lint.py 분할 전후 결과 동일(orphans 0, broken_links 38 같은 항목, broken_sources 0. yaml_error·stray 1건은 사용자의 웹클리퍼 템플릿 파일로 기존 건)
- 백업: Claude outputs/schema_backup/AGENTS_v1.34_20261111.md, CLAUDE_20261111.md. log.md 원본·스크립트 원본은 세션 작업 공간에만 보관(저장소에 넣지 않음)
- 기존 항목의 내용은 고치지 않음. 머리말 안내문의 "AGENTS.md 9절"은 이번에 고치지 않음
- 커밋 메시지 초안: schema: AGENTS v1.35 log.md 월별 분할(log/YYYY-MM.md), 색인·lint 제외 반영, split_log.py 신설

## [2026-11-11] schema | AGENTS.md v1.35 → v1.36: 0절 1항에 AGENTS_절차.md·AGENTS_원격.md를 AGENTS.md의 일부로 명시(③-1만 반영) | Claude Sonnet 5.5
- 등급 ③(0절 변경, 항목별 승인). 승인: 2026-11-11 사용자가 경량화안(작업 2)의 ③-1을 가리켜 "③-1 승인". ③-2(0절 3항 원격 규칙 이동)·③-3(2.1절 이동)과 ②등급 묶음은 승인 전이라 반영하지 않음
- 0절 1항 문구 확장: `AGENTS.md(7.1절 본문인 AGENTS_통계기준.md 포함)` → `AGENTS.md(7.1절 본문인 AGENTS_통계기준.md, 절차 본문인 AGENTS_절차.md, 부록 AGENTS_원격.md 포함)`. 두 파일은 아직 만들지 않았고(후속 ②등급 반영 예정), 지금은 이름만 선언된 상태
- 판 번호·개정일 갱신(v1.36). 기존 위키 페이지 영향 없음
- 백업: Claude outputs/schema_backup/AGENTS_v1.35_20261111.md
- 커밋 메시지 초안: schema: AGENTS v1.36 0절 1항에 AGENTS_절차.md·AGENTS_원격.md 명시(③-1)

## [2026-11-11] schema | AGENTS.md v1.36: 0절 3항(원격 규칙)을 AGENTS_원격.md로, 2.1절 본문을 AGENTS_절차.md로 이동(③-2, ③-3) | Claude Sonnet 5.5
- 등급 ③(항목별 승인). 승인: 2026-11-11 사용자가 경량화안(작업 2)의 ③-2와 ③-3을 가리켜 "③-2 승인, ③-3 승인". ②등급 묶음(2·3·4·5·6·9·10절 이동, 대응표, CLAUDE.md 수정 등)은 승인 전이라 반영하지 않음
- ③-2: 0절 3항 원문(remote_allowed: false 자료의 원격 제공 금지, AIVAULT_REMOTE_EXTRA_IDS 예외는 개별 승인)을 새 파일 AGENTS_원격.md에 그대로 옮기고, 0절 3항에는 "원격 규칙은 AGENTS_원격.md에 있으며 현재 원격 경로는 연결하지 않는다, 연결하게 되면 그 파일을 따른다"만 남김. 내용은 바꾸지 않았고 위치만 옮김
- ③-3: 2.1절 본문(등급표, ①등급 조건, 승인 요건, 반영 6단계, 되돌리기)을 새 파일 AGENTS_절차.md 2.1절로 그대로 옮기고, AGENTS.md에는 요지 4줄만 남김. 2.1절 뒤쪽의 쓰기 범위 단락은 AGENTS.md에 그대로 둠
- 검증: 이동 전 AGENTS.md(v1.36) 비어 있지 않은 397줄 중 새 파일 3개에 그대로 없는 줄 0. AGENTS.md 26,534 → 24,656자
- 현재 상태: AGENTS_절차.md에는 2.1절만 있고 대응표는 아직 없음(②등급 반영 때 추가). AGENTS_원격.md에는 0절 3항만 있고 2.1절 표의 ChatGPT 행은 AGENTS.md에 남아 있음
- 백업: Claude outputs/schema_backup/AGENTS_v1.36_20261111.md
- 커밋 메시지 초안: schema: AGENTS v1.36 0절 3항 원격 규칙을 AGENTS_원격.md로, 2.1절 본문을 AGENTS_절차.md로 이동(③-2·③-3)

## [2026-11-11] schema | AGENTS.md v1.36 경량화 완료(②등급): 2.2·2.3·3.1~3.4·4·5·6.2~6.7·9·10절을 AGENTS_절차.md로 이동, 대응표 신설, CLAUDE.md 첫머리 수정 | Claude Sonnet 5.5
- 등급 ②. 승인: 2026-11-11 사용자가 경량화안(작업 2)의 ②등급 묶음을 가리켜 "②등급 묶음 승인". ③-1·③-2·③-3은 앞선 두 항목에서 반영함
- 이동: 2.2, 2.3, 3.1~3.4, 4.1~4.3, 5, 6.2~6.7, 9, 10절 전문을 AGENTS_절차.md로(절 번호 유지, 내용 변경 없음). AGENTS.md에는 3절 끝 안내 1줄, 4절·9절 요지, 6절 안내 1줄, "작업별 읽을 문서" 대응표를 둠. 2절 권한 표의 스키마 파일 행에 AGENTS_절차.md·AGENTS_원격.md 추가, 구성요소 표의 ChatGPT 행은 원문 그대로 AGENTS_원격.md로 이동
- CLAUDE.md: 첫머리의 "AGENTS.md와 SOURCE_REGISTRY.yaml을 반드시 읽고" 지시를 삭제하고 "AGENTS.md 자동 로드, 대응표의 절은 작업 전에 읽는다, REGISTRY는 관련 id·path와 defaults만 검색해 읽는다"로 바꿈. 나머지 규칙은 그대로
- 검증: 이동 전 AGENTS.md 비어 있지 않은 376줄 중 새 파일 3개(AGENTS.md, AGENTS_절차.md, AGENTS_원격.md)에 그대로 없는 줄은 1줄(의도한 변경: 2절 표의 스키마 파일 행). 누락 0
- 분량: 상시 로드 AGENTS.md 8,825자 + CLAUDE.md 2,845자 = 11,670자(이전 29,279자). AGENTS_절차.md 19,818자. wiki_lint.py exit=0
- 기존 위키 페이지가 인용한 "AGENTS.md ○절"은 대응표로 찾음(페이지 수정 없음). 위키 변경이 아니어서 색인 요청은 하지 않음
- 백업: Claude outputs/schema_backup/AGENTS_v1.36_20261111_2.md, CLAUDE_20261111_2.md
- 미반영(후속 후보): SOURCE_REGISTRY.yaml의 notes·중복본·remote_allowed 정리는 이번 범위 밖
- 커밋 메시지 초안: schema: AGENTS v1.36 경량화(작업별 절차를 AGENTS_절차.md로 분리, 대응표, CLAUDE.md 정리)

## [2026-11-11] fix | Claude outputs의 옛 사본 정리: build_index.py·mcp_server.py·README 사본·stats_seqmap json 삭제, 동일 사본 4건 삭제, README.md 안내문으로 교체 | Claude Sonnet 5.5
- 승인: 2026-11-11 사용자가 작업 4 처분안을 가리켜 "A+B 승인"(AGENTS.md 2.1절 삭제는 사용자 확인 후)
- 삭제(A): Claude outputs/build_index.py(50,012바이트, 실제 52,819), mcp_server.py(26,087, 실제 28,380), ai-vault-mcp_README.md, stats_seqmap_2026-11-10.json(43KB, 읽는 스크립트 없음). README.md는 옛 README 사본(위 파일과 동일 내용)이라 안내문으로 교체
- 삭제(B): search.py, check_index.py, check_md_quality.py, convert_haesul.py(J:\MCP\ai-vault-mcp의 파일과 바이트 단위로 동일한 사본. 삭제 전 cmp로 확인). 실제 버전은 모두 J:\MCP\ai-vault-mcp에 있음
- 사전 확인: 위키 페이지·SOURCE_REGISTRY.yaml이 이 파일들을 경로로 참조하지 않음(log.md 이력과 2026-09-23 lint 보고의 말 언급뿐). refine_subcommittee_results.py는 이미 J:\MCP 경로를 지정해 영향 없음. 사본 build_index.py를 import하던 search.py·check_md_quality.py는 함께 삭제(B)
- 새 README.md: 실제 버전 위치, wiki_lint.py v1.4·split_log.py 등 이 폴더 주요 스크립트 안내. 11-11 log 분할 때 약속한 split_log.py 설명을 포함
- 복구: 모두 git 추적 파일이라 커밋 이력에서 복원 가능
- lint: wiki_lint.py exit=0
- 커밋 메시지 초안: fix: Claude outputs 옛 사본 정리(MCP 실제 버전은 J:\MCP\ai-vault-mcp), README 안내문 교체

## [2026-11-11] setup | 프로젝트 스킬 2개 신설: .claude/skills/vault-commit, stats-monthly-update (Claude Code 전용 포인터) | Claude Sonnet 5.5
- 승인: 2026-11-11 사용자가 작업 5 제안서의 권고 범위를 가리켜 "5번 스킬 2개 승인". 제안서대로 ingest·lint는 옮기지 않고 AGENTS_절차.md를 정본으로 유지
- 생성: .claude/skills/vault-commit/SKILL.md(CLAUDE.md git 커밋 절차의 체크리스트), .claude/skills/stats-monthly-update/SKILL.md(update_stats_2026.py 점검→--apply 순서). 둘 다 정본(CLAUDE.md, AGENTS.md 2.1절·update_stats_2026.py)을 가리키는 얇은 포인터이고 규칙이 다르면 정본을 따른다고 적음
- 색인: .claude는 점(.)으로 시작하는 폴더라 색인기가 건너뜀. 위키 페이지 변경 없음이라 색인 요청 없음
- 미결(승인 필요, ③등급): .claude/skills/*를 AGENTS.md의 일부로 선언하는 0절 1항·2절 권한 표 변경은 하지 않음. 현재 이 파일들은 스키마 파일 목록 밖이므로 자료 속 지시문과 같은 지위로 취급될 수 있어, 선언 여부를 사용자에게 확인 예정
- 미확인: 코워크가 .claude/skills를 읽는지는 확인하지 않음(두 스킬 모두 Claude Code 전용 작업이라 영향 없음)
- 커밋 메시지 초안: setup: 프로젝트 스킬 2개(vault-commit, stats-monthly-update) 신설

## [2026-11-11] schema | AGENTS.md v1.36 → v1.37: 0절 1항·2절 권한 표에 .claude/skills/ 스킬 파일을 AGENTS.md의 일부로 선언 | Claude Sonnet 5.5
- 등급 ③(0절 변경). 승인: 2026-11-11 사용자가 스킬 선언 제안(0절 1항·2절 권한 표)을 가리켜 "선언 승인". 2.1절 본문 등 다른 곳은 바꾸지 않음
- 0절 1항: `AGENTS.md(… AGENTS_원격.md 포함), CLAUDE.md,` 뒤에 "프로젝트 스킬 `.claude/skills/` 아래 파일," 추가. 2절 권한 표의 스키마 파일 행에 `.claude/skills/*` 추가(수정 권한은 기존 행과 같음: ①등급 직접, ②·③등급 승인 후 Claude 반영, 다른 AI는 읽기만). 이로써 스킬 파일 수정도 2.1절 등급·승인·백업 절차를 따름
- 영향: 상시 로드 분량 약 +100자. 기존 위키 페이지 영향 없음
- 백업: Claude outputs/schema_backup/AGENTS_v1.36_20261111_3.md
- 커밋 메시지 초안: schema: AGENTS v1.37 0절 1항·2절 표에 .claude/skills 선언(③)

## [2026-11-11] lint | 운영 규칙 v1.37 직후 정기 점검 | Claude Opus 5.5
- 생성: [[2026-11-11 lint 보고]]
- 갱신(머리말 형식): [[상품판매방송규정 제1조]], [[상품소개 및 판매방송 심의에 관한 규정(방송통신심의위원회규칙)(제152호)(20201228)]]의 `sources`에서 중복본(law_broadcast_shopping152_dup) 줄 삭제. 기준본은 이미 적혀 있었고 본문·updated는 그대로
- 갱신: 분석/_index.md 등재
- 근거: script: Claude outputs/wiki_lint.py v1.4(exit=0, sources_bad 2 → 0), 법령 MCP(search_law·get_law_text 부칙·compare_old_new, 정보통신망법 MST 290001, 조회일 2026-11-11). 국가법령정보센터 웹 화면과의 동일성은 별도로 확인하지 않음
- 주요 발견: 위원회 규칙 제8~12호 국가법령정보센터 등재(열린 항목 238개 처리 가능), 정보통신망법 제21988호(2026.10.2. 시행)·제21500호(2026.10.1. 시행) 미반영(조문 40개, 제44조의7 제4항 제1호 문언 변경), 방송법 제22111호(2027.4.21. 시행 예정) 미기재, 〔충돌〕 원인별 분류, 통신 통계 집계값 쟁점 12개 internal 표시 여부 미결. 제안 10건은 보고서 12절(사용자 확인 전)
- 정정: 같은 날 대화에서 열린 항목을 1,366개로 말했으나, wiki_lint.py 기준 1,007개(389개 페이지)가 맞다(앞의 수치는 임시 스크립트의 목록 판정 차이)
- 세션: 채팅(코워크와 같은 원격 셸, 삭제 제한)이므로 커밋하지 않음
- 커밋 대상 파일: 0 wiki/분석/2026-11-11 lint 보고.md, 0 wiki/분석/_index.md, 0 wiki/조문/상품판매방송규정 제1조.md, 0 wiki/문서/상품소개 및 판매방송 심의에 관한 규정(방송통신심의위원회규칙)(제152호)(20201228).md, 0 wiki/log.md
- 커밋 메시지 초안: lint: 2026-11-11 정기 점검 보고, 중복본 출처 2건 정리

## [2026-11-11] fix | 정보통신망법 조문 40개를 법률 제21988호(2026.10.2. 시행) 기준으로 갱신(lint 제안 ②) | Claude Opus 5.5
- 승인: 2026-11-11 사용자가 [[2026-11-11 lint 보고]] 제안 처리 순서(② → ① → ⑥)를 가리켜 "니가 제안한대로 진행"
- 근거: 법령 MCP compare_old_new(MST 290001: 제21988호 대비, MST 285199: 제21500호 대비. 제21500호 결과는 30개 조문 단위까지만 표시되었으나 조 번호 순서이고 제45조부터 시작), get_law_text(MST 290001, 제44조의7·제53조·제58조·제58조의2·제61조·제70조·제72조·제73조·제74조·제76조). 국가법령정보센터 웹 화면과의 동일성은 별도로 확인하지 않음. verified_at은 2026-09-26 갱신 때와 같은 방식(법령 MCP 조회 결과를 원문 대조로 봄)
- 내용 변경: [[정보통신망법 제44조의7]](제4항 제1호 공소청의 장 추가), [[정보통신망법 제73조]](제6호 삭제), [[정보통신망법 제76조]](제1항 신설, 항 번호 하나씩 밀림)
- 머리말·제목·열린 항목만 갱신: 정보통신망법 조문 37개(제2조, 제41조~제44조의26 중 제44조의7 제외, 제53조, 제58조, 제58조의2, 제61조, 제70조, 제72조, 제74조)
- 교차참조 갱신: 제76조 항 번호 22곳(조문 제42조의3·제43조·제44조의6·제44조의7·제44조의9·제44조의14·제53조·제58조·제58조의2, 쟁점 [[권리침해정보(통신심의)]]·[[디지털성범죄정보(통신심의)]]·[[광고성 정보 전송·게시(통신심의)]]), 제44조의7 공소청 추가 반영 2곳(조문 제44조의9, 쟁점 디지털성범죄정보)
- 검증: wiki_lint.py exit=0, 깨진 링크(콘텐츠 페이지) 0, 열린 항목 1,007 → 969
- 갱신: [[2026-11-11 lint 보고]] 13절(후속 처리)
- 세션: 채팅(원격 셸, 삭제 제한)이므로 커밋하지 않음
- 커밋 대상 파일: 0 wiki/조문/정보통신망법 *.md(40개 전부), 0 wiki/쟁점/광고성 정보 전송·게시(통신심의).md, 0 wiki/쟁점/권리침해정보(통신심의).md, 0 wiki/쟁점/디지털성범죄정보(통신심의).md, 0 wiki/분석/2026-11-11 lint 보고.md, 0 wiki/log.md
- 커밋 메시지 초안: fix: 정보통신망법 조문 40개 법률 제21988호 기준 갱신(제44조의7·제73조·제76조 개정 반영, 제76조 항 번호 교차참조 정리)

## [2026-11-11] schema | AGENTS.md v1.37 → v1.38: 8절에 internal 자료 집계값의 예외 단서 추가 | Claude Opus 5.5
- 등급 ②. 승인: 2026-11-11 사용자가 [[2026-11-11 lint 보고]] 제안 ⑥의 선택지 중 "집계값은 예외로 규칙 명시"(단서 문안 미리보기 포함)를 선택
- 변경: 8절 마지막 항목 뒤에 "다만 internal 자료에서 개인정보·게시물 주소·신청자 정보 등 internal로 지정한 사유에 해당하는 내용을 빼고 집계한 수치(연도별 건수, 비율 등)만 옮긴 위키 페이지에는 `classification: internal`을 적지 않는다" 1줄 추가. 판 번호 갱신. 그 밖의 문장은 바꾸지 않음(diff 2곳)
- 영향: 통계 CSV(stats_telecom) 집계값만 옮긴 통신심의 쟁점 12개는 public 유지(머리말 변경 없음). wiki_lint.py internal_suspect 판정은 미반영(후속: Claude Code)
- 백업: Claude outputs/schema_backup/AGENTS_v1.37_20261111.md
- 갱신: [[2026-11-11 lint 보고]] 13절
- 커밋 대상 파일: AGENTS.md, Claude outputs/schema_backup/AGENTS_v1.37_20261111.md, 0 wiki/분석/2026-11-11 lint 보고.md, 0 wiki/log.md
- 커밋 메시지 초안: schema: AGENTS v1.38 8절 internal 자료 집계값 예외 단서(②)

## [2026-11-11] fix | 위원회 규칙 제8~12호 국가법령정보센터 등재본 대조(lint 제안 ①): 조문 페이지 238개 중 237개 일치 반영, 1개 불일치 보고, registry v1.50 | Claude Sonnet 5.5
- 세션: Claude Code. 사용자 지시: 인계메모 작업 2(원문은 법령 MCP 조회 가능 확인 뒤 사용자가 내려받는 방식 선택, "내려받기 방식으로 진행하자")
- 원본: 사용자가 2026-11-11 내려받은 PDF 5개 — 3 source_raw/법령 등_raw/방송_raw/심의규정(법제처 다운)/ 4개(제8·10·11·9호)와 통신_raw/ 1개(제12호). 파일명 끝 "(제N호)(20260929).pdf"
- 변환(6.7): 1 documents_md/법령_md/방송_md/·통신_md/에 같은 이름 .md 5개 추가(pdftotext 기본 모드, 쪽마다 p.N 주석, 기존 공표본 변환본과 이름이 달라 덮어쓰기 없음). 점검: 쪽 22/16/15/9/8, 대체문자 0, 부칙 있음. 쪽 단위 기본 모드라 한 줄에 여러 조가 이어져 있고 쪽 머리글("법제처 N 국가법령정보센터 …")이 본문 사이에 끼어 있음(오류는 고치지 않음)
- 대조: script: Claude outputs/compare_rules_2026.py v1.1(읽기 전용). 대상 238개 = 방송심의규정 70·광고심의규정 59·상품판매방송규정 72·통신심의규정 26·등급분류규칙 11(기대값과 일치). 방법은 1절 인용 블록(">" 줄, 앞의 "> " 제거)을 정규화해 등재본 변환본 안에서 포함 여부와 뒤따르는 문언(조문 끝 누락)을 확인. 정규화: 공백, 가운뎃점(ㆍ ・ ‧ ․ ･ → ·), 낫표(｢｣ → 「」), 따옴표 모양, 날짜 표기, 쪽 머리글 제거. 인용 블록 안 `**`로 시작하는 정정 메모 줄은 비교에서 제외(방송심의규정 제21조·제25조 2페이지)
- 결과: 일치 237 / 불일치 1(공백만 정리해도 일치 111, 나머지 126은 위 정규화로 일치). 규칙별 일치: 방송심의규정 69/70, 광고심의규정 59/59, 상품판매방송규정 72/72, 통신심의규정 26/26, 등급분류규칙 11/11
- 불일치 1건: [[방송심의규정 제7조]] 제16항 표기. 페이지·공표본은 "⑯", 등재본은 "<16>"(법령 MCP get_admin_rule MST 2200000108985 jo 제7조 재조회로 확인. PDF 변환본에서는 "1^"로 추출됨). 문언은 같고 항 번호 기호만 다름. 고치지 않음("승인 후 반영")
- MCP 조회 기준: 법령 MCP get_admin_rule, 행정규칙일련번호 방송심의규정 2200000108985·광고심의규정 2200000108989·상품판매방송규정 2200000108991·통신심의규정 2200000108993·등급분류규칙 2200000108987(전부 공포 2026.9.21., 시행 2026.9.29.). 국가법령정보센터 웹 화면과의 동일성은 별도로 확인하지 않음. 일치 판정은 사용자가 내려받은 등재본 PDF의 변환본 기준
- 일치 페이지 237개 반영(치환 스크립트, 페이지마다 바꿀 문장이 한 번만 있는지 확인): 열린 항목 "- [ ] 국가법령정보센터에 제N호가 등재되면 …"을 "- [x] …: 해소(2026-11-11). 국가법령정보센터 등재본(행정규칙일련번호 …)과 1절 문언이 같다"로 닫음, sources에 web 항목(행정규칙일련번호, 확인일) 추가, text_basis 끝 "(국가법령정보센터 등재 전)" → "(국가법령정보센터 등재본과 대조, 2026-11-11)", verified_at·updated 갱신. 본문 1절 인용 블록은 바꾸지 않음. web: 항목의 URL은 DRF lawService 행정규칙(target=admrul) 형식이며 링크 동작은 확인하지 않음
- registry: SOURCE_REGISTRY.yaml v1.49 → v1.50, 새 id 5개(law_rule8_nlic, law_rule10_nlic, law_rule11_nlic, law_rule9_nlic, law_rule12_nlic), 등급 ①(새 id 추가, 기존 항목 수정 없음, 사용자 기본값 public·classification_confirmed·remote_allowed true). 기준본 지위는 정하지 않음(canonical·searchable 기본값) — 보고 뒤 사용자 결정(②등급). YAML 파싱·id 중복 0·새 path 존재 확인. 참고: 기존 항목 1개의 path("2 data_csv/통계_csv/방송/보정 전_csv/2012-2017 방송심의 통계.csv")가 현재 존재하지 않음(이번 변경과 무관, 미처리)
- 검증: wiki_lint.py exit=0, 열린 항목 969 → 732(237 감소 = 일치 페이지 수), broken_links 38(같은 항목)·orphans 0·broken_sources 0·sources_bad 0. 색인 reindex_last.log exit=0, 추가 5 / 갱신 237
- 백업: Claude outputs/schema_backup/SOURCE_REGISTRY_v1.49_20261111.yaml
- 커밋 메시지 초안: fix: 위원회 규칙 제8~12호 등재본 대조, 조문 237개 해소 반영, registry v1.50, compare_rules_2026.py 신설

## [2026-11-11] fix | wiki_lint.py v1.5: AGENTS.md v1.38 8절 단서 반영, internal_aggregate 항목 신설 | Claude Sonnet 5.5
- 세션: Claude Code. 승인: 2026-11-11 사용자가 작업 3의 변경 범위 보고를 가리켜 "작업 3 승인"
- 변경: Claude outputs/wiki_lint.py v1.4 → v1.5. internal로 지정된 출처를 쓴 페이지 가운데, 그 internal 출처의 registry type이 모두 statistics이고 internal 자료 링크·언급 단서가 없으면 internal_suspect에서 빼 internal_aggregate(확인용 목록)로 출력. 그 밖의 판정은 그대로. 위키 페이지는 바꾸지 않음
- 검증(같은 위키 상태에서 v1.4와 v1.5 실행 비교): 두 번 모두 exit=0. JSON에서 달라진 키는 internal_suspect(19 → 7)와 신설 internal_aggregate(12)뿐이며, 빠진 12개 = 새 항목의 12개로 같은 집합이고 internal_suspect에 새로 들어온 페이지는 없음. 12개는 모두 통신심의 쟁점 페이지(광고성 정보 전송·게시, 교통단속 회피장비 판매정보, 다단계 판매정보 등)
- 참고: 남은 internal_suspect 7개는 소송 현황 문서 링크·언급 등 다른 단서가 있는 페이지로, 이번 변경 범위 밖
- Claude outputs/README.md의 wiki_lint.py 설명을 v1.5로 갱신
- 커밋 메시지 초안: fix: wiki_lint v1.5 internal 집계값 페이지를 internal_aggregate로 분리(AGENTS v1.38 8절)

## [2026-11-11] fix | 방송심의규정 제7조: 제16항 번호 기호 "⑯" 유지 확정, 등재본 대조 열린 항목 해소 | Claude Sonnet 5.5
- 세션: Claude Code. 사용자 확인 2026-11-11: "방송심의규정 제7조의 제16항 번호 기호는 ⑯이 맞어". 앞선 규칙 제8~12호 대조에서 238개 중 유일한 불일치였던 항목(등재본 원문은 "<16>", 문언은 같음)
- 처리: 1절 인용 블록은 바꾸지 않음(⑯ 유지). 다른 일치 페이지와 같은 방식으로 열린 항목을 닫고(번호 기호 차이와 사용자 확인을 같은 줄에 적음), sources에 web 항목(행정규칙일련번호 2200000108985, 확인일) 추가, text_basis 끝을 "(국가법령정보센터 등재본과 대조, 2026-11-11)"로, verified_at·updated 갱신
- 결과: 규칙 제8~12호 등재본 대조 238개 모두 분류·해소 완료(일치 237 + 사용자 확인 1). wiki_lint.py exit=0, 열린 항목 732 → 731
- 커밋 메시지 초안: fix: 방송심의규정 제7조 제16항 번호 기호 ⑯ 유지 확정, 등재본 대조 해소

## [2026-11-11] schema | SOURCE_REGISTRY.yaml v1.50 → v1.51: 등재본 변환본 5개(law_rule8/9/10/11/12_nlic)를 중복본으로 변경 | Claude Sonnet 5.5
- 등급 ②(기존 항목의 canonical·duplicate_of·searchable 변경). 승인: 2026-11-11 사용자가 기준본 지위 제안 가운데 "등재본 변환본 5개를 중복본으로 바꾸는 안"을 선택하며 "canonical: false, duplicate_of는 각 공표본 변환본 id, searchable: false, 위키 sources는 옮기지 마"라고 지시
- 변경: law_rule8_nlic·law_rule9_nlic·law_rule10_nlic·law_rule11_nlic에 canonical false, duplicate_of law_broadcast, searchable false. law_rule12_nlic에 canonical false, duplicate_of law_telecom, searchable false. notes의 "기준본 지위는 정하지 않았다" 문장을 중복본 결정(2026-11-11)과 기준본 설명으로 교체. ingest(wiki)·classification 등 그 밖의 필드는 바꾸지 않음
- duplicate_of 대상: 공표본 변환본(규칙 제8~12호)은 파일 단위 id가 없고 폴더 단위 항목(방송 law_broadcast, 통신 law_telecom)이 포함하므로 그 폴더 id를 가리킴(기존 duplicate_of: law_broadcast 항목과 같은 방식). 공표본용 파일 단위 id 5개를 새로 만드는 안은 승인 범위 밖이라 하지 않음
- 영향: 위키 페이지 sources에는 등재본 변환본 경로가 없어 sources_bad 영향 없음(위키 sources는 옮기지 않음). 등재본 대조 결과는 조문 페이지의 web: 출처와 log에 남음
- 검증: YAML 파싱 id 88개·중복 0, 5개 항목의 canonical·duplicate_of·searchable와 대상 id 존재, 새 path 존재 확인. 재색인 reindex_last.log exit=0, index_report.md "삭제 5"(등재본 조각 5개 제거), 검색 DB에서 등재본(20260929) 문서 0건(읽기 전용 조회)
- 백업: Claude outputs/schema_backup/SOURCE_REGISTRY_v1.50_20261111.yaml
- 커밋 메시지 초안: schema: registry v1.51 등재본 변환본 5개 중복본 처리(canonical false, searchable false)

## [2026-11-11] schema | SOURCE_REGISTRY.yaml v1.51: stats_root_dup의 path를 백업_보정 전_csv로 정정 | Claude Sonnet 5.5
- 등급 ②(기존 항목의 path 변경). 승인: 2026-11-11 사용자가 REGISTRY 정리 중 "stats_root_dup의 path를 '2 data_csv/통계_csv/방송/백업_보정 전_csv/2012-2017 방송심의 통계.csv'로 고치는 것만" 승인. notes·중복본 38건·remote_allowed는 그대로 둠
- 변경: stats_root_dup.path "2 data_csv/통계_csv/방송/보정 전_csv/2012-2017 방송심의 통계.csv" → "2 data_csv/통계_csv/방송/백업_보정 전_csv/2012-2017 방송심의 통계.csv". 폴더 이름이 바뀌어 옛 경로의 파일이 없던 상태였고, 새 경로에 파일이 있음. canonical false·duplicate_of stats·searchable false는 그대로
- 검증: 새 path 존재, path 중복 0, 파일이 없는 파일 단위 path 0(위 항목과 같은 v1.51 한 번에 반영)
- 백업: Claude outputs/schema_backup/SOURCE_REGISTRY_v1.50_20261111.yaml (위 항목과 같은 판)
- 커밋 메시지 초안: schema: registry v1.51 stats_root_dup path 정정

## [2026-11-11] schema | AGENTS.md v1.38 → v1.39: AGENTS_절차.md 6.8절 "정기 점검·자동화" 신설, B 예약 작업 생성 | Claude Opus 5.5
- 등급 ②. 승인: 2026-11-11 사용자가 정례화 설계안 1·2절(6.8절 신설, AGENTS.md 6절 문장·대응표 행)을 가리켜 "승인, 지금 반영"
- 결정(같은 날 결정 질문): A 매주 수요일 09:40 Windows 작업 스케줄러, B 매월 첫째 주 수요일 14:13 claude.ai 예약 작업(PC 연결 필요), 알림 휴대폰 푸시, 새 △ 통계 파일은 감지·알림만 하고 반영은 C. 알림과 통계 범위는 사용자 무응답으로 인계메모 기본값을 따름
- 변경: AGENTS_절차.md 6.7절 뒤에 6.8절(19줄) 삽입. AGENTS.md 머리말 판 번호 v1.39, 6절 첫 줄 "6.2~6.7" → "6.2~6.8"(정기 점검·자동화 추가), 대응표에 "정기 점검·자동화 → AGENTS_절차.md 6.8" 행 추가
- 영향: 운영 규칙 문서만 바뀜. 위키 페이지·registry 변경 없음
- 검증: 바꿀 문장 각 1회 확인(치환 스크립트), diff로 의도한 3곳·19줄만 바뀐 것 확인, BOM 없음·LF 유지(치환 직후 붙은 BOM을 바로 제거)
- 백업: Claude outputs/schema_backup/AGENTS_v1.38_20261111.md, Claude outputs/schema_backup/AGENTS_절차_v1.38_20261111.md
- 예약 작업: "AI 자료창고 월간 정비(B)"(cron `CRON_TZ=Asia/Seoul 13 14 * * 3`, PC 필요, 폴더 J:\AI 자료·J:\MCP\ai-vault-mcp, 푸시 알림, 승인 설정 auto(서버 지정, 사용자가 유지 선택)). 처음 만든 작업은 폴더가 붙지 않아 지우고 폴더를 지정해 다시 만듦. 같은 날 안전 시험 실행(위키 쓰기 없이 data\maintenance\test_B_2026-11-11.md에만 쓰도록 지시)
- 남은 일(Claude Code): A 구현(maintenance_check.py·bat·작업 스케줄러 등록), 스킬 wiki-maintenance 신설·stats-monthly-update 0단계 추가, 커밋. 남은 lint 제안 ③④⑤⑦⑧⑨⑩은 첫 B 보고서(2026-12-02)의 미처리 제안으로 넘김(사용자 결정)
- 세션: 채팅(원격 셸, 삭제 제한)이므로 커밋하지 않음
- 커밋 대상 파일: AGENTS.md, AGENTS_절차.md, Claude outputs/schema_backup/AGENTS_v1.38_20261111.md, Claude outputs/schema_backup/AGENTS_절차_v1.38_20261111.md, 0 wiki/log.md
- 커밋 메시지 초안: schema: AGENTS v1.39 AGENTS_절차 6.8절 정기 점검·자동화 신설(②)

## [2026-11-11] fix | 정기 점검 A 구현(maintenance_check.py·bat), 스킬 wiki-maintenance 신설·stats-monthly-update 0단계 추가 | Claude Sonnet 5.5
- 세션: Claude Code. 승인: 인계메모 작업 1·2(2026-11-11 사용자 승인, 스킬 정비안 승인 포함)
- 신설: Claude outputs/maintenance_check.py v1.0(읽기 전용, AGENTS_절차.md 6.8절 A 항목 전부), Claude outputs/run_maintenance_check.bat v1.1(run_history.log에 "시각 종료코드" 한 줄), .claude/skills/wiki-maintenance/SKILL.md(6.6·6.8절 기준 6단계). 변경: .claude/skills/stats-monthly-update/SKILL.md(1단계 앞 0단계 추가), Claude outputs/README.md(두 파일 설명 추가)
- 결과 위치: J:\MCP\ai-vault-mcp\data\maintenance\{YYYY-MM-DD}_check.json·_요약.md·run_history.log(자료창고 안에는 쌓지 않음)
- 검증: 수동 실행 종료 0, 같은 날 두 번 실행해 JSON(run_at 제외)이 같음, bat 실행 후 run_history.log에 한 줄씩 추가. wiki_lint 수치(열린 항목 731, 깨진 출처 0)가 이전 lint 기록과 일치. 위키·스키마·search.db는 바꾸지 않음
- 알려진 점: 클리핑 새 파일 수는 이전 날짜의 check.json이 있어야 계산되어 첫 실행은 "기준 없음". 작업 스케줄러 등록은 사용자가 PowerShell로 함
- 커밋 대상 파일: Claude outputs/maintenance_check.py, Claude outputs/run_maintenance_check.bat, Claude outputs/README.md, .claude/skills/wiki-maintenance/SKILL.md, .claude/skills/stats-monthly-update/SKILL.md, 0 wiki/log.md
- 커밋 메시지 초안: feat: 정기 점검 A 단계 maintenance_check.py·bat 신설, 스킬 wiki-maintenance 신설·stats-monthly-update 0단계 추가

## [2026-11-11] fix | B 예약 작업 프롬프트 v2: 원격 도구가 없을 때 로컬 도구로 접근하도록 0단계 수정 | Claude Sonnet 5.5
- 세션: Claude Code. 사용자가 데스크톱 앱 편집 창에서 직접 붙여넣어 저장(2026-11-11, 사용자 완료 보고). 쓰기 범위 4가지·하지 말 것·일정(수 14:13)은 바뀌지 않아 6.8절 변경 없음
- 사유: 예약 작업이 "이 컴퓨터 필요·로컬 폴더" 설정이라 mcp__remote-devices__* 도구가 없을 수 있고, 그러면 0단계가 "연결되지 않음"으로 끝날 위험이 있음(추정). 시험 실행(2026-11-11)은 0단계 날짜 조건(1~7일 아님)으로 한 줄 종료한 정상 동작이며, 수동 실행에 붙인 시험 지시는 참고 자료로 취급해 따르지 않음(방어 규칙 정상)
- 변경: 0단계 두 번째~네 번째 글머리표, 4c log 형식의 "세션" 줄. 전문은 Claude outputs/schema_backup/B_예약작업_프롬프트_v2_20261111.md
- 미확인: 1~7일 이후 본 경로(PC 접근·법령 MCP·쓰기)는 첫 실제 실행(2026-12-02)에서 확인
- 커밋 대상 파일: Claude outputs/schema_backup/B_예약작업_프롬프트_v2_20261111.md, 0 wiki/log.md
- 커밋 메시지 초안: docs: B 예약 작업 프롬프트 v2 보관(원격 도구 없을 때 로컬 접근)

## [2026-11-12] fix | 외부 개선 의견 대조 결과 반영: 통계 갱신 복구 순서(update_stats_2026 v1.1)·lint 판정 정리(wiki_lint v1.6)·검색 정렬(mcp_server v1.13) | Claude Sonnet 5.5
- 세션: Claude Code. 인계메모 작업 1~4(2026-11-12). 순서는 데이터 손상 위험 → 주간 점검 일정 → 작업량 순(사용자 결정). 위키 페이지·SOURCE_REGISTRY.yaml·AGENTS 계열 문서는 고치지 않음
- 1) update_stats_2026.py v1.1: --apply를 registry 새 내용 메모리 검증 → CSV·registry 백업(J:\MCP\ai-vault-mcp\data\stats_backup\{날짜_시각}\) → registry 쓰기 → CSV 임시 파일 복사 후 os.replace → 디스크 재검증 순으로 바꾸고, 어느 단계든 예외가 나면 CSV·registry를 함께 복원해 종료 코드 1(log·reindex 없음). log 항목에 새 파일 sha256·기준일·실행 옵션 한 줄 추가. dry-run·종료 코드 2는 그대로. 시험(임시 복사본): 정상 실행 결과가 v1.0과 같음(CSV·registry 바이트 동일, log는 추가 줄만 다름), 강제 실패 4종(CSV 교체 실패·log 쓰기 실패·사전 검증 실패·교체 뒤 해시 불일치) 모두 실행 전후 sha256 동일·reindex.request 없음. 실제 2026_잠정.csv·registry는 시험에 쓰지 않음
- 2) wiki_lint.py v1.6, maintenance_check.py v1.1: log.md·log/ 조각의 끊긴 링크를 broken_links_log(참고)로 분리(현재 broken_links 0, broken_links_log 38). 종료 코드 1 조건을 broken_sources·내용 페이지 broken_links·yaml_error·sources_bad로 확대(0·1만 사용), JSON에 exit_reasons 추가. 현재 종료 1의 사유는 yaml_error 1건(위키 루트 웹클리퍼 기본-템플릿-clipper.md, Cowork가 @templates로 이동 예정이라 예외 처리 없음). maintenance_check 요약이 log 링크를 따로 표시하고 종료 1 사유를 적으며, lint 출력이 JSON이 아니면 실행 실패로 기록
- 3) mcp_server.py v1.13: search의 ORDER BY만 변경(① 파일명 정확 일치 문서 맨 앞 ② bm25 × 위키 층 가중치 1.14 ③ chunk_id). 시험 질의 7종 total 전부 불변. '방송심의규정 제46조' 조문 페이지 15위 → 전체·kind=wiki 1위, '객관성' 위키 0 → 9/10, '공정성' 0 → 10/10. 적용하려면 Claude 데스크톱 재시작 필요
- 확인 결과: aliases는 별도 색인되지 않으나 머리말 원문이 문서 첫 조각에 들어 있어 본문 검색으로는 찾힘(260개 조각). reindex는 색인 대상 파일을 바꾸지 않아 요청하지 않음
- 승인 후 반영(미반영): AGENTS_절차.md 6.6절·10절에 log 링크는 broken_links_log로 따로 세고 고치지 않는다는 문구 추가(②등급); aliases 색인·문서 단위 묶기·2글자 검색어 우선 조회(색인기 변경·전체 재구축·offset 의미 변경 동반, 2단계)
- 커밋 대상 파일: J:\AI 자료 저장소: Claude outputs/update_stats_2026.py, Claude outputs/wiki_lint.py, Claude outputs/maintenance_check.py, Claude outputs/README.md, .claude/skills/stats-monthly-update/SKILL.md, 0 wiki/log.md / J:\MCP\ai-vault-mcp 저장소: mcp_server.py, README.md (Claude Code가 직접 커밋)

## [2026-11-12] schema | AGENTS v1.39 → v1.40: AGENTS_절차.md 6.6절·10절에 log 링크 처리 문구 추가(②) | Claude Sonnet 5.5
- 등급·승인: ②등급. 2026-11-12 사용자가 위 fix 항목의 승인 대기 제안(6.6절·10절 문구)을 가리켜 "승인, 반영"이라고 승인
- 변경: 6.6절 "존재하지 않는 페이지로 향하는 링크" 항목 아래에 broken_links / broken_links_log 구분과 wiki_lint 종료 코드(0·1, 1의 조건) 문장 추가. 10절 끝에 log의 [[링크]]는 당시 이름 그대로 두고 lint는 broken_links_log로 따로 센다는 문장 추가. AGENTS.md는 판 번호·개정일만 갱신
- 백업: Claude outputs/schema_backup/AGENTS_v1.39_20261112.md, Claude outputs/schema_backup/AGENTS_절차_v1.39_20261112.md. 치환 스크립트로 수정하고 바꿀 문장이 한 번만 있음을 확인
- 검증: wiki_lint v1.6 재실행 broken_links 0, broken_links_log 38(변화 없음)
- 커밋 대상 파일: AGENTS.md, AGENTS_절차.md, Claude outputs/schema_backup/AGENTS_v1.39_20261112.md, Claude outputs/schema_backup/AGENTS_절차_v1.39_20261112.md, 0 wiki/log.md

## [2026-11-12] lint | 열린 확인 항목 분류, internal 의심·unknown 출처 재점검, 클리퍼 템플릿 이동 | Claude Opus 5.5
- 세션: 채팅(원격 셸). 외부 개선 의견 대조 후속 가운데 Cowork 몫(사용자 "다음 진행", 2026-11-12)
- 신설: Claude outputs/open_items_classify.py v1.0(읽기 전용, wiki_lint.py 결과로 열린 항목을 A~F 유형으로 기계 분류하고 반복 문장 묶음 출력), 분석/2026-11-12 열린 확인 항목 분류.md(열린 항목 731개·389쪽 분포, 반복 묶음 9종, 시한 지난 항목, 처리 순서 제안, 보안등급 재점검). 분석/_index.md 등재, 분석/2026-11-11 lint 보고.md 13절 끝에 후속 링크 한 줄(내용 변경 없음)
- 보안등급 재점검: internal_suspect 7쪽은 모두 internal 소송 목록 문서로 링크·언급만 하고 내용은 옮기지 않음(사건번호 출처 대조, 2016누75915는 public 논문 인용). 2026-11-11 보고 6절 판단 유지. unknown 출처 위키 2쪽의 @Inbox 메모 2개는 보안등급 unknown(원격 허용 꺼짐), public 변경 여부는 사용자 결정 사항으로 남김. 판례 취합파일 문서 페이지의 classification internal(출처 registry precedent는 public)은 사용자 확인 사항으로 남김
- 이동: 0 wiki/웹클리퍼 기본-템플릿-clipper.md → 0 wiki/@templates/(AGENTS.md 2.2절, 2026-11-11 lint 보고 제안 ⑩, 사용자 승인 2026-11-12)
- 검증: wiki_lint v1.6 종료 0(exit_reasons 없음, yaml_error·stray 0, broken_links 0, 고립 0), 열린 항목 731, 분류 합계 731(A 121·B 56·C 112·D 133·E 208·F 101)
- 커밋 대상 파일: 0 wiki/분석/2026-11-12 열린 확인 항목 분류.md, 0 wiki/분석/_index.md, 0 wiki/분석/2026-11-11 lint 보고.md, 0 wiki/웹클리퍼 기본-템플릿-clipper.md(삭제로 기록), 0 wiki/@templates/웹클리퍼 기본-템플릿-clipper.md, Claude outputs/open_items_classify.py, Claude outputs/README.md, 0 wiki/log.md
- 커밋 메시지 초안: lint: 열린 확인 항목 분류(open_items_classify.py v1.0), 보안등급 재점검, 클리퍼 템플릿 @templates 이동

## [2026-11-12] fix | 방송법 제83조·제86조 verified_at 기입, @Inbox 메모 2개 보안등급 public, 열린 항목 분류 페이지 정정 | Claude Opus 5.5
- 세션: 채팅(원격 셸). 사용자 지시(2026-11-12): 수신함 메모 2개 보안등급 public(앞으로 별도 언급 없으면 public), 판례 취합파일 문서 페이지 public 변경, 방송법 제83조·제86조 "확인됐으니 진행"
- 방송법 제83조·제86조: 법령 MCP get_law_text로 현행본(법률 제21572호, 법령일련번호 285487)과 시행예정본(제22111호, 시행 2027.4.21., 법령일련번호 291333)의 두 조를 조회해 위키 문언·개정 주석과 일치함을 확인. verified_at 2026-09-29 → 2026-11-12, text_basis 갱신, sources에 web 항목 추가, 첫머리 대조 상태 갱신, 1절 제목 "기준 조문" → "현행 조문", 7절 해당 항목 닫음(열린 항목 731 → 729)
- @Inbox: "방미통심위 심의를 거치지 않는 온라인 불법정보 삭제·차단 분야", "보건복지부 자살예방정보 삭제 권한 관련"의 머리말 보안등급 unknown → public(본문 수정 없음)
- 보류: 판례 취합파일 문서 페이지의 classification internal 해제. 판결 목록에 internal 소송 목록 문서에서 옮긴 확정일·선고일이 있어 AGENTS.md 8절·2026-09-23 사용자 결정에 따른 표시로 확인됨. 같은 날 앞선 분석 페이지의 "의도 확인 필요" 서술은 Claude의 오판이라 정정하고 사용자에게 보고함
- 분석/2026-11-12 열린 확인 항목 분류.md 5절(수신함 메모 처리, 판례 문서 페이지 정정)·3절(방송법 해소) 갱신
- 검증: wiki_lint v1.6 종료 0, 깨진 링크·고립·머리말 오류 0
- 커밋 대상 파일: 0 wiki/조문/방송법 제83조.md, 0 wiki/조문/방송법 제86조.md, 0 wiki/@Inbox/방미통심위 심의를 거치지 않는 온라인 불법정보 삭제·차단 분야.md, 0 wiki/@Inbox/보건복지부 자살예방정보 삭제 권한 관련.md, 0 wiki/분석/2026-11-12 열린 확인 항목 분류.md, 0 wiki/log.md
- 커밋 메시지 초안: fix: 방송법 제83조·제86조 verified_at 기입, 수신함 메모 2개 보안등급 public, 열린 항목 분류 페이지 정정

## [2026-11-12] fix | 통신심의 쟁점 11쪽의 "그 밖의 법원 판결·위원회 유권해석 검색" 항목을 검색 한계 서술로 옮기고 닫음 | Claude Opus 5.5
- 세션: 채팅(원격 셸). 사용자 결정(2026-11-12): 완료 기준이 없는 탐색형 항목이므로 "한계 서술로 바꾸고 닫기"
- 변경: 각 쪽 4.1절(법원 판결 검색 결과) 끝에 "검색 한계" 한 줄 추가(MCP 검색만 했고 공식 판례 DB 전수·유권해석 검색은 하지 않았다는 범위 표시), 7절 해당 항목을 [x]로 닫고 옮긴 위치 표기, updated 갱신. 그 밖의 내용 변경 없음
- 분석/2026-11-12 열린 확인 항목 분류.md 4절 4항에 처리 결과 한 줄 추가
- 검증: wiki_lint v1.6 종료 0, 깨진 링크·고립·머리말 오류 0, 열린 항목 729 → 718
- 커밋 대상 파일: 0 wiki/쟁점/광고성 정보 전송·게시(통신심의).md, 0 wiki/쟁점/교통단속 회피장비 판매정보(통신심의).md, 0 wiki/쟁점/다단계 판매정보(통신심의).md, 0 wiki/쟁점/무신고 숙박업정보(통신심의).md, 0 wiki/쟁점/범죄 모의정보(통신심의).md, 0 wiki/쟁점/병역의무 기피·감면정보(통신심의).md, 0 wiki/쟁점/스파이앱 판매정보(통신심의).md, 0 wiki/쟁점/자격증 대여정보(통신심의).md, 0 wiki/쟁점/통화·유가증권 위조정보(통신심의).md, 0 wiki/쟁점/헌혈증서 매매정보(통신심의).md, 0 wiki/쟁점/휴대폰 복제정보(통신심의).md, 0 wiki/분석/2026-11-12 열린 확인 항목 분류.md, 0 wiki/log.md
- 커밋 메시지 초안: fix: 통신심의 쟁점 11쪽 판결 검색 항목을 검색 한계 서술로 전환

## [2026-11-12] fix | 통신심의 쟁점 2쪽 정보통신망법 제21500호 시행분 대조(광고성 정보 전송·게시, 해킹·바이러스정보) | Claude Opus 5.5
- 세션: 채팅(원격 셸). 사용자 지시 "남은거 처리 진행"(2026-11-12). 분석/2026-11-12 열린 확인 항목 분류 3절의 시한 지난 항목
- 대조: 법령 MCP get_law_text로 정보통신망법 제48조·제50조·제50조의4·제50조의7·제50조의8·제71조를 제21305호(시행 2026.7.7., 법령일련번호 282481)·현행 제21988호(시행 2026.10.2., 290001)·제21500호 시행예정본(시행 2027.4.1., 285199)으로 조회해 비교
- 결과: 제50조의4 제4항 개정(2026.3.31., 대통령령 유형·기준에 따른 5개 조치), 제71조 제1항 제13호의2 신설(제48조의4 제5항 명령 위반 자료 미보전). 나머지 4개 조는 세 판 모두 같음. 2027.4.1. 시행분은 6개 조를 바꾸지 않음
- 반영: 두 쪽의 1절 판 표와 대조 목록에 한 항목씩 추가(〔해석〕 표시 포함), sources에 web 항목 추가, 7절 해당 항목 닫음, updated 갱신. 분석/2026-11-12 열린 확인 항목 분류 3절에 해소 표시
- 검증: wiki_lint v1.6 종료 0, 깨진 링크·고립·머리말 오류 0, 열린 항목 718 → 716
- 커밋 대상 파일: 0 wiki/쟁점/광고성 정보 전송·게시(통신심의).md, 0 wiki/쟁점/해킹·바이러스정보(통신심의).md, 0 wiki/분석/2026-11-12 열린 확인 항목 분류.md, 0 wiki/log.md
- 커밋 메시지 초안: fix: 통신심의 쟁점 2쪽 정보통신망법 제21500호 시행분 대조 반영
