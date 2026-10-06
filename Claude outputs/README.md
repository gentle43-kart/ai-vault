# ai-vault-mcp

AI 자료창고(J:\AI 자료)의 검색 DB와, 나중에 붙일 MCP 서버를 두는 폴더입니다. 검색 DB와 읽기 전용 MCP 서버(mcp_server.py v1.5)가 있습니다(색인기 v1.8, 검색기 v1.2).

## 변경 이력

- v1.11 (2026-10-06, Claude): mcp_server.py v1.5: `search`에 선택 인자 `kind`(자료 묶음)와 `registry_id`(정확한 id 목록) 추가. 둘 다 기본값은 빈 값이며 생략하면 v1.4와 결과가 같다. 값은 SQL에 직접 넣지 않고 `?` 매개변수로 넘기고, 틀린 값은 오류로 사용 가능한 값을 알려 준다. kind 묶음은 SOURCE_REGISTRY의 type을 기준으로 한다(보안등급·법령 여부 기준이 아님). `search_case`는 의결번호로 이미 좁혀지므로 바꾸지 않았다. DB·색인 변경 없음(재색인 불필요).
- v1.10 (2026-10-05, Claude): build_index.py v1.8: 색인 성공 후 `PRAGMA wal_checkpoint(TRUNCATE)`로 `search.db-wal`을 비우고, 결과를 `index_report.md`의 "WAL 정리" 줄에 적는다(완료/보류/오류). MCP 서버 등 다른 연결이 읽기 중이면 보류될 수 있으며, 보류되어도 exit=0이다. 다음 색인 때 다시 시도한다. `--full`은 `search.db`와 함께 남은 `search.db-wal`·`search.db-shm`도 지운다(이전 DB의 WAL이 새 DB에 적용되어 손상되는 것을 막음). DB 구조 변경 없음(전체 재색인 불필요).
- v1.9 (2026-10-05, Claude): mcp_server.py v1.4: 명령행 `--remote-extra-ids` 추가(환경변수보다 우선, 형식 오류 id는 표준오류로 알림). v1.8에 적었던 tunnel-client `--env` 옵션과 프로필 경로는 공식 문서에서 확인되지 않아 삭제하고, `--mcp-command` 안에 옵션을 적는 방식으로 바꿈. build_index.py v1.7: 수신함 메모 머리말 `보안등급:`이 비어 있으면 다음 줄(예: `status: 대기`)을 보안등급으로 읽던 오류 수정(정규식 `\s*` → `[ \t]*`). 보안등급이 비어 있거나 없는 메모는 classification을 `unknown`으로 기록해 `--scope all` 결과 제목에 `[unknown]`이 붙는다. 원격 제외 판정(public만 허용)은 v1.6과 같다. 기존 DB는 해당 메모가 다시 색인될 때 반영된다(전체 재색인 불필요).
- v1.8 (2026-10-01, Claude): mcp_server.py v1.3: AIVAULT_REMOTE_EXTRA_IDS 추가(remote 범위에서 특정 registry_id 추가 허용, 기본 빈값). build_index.py v1.6: effective()가 type: inbox 파일의 보안등급 머리말 필드를 반영해 원격 허용 여부 결정. README에 tunnel-client 환경변수 전달 방법 추가.
- v1.7 (2026-10-01, Claude): mcp_server.py v1.2: 조회 범위 선택 추가. `AIVAULT_SCOPE=all`(또는 `--scope all`)이면 remote_allowed 조건 없이 색인된 전체 자료(internal·unknown 포함)를 돌려주고, 결과 제목 앞에 `[internal]` 등 보안등급을 붙인다. 기본값(remote)은 v1.1과 같아 ChatGPT 터널 설정은 바꾸지 않는다. Claude 데스크톱 `claude_desktop_config.json`의 ai-vault env에만 `AIVAULT_SCOPE: all`을 둔다. fetch 메타데이터에 remote_allowed·scope 추가.
- v1.6 (2026-09-22, Claude): build_index.py v1.5: 위키(0 wiki) 페이지 색인. SOURCE_REGISTRY의 type: wiki 항목이 있어야 색인됨. 관리용 노드(index.md, log.md, _index.md)는 제외. 페이지 머리말 classification이 public이 아니면(internal 등) 그 페이지만 원격 제외. 시험용 --registry 옵션 추가. mcp_server.py v1.1: 안내문에 위키 자료 성격 추가.
- (2026-09-27, Claude) hyup_articles.py v1.0 추가. 「협찬고지 등에 관한 규칙」(구 「협찬고지에 관한 규칙」) 조문별 집계(AGENTS.md 7.1 "협찬고지규칙 통계" v1.13). Claude outputs\에만 둔다.
- (2026-09-25, Claude) election_articles.py v1.0 추가. 선방위 통계 CSV 조문별 집계(위키 선거방송특별규정 제5조·제10조·제18조 5절 근거). Claude outputs\에만 둔다.
- (2026-09-23, Claude) section_stats.py v1.0 추가. 제150호 절 단위 집계(절 행 수, 절 밖 조문 병합, 제46조 단독 비율, 의결일·프로그램명 기준 안건 추정). stats_articles.py의 load·조문 식별 재사용. Claude outputs\에만 둔다.
- (2026-09-23, Claude) wiki_lint.py v1.0 추가. AGENTS.md 6.6절 lint의 기계 점검 항목(머리말, 링크, 역링크, sources, internal 표기, 사례 상태, 추가 확인 필요 집계)을 읽기 전용으로 점검해 JSON으로 출력. Claude outputs\에만 둔다.
- (2026-09-23, Claude) count_article_item.py v1.0 추가. 호·항 단위 행 추출(위키 쟁점 페이지 "성적 수치심을 유발하는 신체 촬영" 3절 근거). Claude outputs\에만 둔다.
- (2026-09-22, Claude) stats_articles.py v1.0 추가. 통계 CSV 조문별 집계(AGENTS.md 7.1). 검색 DB와 무관하며 Claude outputs\에만 둔다(J:\MCP\ai-vault-mcp에 복사하지 않음).
- v1.5 (2026-09-22, Claude): mcp_server.py v1.0 추가. 도구 search·fetch·search_case, remote_allowed 자료만 제공(끌 수 없음), DB 읽기 전용, 쓰기 도구 없음. stdio(기본)와 streamable HTTP(--http) 지원.
- v1.4 (2026-09-22, Claude): build_index.py v1.4: 색인 대상 폴더에 `0 wiki/Clippings`(기사 수신함) 추가(SCAN_DIRS), 점으로 시작하는 폴더(.obsidian 등)는 건너뜀.
- v1.3 (2026-09-22, Claude): ① search.py v1.2: 2글자 이하 검색어가 항상 0건이던 오류 수정(FTS5 trigram 표의 LIKE → instr). ② build_index.py v1.3: `type: statistics`인 CSV만 decisions 표에 넣음(규정 연혁 취합본 행이 통계로 섞이던 문제). 통계가 아닌 CSV는 판 이름 행(제n호, 시행일)을 머리글로, 조 제목을 조각 제목으로 씀. 날짜로 읽지 못한 의결일 값은 decisions에 넣지 않음. 기존 DB는 `python build_index.py --full`로 다시 만들어야 반영됨.
- 운영 사본: 이 폴더(J:\MCP\ai-vault-mcp)가 실행용이고, J:\AI 자료\Claude outputs\는 같은 스크립트의 보관용 사본이다(AGENTS.md v1.5 2절). 두 곳을 함께 고친다.
- v1.1 (2026-09-21): 의결번호 인식 개선(범위 번호 `0017~0018호`, 전체회의 번호 `2024-24-0116`, 2012~2017 통계의 결합 열, 두 자리 연도 날짜, 띄어쓰기가 섞인 번호). DB 구조가 바뀌었으므로 교체 후 `python build_index.py --full` 필요.
- v1.0 (2026-09-21): 최초 작성.
- (2026-09-29, Claude) renumber_2026.py 추가. AGENTS.md v1.19 3.1절(조 번호 전면 변경 대응).

