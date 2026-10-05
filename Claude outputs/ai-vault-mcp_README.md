# ai-vault-mcp

AI 자료창고(J:\AI 자료)의 검색 DB와, 나중에 붙일 MCP 서버를 두는 폴더입니다. 검색 DB와 읽기 전용 MCP 서버(mcp_server.py v1.4)가 있습니다(색인기 v1.7, 검색기 v1.2).

## 변경 이력

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
| mcp_server.py | MCP 서버(읽기 전용). 기본은 원격 허용 자료만, `AIVAULT_SCOPE=all`이면 전체 자료(Claude 데스크톱 로컬 연결용), `--remote-extra-ids`로 승인된 항목 추가 |
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
