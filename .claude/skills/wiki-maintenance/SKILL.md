---
name: wiki-maintenance
description: AI 자료창고 정기 점검(lint)을 하거나, 주간 점검(A) 결과·월간 정비 보고서(B)를 확인하고 승인된 제안을 반영할 때 사용
---

# 자료창고 정기 점검 확인·반영 (Claude Code 전용, C 단계)

정본은 `AGENTS_절차.md` 6.6절(lint)·6.8절(정기 점검·자동화)이다. 규칙이 다르면 그쪽을 따른다. A는 작업 스케줄러 "AI자료 정기점검"(매주 수 09:40, 읽기 전용), B는 claude.ai 예약 작업(매월 첫째 주 수 14:13)이며, 이 스킬은 둘의 결과를 읽고 사용자가 승인한 것만 반영하는 C 단계다.

1. A 최신 요약을 확인한다: `J:\MCP\ai-vault-mcp\data\maintenance\`의 최신 `*_요약.md`. 요약 첫머리의 경고(직전 실행 실패, 8일 넘는 공백)를 먼저 보고한다. `run_history.log`와 `last_run.log`로 원인을 본다.
2. B 보고서를 확인한다: `0 wiki/분석/{날짜} lint 보고.md`(이번 달). 없으면 그 사실을 알린다. 제안 표를 사용자에게 보이고 반영할 번호를 고르게 한다. 고르지 않은 제안은 반영하지 않고 다음 보고서의 미처리 제안으로 둔다.
3. 승인한 범위만 반영한다. 링크·색인·머리말 형식 오류는 바로 고쳐도 되지만, 내용 수정은 사용자 확인 후, 새 페이지 생성·대규모 교차링크·일괄 재작성은 제안한 범위 안에서만 한다(6.6절). 스키마 파일(`AGENTS*.md`, `CLAUDE.md`, `SOURCE_REGISTRY.yaml`)은 2.1절의 등급·백업 절차를 따른다.
4. A·B가 알린 관리 항목을 처리한다.
   - 새 △ 통계 파일 → `stats-monthly-update` 스킬(0단계가 A 요약의 '새 △ 파일'을 대상으로 삼는다)
   - log.md 분할 필요 → `python "Claude outputs/split_log.py"`로 점검한 뒤 문제가 없으면 `--apply`
   - `reindex.failed` 있음 → `data\index_failed.txt`의 원인부터 확인하고 사용자에게 알린 뒤 `reindex.request`를 만든다
   - 미push가 한 저장소에 10개 이상이거나 가장 오래된 것이 7일을 넘음 → `vault-commit`의 push 권고 절차
5. 위키를 고쳤으면 `data\reindex.request`를 만들고(`reindex.failed`가 없을 때), 색인이 돌 때까지 기다린 뒤 `data\reindex_last.log`의 `exit=0`을 확인한다.
6. `0 wiki/log.md` 끝 50줄만 확인해 항목(작성자 모델명 포함)을 붙이고, `vault-commit` 스킬로 커밋한다. B가 남긴 log 항목의 "커밋 대상 파일"과 "커밋 메시지 초안"도 대상이다. push는 하지 않는다.

A의 결과 파일은 자료창고 안(`0 wiki`, `Claude outputs`)에 복사하지 않는다. B는 6.8절의 네 가지(보고서, `분석/_index.md` 한 줄, log 항목, `reindex.request`) 외에는 쓰지 않으므로, B가 다른 파일을 바꾼 흔적이 있으면 반영 전에 사용자에게 보고한다.