## 파일

| 파일 | 역할 |
|---|---|
| build_index.py | SOURCE_REGISTRY.yaml에서 `searchable: true`인 자료만 읽어 `data\search.db`를 만든다(원본은 읽기만 함) |
| search.py | search.db 조회(읽기 전용) |
| check_index.py | 의결번호 연결 상태 점검(읽기 전용) |
| mcp_server.py | MCP 서버(읽기 전용). 기본은 원격 허용 자료만, `AIVAULT_SCOPE=all`이면 전체 자료(Claude 데스크톱 로컬 연결용), `--remote-extra-ids`로 승인된 항목 추가. `search`는 `kind`·`registry_id`로 범위 지정 가능(v1.5) |
| stats_articles.py | (Claude outputs\에만 있음) 통계 CSV에서 「방송심의에 관한 규정」 조문별 행 수·결과 분포·기수별 분포 집계. 위키의 통계 수치 근거 스크립트 |
| count_article_item.py | (Claude outputs\에만 있음) 통계 CSV에서 특정 조의 호·항이 관련조항에 적힌 행을 뽑음. stats_articles.py의 조문 식별 함수 재사용, 검증값: 제27조 조 단위 777 |
| wiki_lint.py | (Claude outputs\에만 있음, v1.1: 중복본 판정에 레지스트리 규칙 2 적용) `python wiki_lint.py [자료창고 루트] > lint.json`. 위키를 고치지 않음. 검증: 2026-09-23 lint 보고의 수치(콘텐츠 페이지 107, 조문 63, 끊긴 링크 5종)와 일치 |
| section_stats.py | (Claude outputs\에만 있음) 절 단위 집계. 검증값: 제5절 965행, 제7절 1,816행, 제46조 1,351행. 위키 [[광고효과 등]]·[[소재 및 표현기법]] 수치 근거 |
| election_articles.py | (Claude outputs\에만 있음) 선방위 통계 CSV에서 「선거방송심의에 관한 특별규정」 조문(조 번호+조 제목)별 행 수·항별 행 수·결과 분포·선거별·연도별 분포 집계(AGENTS.md 7.1 "선거방송심의 통계"). 검증값: 02-25 1,467행, 2026년 고유 51행, 제5조(공정성) 232, 제18조(여론조사의 보도) 193, 제10조(시사정보프로그램) 157 |
| hyup_articles.py | (Claude outputs\에만 있음) 통계 CSV에서 협찬고지규칙 조문별 행 수·결과·연도·항호 분포 집계. 조 제목으로 판 판별(구 제8~11조 따로 셈). `--article 제7조 --rows`. 검증값: 표기 216행, 제7조 128, 구 제10조 41, 구 제11조 31 |
| sanction_results.py | (Claude outputs\에만 있음) 방송심의 통계 CSV 전체(12,560행)의 결과 분포를 방송법 제100조 조치 유형별로 집계(stats_articles.py의 분류를 사용). 검증값: 과징금 73, 관계자 징계 223, 경고 807, 주의 1,932, 권고 6,320, 의견제시 1,815, 시청자에 대한 사과 18(모두 2012.8.3. 전). 위키 [[방송법 제100조]] 5절 근거 |
| data\search.db | 검색 DB (자동 생성) |
| data\index_report.md | 색인 결과 보고서 (자동 생성) |
| renumber_2026.py | 2026.9.29. 제정 규칙(방송심의규정 제8호·광고심의규정 제10호·상품판매방송규정 제11호)의 조 번호 변경에 따른 조문 페이지 이름 변경과 위키 링크 치환(1회 실행 완료, 2026-09-29). MAP에 구→신 번호 대응 전체가 있다. 1회용 스크립트이며, 이미 적용된 위키에서는 실행을 중단한다(다시 적용하면 새 번호를 구 번호로 오인해 한 번 더 옮기기 때문) |
| renumber_2026_telecom.py | 통신심의규정 제12호(2026.9.29. 시행) 조 번호 변경(구 제8조의2 이후 한 칸씩)에 따른 조문 페이지 이름 변경과 링크 치환(1회 실행 완료, 2026-09-30). 1회용이며 이미 적용된 위키에서는 중단한다 |

