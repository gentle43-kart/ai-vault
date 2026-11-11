# Claude outputs

분석·색인·점검 스크립트와 그 설명을 두는 폴더입니다(AGENTS.md 2.1절). 위키 페이지가 아니며 ingest·색인 대상이 아닙니다.

## 색인·검색 서버 (이 폴더에 없음)

검색 DB, 색인기(`build_index.py`), MCP 서버(`mcp_server.py`), 검색기(`search.py`), 점검 스크립트(`check_index.py`, `check_md_quality.py`), `convert_haesul.py`, 그 README의 **실제 버전은 `J:\MCP\ai-vault-mcp`** 에 있습니다. 2026-11-11에 이 폴더의 옛 사본(실제 버전과 동일하거나 더 오래됨)을 삭제했습니다.

## 이 폴더의 주요 스크립트

- `wiki_lint.py` v1.5: 위키 lint(읽기 전용, JSON 출력). `0 wiki/log/` 월별 조각은 형식 점검에서 제외하고 링크 스캔에는 포함. internal 출처가 모두 statistics 유형이고 링크·언급 단서가 없는 페이지는 `internal_suspect` 대신 `internal_aggregate`(확인용 목록)로 출력
- `split_log.py` v1.0: `0 wiki/log.md`의 지난 달 항목을 `0 wiki/log/YYYY-MM.md`로 바이트 그대로 옮김(기본은 점검만, `--apply`로 적용. 매월 첫 항목을 쓰기 전에 실행)
- `maintenance_check.py` v1.0: 정기 점검 A 단계(AGENTS_절차.md 6.8절). 읽기 전용으로 wiki_lint 결과, 수신함 대기·클리핑 새 파일, 새 △ 통계 파일, log 분할 필요, 두 저장소의 미커밋·미push, reindex.failed, 이번 달 B 보고서 유무, 직전 실행 실패·8일 넘는 공백을 점검한다. 결과는 자료창고 밖 `J:\MCP\ai-vault-mcp\data\maintenance\`의 `{날짜}_check.json`·`{날짜}_요약.md`에 쓴다(이 폴더에는 쌓지 않는다). 같은 날 다시 실행하면 덮어쓰며 수치는 같다
- `run_maintenance_check.bat` v1.1: 작업 스케줄러 "AI자료 정기점검"(매주 수요일 09:40)이 실행하는 파일. `maintenance_check.py`를 실행하고 `data\maintenance\run_history.log`에 "시각 종료코드" 한 줄을 붙인다. python 경로는 `run_index_on_request.bat`과 같다. 주석은 ASCII로만 쓴다(cmd가 chcp 전의 한글을 잘못 해석함)
- `stats_articles.py` 등 통계 스크립트: 각 파일 첫머리의 목적·입력·출력·검증값 주석 참조
- `update_stats_2026.py`: `stats_2026_recent` 월별 갱신(`--apply`)
- `schema_backup/`: 스키마 파일 수정 전 백업(AGENTS.md 2.1절)
