# 국회 관심 법률안 모니터링

관심 키워드(기본: 방송·통신·시청각)가 의안명에 들어간 22대 국회 법률안을 모아,
**국회가 제공한 '제안이유 및 주요내용' 원문을 그대로** 저장하고 보여주는 로컬 프로그램이다.
AI 요약·재작성은 하지 않는다.

## 실행

| 용도 | 방법 |
|---|---|
| 웹 화면 | `run.bat` 더블클릭 → 브라우저 `http://localhost:8000` |
| 최신 조사 | 웹 화면의 [최신 조사] 버튼, 또는 `.venv\Scripts\python -m app.cli sync` (기본: 최근 7일 제안분, 약 10초) |
| 기간 바꿔 조사 | `sync --days 30`(최근 30일), `sync --all`(해당 대수 전체, 수 분) |
| 목록 | `.venv\Scripts\python -m app.cli list` (`--new`, `--keyword 방송`, `--status pending`, `--q 방송법`, `--full`, `--json`) |
| 의안 1건 | `.venv\Scripts\python -m app.cli show 2223020` |
| 마지막 조사 결과 | `.venv\Scripts\python -m app.cli status` |

명령줄 출력은 `--out 파일.txt`로 UTF-8 파일에 저장할 수 있다.
F5(새로고침)는 DB만 읽는다. 국회 서버 조회는 [최신 조사] / `sync`에서만 한다.

## 설정

- `.env` — `ASSEMBLY_API_KEY=열린국회정보 인증키` (Git에 올리지 않음)
- `config/keywords.yaml` — 관심 키워드, 국회 대수(age), 기본 조사 범위(`recent_days`, 0이면 전체), NEW 표시 기간, 요청 간격, 자동 조사 여부

키워드를 바꾸면 다음 조사부터 반영된다. 설정에서 뺀 키워드의 의안은 화면에서 숨겨진다(DB에는 남음).

## 데이터 출처 (2026-11-25 실제 응답 확인)

| 데이터 | 출처 | 필드 |
|---|---|---|
| 의안 목록·의안명 검색 | Open API `TVBPMBILL11` (`AGE`, `BILL_NAME` 부분일치) | BILL_NO, BILL_ID, BILL_NAME, PROPOSER, PROPOSER_KIND, PROPOSE_DT, CURR_COMMITTEE, PROC_RESULT_CD, LINK_URL |
| 제안이유 및 주요내용 | 의안정보시스템 상세 화면이 쓰는 요청 `likms.assembly.go.kr/bill/bi/bill/detail/billInfo.do` | `<pre id="prntSummary">` 원문 |

- Open API(BILLRCP·BILLINFODETAIL·BILLINFOPPSR·BILLJUDGE·ALLBILL·TVBPMBILL11) 어디에도 제안이유·주요내용 필드가 없어 의안정보시스템에서 받는다.
  공개 API가 아니라 사이트 내부 요청이므로, 사이트가 개편되면 이 부분만 실패한다(의안 기본정보는 계속 저장되고, 원문은 "가져오지 못함"으로 표시·다음 조사 때 재시도).
- 국회 API는 User-Agent 헤더가 없으면 400을 돌려준다(코드에서 처리).
- 원문은 '제안이유'와 '주요내용'이 한 덩어리로 오며, 의안마다 구분 형식이 달라 나누지 않고 한 칸(`summary_text`)에 그대로 저장한다.
- '처리상태'는 PROC_RESULT_CD 값이다. 비어 있으면 화면에 '계류(처리 전)'로 표시한다.
- 인증키가 없거나 `ASSEMBLY_SAMPLE_MODE=1`이면 샘플 모드(키워드당 최대 5건)로 동작한다.

## 조사 방식

1. 키워드별 의안명 검색 → 의안번호로 중복 제거(키워드는 누적)
   - 기본은 제안일 기준 최근 `recent_days`(7)일. API는 날짜 조건을 받지 않지만(제안일 조건을 넣어도 무시됨) 결과가 제안일 최신순이라(2026-11-25 확인) 기준일 이전 의안이 나오면 거기서 멈춘다.
   - 기간을 제한하면 그 이전에 제안된 의안의 진행 상황(위원회 회부·가결 등)은 갱신되지 않는다. 진행 상황까지 보려면 가끔 `sync --all`을 실행한다.
2. 처음 보는 의안, 또는 원문 수집에 실패했던 의안만 원문 요청(요청 간 0.5초 대기)
3. 목록 정보+원문으로 SHA-256 해시를 만들어 신규/변경/변동 없음 판단
4. 실패한 의안은 건너뛰고 계속 진행, `sync_logs`에 결과 기록
5. 웹·명령줄 동시 실행은 DB 잠금으로 막는다(이미 실행 중이면 `already_running`)

전체 조사(`--all`)는 관련 의안 수백 건의 원문을 받으므로 처음에는 수 분 걸린다. 이후에는 새 의안만 받는다.

## 구조

```
app/config.py                  .env, keywords.yaml 로드
app/services/national_assembly.py  국회 Open API + 의안정보시스템 원문 수집(재시도 2초·5초)
app/services/search_service.py     키워드 매칭
app/services/bill_service.py       응답 정규화, 중복 제거, 해시
app/services/sync_service.py       조사 전체 흐름
app/db.py                      SQLite 스키마·저장소
app/main.py                    FastAPI (GET /, /api/bills, /api/bills/{no}, POST /api/sync, GET /api/sync/status, /api/keywords)
app/cli.py                     명령줄(스킬용)
app/templates, app/static      화면(원문은 textContent로만 표시 → XSS 방지)
scripts/dev_serve_sample.py    개발용: 샘플 모드 + data/dev_sample.db로 웹 실행
tests/                         pytest (네트워크 없이 실행)
```

## 테스트

```
.venv\Scripts\python -m pytest -q
```