## 처음 실행

```powershell
cd J:\MCP\ai-vault-mcp
pip install pyyaml
python build_index.py
```

- 자료를 추가하거나 고친 뒤 `python build_index.py`를 다시 실행하면 바뀐 파일만 다시 색인합니다.
- 전체를 새로 만들려면 `python build_index.py --full`을 실행합니다.
- SOURCE_REGISTRY.yaml에서 보안등급이나 원격 허용 여부를 바꾸면 해당 파일이 자동으로 다시 색인됩니다.

## 검색 예시

```powershell
python search.py "방송사고"
python search.py "제55조의2" --id minutes_broadcast --limit 20
python search.py "음주 미화"                     # 공백으로 나눈 단어를 모두 포함(AND)
python search.py "공정" --remote-only            # 원격 허용 자료만
python search.py --case 2026-방송-02-0003         # 의결번호로 회의록과 통계를 함께 찾기
python search.py --show 32                       # 조각 번호로 전문 보기
```

- 검색 방식은 SQLite FTS5 trigram입니다. 3글자 이상 단어는 색인으로 빠르게 찾고, 2글자 이하 단어는 전체를 훑어서 찾으므로 느릴 수 있습니다.
- 회의록 조각에는 회의명과 의결번호(■ 제...호 제목 기준)가 붙어 있습니다.

