# ai-vault-mcp

AI 자료창고(J:\AI 자료)의 검색 DB와, 나중에 붙일 MCP 서버를 두는 폴더입니다. 검색 DB와 읽기 전용 MCP 서버(mcp_server.py v1.7)가 있습니다(색인기 v1.10, 검색기 v1.2).

## 변경 이력

- v1.15 (2026-10-06, Claude): build_index.py v1.10: 보안 머리말 판정(보고서 11번). `effective()`가 위키·수신함 머리말을 정규식 대신 YAML로 읽고(`read_frontmatter`, 머리말은 최대 64KB) `classification`·`보안등급` 값을 `public|internal|unknown`으로 검증한다. 머리말 YAML이 깨졌거나 닫히지 않았거나 허용 값이 아니면 원격에서 제외하고(fail-closed) classification을 `unknown`으로 기록한다(종전에는 깨진 머리말의 위키 페이지가 레지스트리 값 public으로 원격 허용될 수 있었다). 머리말이 없거나 `classification` 필드가 없는 위키 페이지는 종전처럼 레지스트리 값을 따른다. 시험: DB의 위키·수신함 435건 판정이 v1.9와 같고(차이 0, internal 25건=위키 24+수신함 1), 깨진 YAML·허용 외 값·닫히지 않은 머리말·깨진 수신함 시험 파일은 원격 제외. 조각 내용은 바뀌지 않아 `PARSER_VERSION`은 1.9 그대로이며, 이후 머리말이 깨진 페이지가 생기면 증분 색인이 "메타데이터만 갱신"으로 반영한다.
- v1.14 (2026-10-06, Claude): build_index.py v1.9: 증분 판정 보완(보고서 6번). documents에 `parser_version`·`policy_hash`(분류·type·layer·period_use·case_namespace·원격 허용)·`struct_hash`(type·period_use·case_namespace) 컬럼을 추가하고(기존 DB는 실행 때 자동 추가), 판정을 바꿨다. 파일(mtime·size)이 같아도 ① `PARSER_VERSION`이나 구조 해시(type·period_use·이름공간)가 바뀌면 그 파일을 다시 색인하고, ② 보안등급·layer·원격 허용·registry_id만 바뀌면 조각은 그대로 두고 documents 행만 고친다(보고서에 "메타데이터만 갱신"으로 표시). 해시가 없는 옛 행은 DB에 저장된 값으로 이전 해시를 복원해 비교하므로 전체 재색인이 필요 없고, 첫 실행에서는 모든 행의 해시가 채워지며 "메타데이터만 갱신 N"으로 집계된다. 효과: 수신함 「영국 민원처리 기간 기준 관련.md」가 머리말대로 internal로 기록된다. 파서 동작(조각 나누기·의결번호·CSV 해석)을 바꿀 때는 `PARSER_VERSION`을 올려야 한다. 시험: DB 사본에서 1회차 컬럼 추가·2회차 전부 변경 없음, 레지스트리 사본으로 layer 변경 → 메타만, case_namespace 변경 → 재색인 확인. mcp_server.py는 바꾸지 않았다.
- v1.13 (2026-10-06, Claude): mcp_server.py v1.7: `search_case`가 `기관:번호`(예: `방통위:2012-03-0021`)를 받아 그 기관 조각만 조회한다. 종전에는 접두부만 비교해 이름공간을 버려서 `방통위:2012-03-0021`이 방심위 조각을 돌려줬다(색인기는 `방통위:2012-03`으로 저장). 허용 기관은 SOURCE_REGISTRY의 `case_namespace` 값이며 미지원 접두어는 허용 값을 알리는 오류가 난다(전각 콜론 `：`도 받음). 접두어 없는 번호는 방심위와 다른 기관 번호를 함께 찾고, 두 기관 이상이 걸리면 결과 제목 앞에 `(기관)`, 항목에 `metadata.institution`을 붙인다(한 기관만 걸리면 v1.6과 같은 응답). 시험: DB mode=ro, 기존 방심위 번호·search·fetch 결과가 v1.6과 같음(scope all·remote). DB·색인 변경 없음. 적용하려면 Claude 데스크톱 재시작 필요.
- v1.12 (2026-10-06, Claude): mcp_server.py v1.6: `search`·`search_case` 응답에 `total`(일치하는 전체 조각 수)·`returned`·`offset`·`limit`·`truncated`를 추가하고, `offset` 인자(기본 0)로 이어서 조회할 수 있게 했다. 도구 설명에 limit 최대 20(초과분은 잘림)과 truncated 확인 안내를 넣었다. `results` 항목과 순서는 v1.5와 같다(offset 이어 조회가 흔들리지 않도록 동점은 chunk_id로 정렬). 상한 20(MAX_LIMIT)은 그대로. 배경: 20건 상한에서 잘린 위키 검색 결과를 "일치 항목 전체"로 오판한 사례. total은 페이지 수가 아니라 조각 수다. DB·색인 변경 없음.
- v1.11 (2026-10-06, Claude): mcp_server.py v1.5: `search`에 선택 인자 `kind`(자료 묶음)와 `registry_id`(정확한 id 목록) 추가. 둘 다 기본값은 빈 값이며 생략하면 v1.4와 결과가 같다. 값은 SQL에 직접 넣지 않고 `?` 매개변수로 넘기고, 틀린 값은 오류로 사용 가능한 값을 알려 준다. kind 묶음은 SOURCE_REGISTRY의 type을 기준으로 한다(보안등급·법령 여부 기준이 아님). `search_case`는 의결번호로 이미 좁혀지므로 바꾸지 않았다. DB·색인 변경 없음(재색인 불필요).
- v1.10 (2026-10-05, Claude): build_index.py v1.8: 색인 성공 후 `PRAGMA wal_checkpoint(TRUNCATE)`로 `search.db-wal`을 비우고, 결과를 `index_report.md`의 "WAL 정리" 줄에 적는다(완료/보류/오류). MCP 서버 등 다른 연결이 읽기 중이면 보류될 수 있으며, 보류되어도 exit=0이다. 다음 색인 때 다시 시도한다. `--full`은 `search.db`와 함께 남은 `search.db-wal`·`search.db-shm`도 지운다(이전 DB의 WAL이 새 DB에 적용되어 손상되는 것을 막음). DB 구조 변경 없음(전체 재색인 불필요).
- v1.9 (2026-10-05, Claude): mcp_server.py v1.4: 명령행 `--remote-extra-ids` 추가(환경변수보다 우선, 형식 오류 id는 표준오류로 알림). v1.8에 적었던 tunnel-client `--env` 옵션과 프로필 경로는 공식 문서에서 확인되지 않아 삭제하고, `--mcp-command` 안에 옵션을 적는 방식으로 바꿈. build_index.py v1.7: 수신함 메모 머리말 `보안등급:`이 비어 있으면 다음 줄(예: `status: 대기`)을 보안등급으로 읽던 오류 수정(정규식 `\s*` → `[ \t]*`). 보안등급이 비어 있거나 없는 메모는 classification을 `unknown`으로 기록해 `--scope all` 결과 제목에 `[unknown]`이 붙는다. 원격 제외 판정(public만 허용)은 v1.6과 같다. 기존 DB는 해당 메모가 다시 색인될 때 반영된다(전체 재색인 불필요).
- v1.8 (2026-10-01, Claude): mcp_server.py v1.3: AIVAULT_REMOTE_EXTRA_IDS 추가(remote 범위에서 특정 registry_id 추가 허용, 기본 빈값). build_index.py v1.6: effective()가 type: inbox 파일의 보안등급 머리말 필드를 반영해 원격 허용 여부 결정. README에 tunnel-client 환경변수 전달 방법 추가.
- v1.7 (2026-10-01, Claude): mcp_server.py v1.2: 조회 범위 선택 추가. `AIVAULT_SCOPE=all`(또는 `--scope all`)이면 remote_allowed 조건 없이 색인된 전체 자료(internal·unknown 포함)를 돌려주고, 결과 제목 앞에 `[internal]` 등 보안등급을 붙인다. 기본값(remote)은 v1.1과 같아 ChatGPT 터널 설정은 바꾸지 않는다. Claude 데스크톱 `claude_desktop_config.json`의 ai-vault env에만 `AIVAULT_SCOPE: all`을 둔다. fetch 메타데이터에 remote_allowed·scope 추가.
- v1.6 (2026-09-22, Claude): build_index.py v1.5: 위키(0 wiki) 페이지 색인. SOURCE_REGISTRY의 type: wiki 항목이 있어야 색인됨. 관리용 노드(index.md, log.md, _index.md)는 제외. 페이지 머리말 classification이 public이 아니면(internal 등) 그 페이지만 원격 제외. 시험용 --registry 옵션 추가. mcp_server.py v1.1: 안내문에 위키 자료 성격 추가.
- v1.5 (2026-09-22, Claude): mcp_server.py v1.0 추가. 도구 search·fetch·search_case, remote_allowed 자료만 제공(끌 수 없음), DB 읽기 전용, 쓰기 도구 없음. stdio(기본)와 streamable HTTP(--http) 지원.
- v1.4 (2026-09-22, Claude): build_index.py v1.4: 색인 대상 폴더에 `0 wiki/Clippings`(기사 수신함) 추가(SCAN_DIRS), 점으로 시작하는 폴더(.obsidian 등)는 건너뜀.
- v1.3 (2026-09-22, Claude): ① search.py v1.2: 2글자 이하 검색어가 항상 0건이던 오류 수정(FTS5 trigram 표의 LIKE → instr). ② build_index.py v1.3: `type: statistics`인 CSV만 decisions 표에 넣음(규정 연혁 취합본 행이 통계로 섞이던 문제). 통계가 아닌 CSV는 판 이름 행(제n호, 시행일)을 머리글로, 조 제목을 조각 제목으로 씀. 날짜로 읽지 못한 의결일 값은 decisions에 넣지 않음. 기존 DB는 `python build_index.py --full`로 다시 만들어야 반영됨.
- 운영 사본: 이 폴더(J:\MCP\ai-vault-mcp)가 실행용이고, J:\AI 자료\Claude outputs\는 같은 스크립트의 보관용 사본이다(AGENTS.md v1.5 2절). 두 곳을 함께 고친다.
- v1.1 (2026-09-21): 의결번호 인식 개선(범위 번호 `0017~0018호`, 전체회의 번호 `2024-24-0116`, 2012~2017 통계의 결합 열, 두 자리 연도 날짜, 띄어쓰기가 섞인 번호). DB 구조가 바뀌었으므로 교체 후 `python build_index.py --full` 필요.
- v1.0 (2026-09-21): 최초 작성.