## 통계 집계 (stats_articles.py)

J:\AI 자료\Claude outputs\에서 실행한다(자료창고 경로를 상위 폴더로 찾음. 다른 위치에서는 환경변수 AI_VAULT 지정).

```powershell
cd "J:\AI 자료\Claude outputs"
python stats_articles.py --verify              # 검증값 대조(모두 일치해야 사용)
python stats_articles.py --article 제46조       # 결과 분포, 조 제목(판 구분), 연도별, 기수별
python stats_articles.py --article 제46조 --recent   # 2026.07~08 행 추가
python stats_articles.py --top 30
```

- 표준 라이브러리만 사용한다. 결과는 화면에만 출력하고 파일로 저장하지 않는다.

## 검색 범위 좁히기 (mcp_server.py v1.5)

`search(query, limit, kind, registry_id)`에서 `kind`와 `registry_id`는 선택이며, 생략하면 전체를 찾습니다. 회의록(약 6만 조각)·논문(약 3만 조각)에 결과가 묻힐 때 씁니다.

| kind | 대응하는 type (SOURCE_REGISTRY 기준) | 자료 |
|---|---|---|
| wiki | wiki | 위키 |
| law | law, regulation | 법령·규정·규칙 |
| minutes | meeting_minutes | 회의록 |
| stats | statistics | 통계·연감 |
| papers | research | 논문 |
| cases | casebook, precedent, interpretation | 심의사례집·판례·해석례 |
| guide | guide, commentary | 지침·해설집(law_budget 포함) |
| news | news | 기사 |
| internal | internal_doc, notes, inbox | 내부·메모류 |

- 여러 개는 `|` 또는 쉼표로 잇습니다(예: `wiki|law`). `registry_id`는 정확한 id를 쉼표로 적습니다(예: `law_broadcast,law_general`). 둘을 같이 주면 둘 다 만족하는 것만 나옵니다.
- 묶음은 type 기준이라 보안등급과 무관합니다. 공개 범위는 서버의 조회 범위(remote/all)가 따로 정하며, 예를 들어 remote에서 `kind=internal`은 0건입니다.
- `layer`는 값이 normalized·curated 둘뿐이라 인자로 만들지 않았습니다.

## 후속 과제

- law_budget(예산·여비 지침)의 ★통합본과 개별 파일 중복(SOURCE_REGISTRY.yaml notes에 "미확인"으로 적힘): 레지스트리 정리 문제로, 코워크에서 처리한다. 이번 v1.5 범위에서 제외했다(2026-10-06 결정).

## ChatGPT 연결 (OpenAI Secure MCP Tunnel)

공개 주소를 만들지 않고, PC에서 OpenAI 쪽으로 나가는 연결만 사용한다. PC가 켜져 있고 tunnel-client가 실행 중일 때만 ChatGPT에서 조회된다.

1. 패키지 설치(최초 1회): `pip install "mcp>=1.9,<2" pyyaml`  (mcp 2.x는 API가 달라 동작하지 않음)
2. 로컬 시험: `python mcp_server.py --http --port 8765` 실행 후 `http://127.0.0.1:8765/mcp` 응답 확인(Ctrl+C로 종료)
3. OpenAI Platform(https://platform.openai.com/settings/organization/tunnels)에서 터널 생성 → tunnel_id 확인. API 키는 Tunnels Read + Use 권한
4. tunnel-client Windows 실행 파일을 https://github.com/openai/tunnel-client 릴리스에서 받는다
5. PowerShell:
   ```powershell
   $env:CONTROL_PLANE_API_KEY = "sk-..."
   .\tunnel-client.exe init --sample sample_mcp_stdio_local --profile aivault --tunnel-id tunnel_... --mcp-command "python J:\MCP\ai-vault-mcp\mcp_server.py"
   .\tunnel-client.exe doctor --profile aivault --explain
   .\tunnel-client.exe run --profile aivault
   ```
6. ChatGPT: https://chatgpt.com/plugins → + (개발자 모드 앱 만들기) → Connection: Tunnel → 터널 선택 또는 tunnel_id 입력

- 원격으로 나가는 자료는 SOURCE_REGISTRY에서 public + classification_confirmed: true + remote_allowed: true인 항목뿐이다. 범위를 바꾸면 build_index.py를 다시 실행한다.
- 위키(0 wiki) 페이지는 머리말 classification이 internal 등이면 원격에서 빠진다(색인 보고서 "원격 제외 위키 페이지" 절).
- **internal 항목 추가 허용(v1.3, AGENTS.md 0절 3 예외):** `AIVAULT_REMOTE_EXTRA_IDS`에 쉼표로 구분한 registry_id를 지정하면 remote 범위에서도 해당 항목이 제공된다. 결과 제목에 `[internal]` 등 보안등급이 붙는다. 개별 승인이 없으면 비워 둔다(기본값 빈 문자열).
  - **tunnel-client에 전달(v1.4):** OpenAI 공식 문서(Secure MCP Tunnel 안내, tunnel-client `docs/configuration.md`)에는 stdio 명령에 환경변수를 넘기는 옵션이 적혀 있지 않다(2026-10-05 확인). 그래서 값을 `--mcp-command` 문자열 안에 명령행 옵션으로 적는다. 이미 만든 프로필은 같은 `--profile` 이름으로 `init`을 다시 실행하거나 `tunnel-client init --help`로 수정 방법을 확인한 뒤 `run --profile aivault`로 재시작한다.
    ```powershell
    .\tunnel-client.exe init --sample sample_mcp_stdio_local --profile aivault --tunnel-id tunnel_... --mcp-command "python J:\MCP\ai-vault-mcp\mcp_server.py --remote-extra-ids notion_notes,law_broadcast_litigation,law_budget,law_general_labor"
    ```
  - 명령행 `--remote-extra-ids`가 환경변수 `AIVAULT_REMOTE_EXTRA_IDS`보다 우선한다. 형식이 틀린 id(영문·숫자·밑줄 외 문자)는 표준오류에 알리고 무시한다.
  - **PowerShell에서 시험:** `python mcp_server.py --http --port 8765 --remote-extra-ids notion_notes,law_budget`