## 파일

| 파일 | 역할 |
|---|---|
| build_index.py | SOURCE_REGISTRY.yaml에서 `searchable: true`인 자료만 읽어 `data\search.db`를 만든다(원본은 읽기만 함) |
| search.py | search.db 조회(읽기 전용) |
| check_index.py | 의결번호 연결 상태 점검(읽기 전용) |
| mcp_server.py | MCP 서버(읽기 전용). 기본은 원격 허용 자료만, `AIVAULT_SCOPE=all`이면 전체 자료(Claude 데스크톱 로컬 연결용), `--remote-extra-ids`로 승인된 항목 추가. `search`는 `kind`·`registry_id`로 범위 지정 가능(v1.5) |
| data\search.db | 검색 DB (자동 생성) |
| data\index_report.md | 색인 결과 보고서 (자동 생성) |

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

## 검색 범위 좁히기 (mcp_server.py v1.5)

`search(query, limit, kind, registry_id, offset)`에서 `kind`와 `registry_id`는 선택이며, 생략하면 전체를 찾습니다. 회의록(약 6만 조각)·논문(약 3만 조각)에 결과가 묻힐 때 씁니다.

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

- 응답의 `total`은 일치하는 전체 조각 수, `returned`는 이번에 돌려준 수, `truncated`가 true면 더 남아 있다는 뜻입니다. 한 번에 최대 20건이므로 전체가 필요하면 `offset`을 20씩 올려 이어서 조회합니다(v1.6). 결과가 limit보다 적게 나와도 전체라는 보장은 없으니 `total`과 비교합니다.
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


## 색인 요청 방식 (2026-09-29)

- Claude는 검색 DB에 직접 쓰지 않는다. 작업 후 `data\reindex.request` 파일을 만든다.
- 작업 스케줄러 "AI자료 색인"이 5분마다 `run_index_on_request.bat`을 실행한다. 요청 파일이 있으면 지우고 `build_index.py`(증분)를 실행해 결과를 `data\reindex_last.log`에 남긴다.
- 작업 해제: `schtasks /Delete /TN "AI자료 색인" /F`
