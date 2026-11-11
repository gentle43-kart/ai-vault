---
name: stats-monthly-update
description: 사용자가 새 월별 통계 파일(△26.01-NN.csv)을 넣었다며 2026년 방송심의 잠정본(2026_잠정.csv, stats_2026_recent)을 갱신해 달라고 할 때 사용. 월별 통계 갱신 요청에 적용.
---

# 2026 통계 잠정본 월별 갱신 (Claude Code 전용)

정본은 `AGENTS.md` 2.1절 ①등급(`AGENTS_절차.md` 2.1)과 `Claude outputs/update_stats_2026.py` 첫머리 설명이다. 규칙이 다르면 그쪽을 따른다.

1. 사용자가 넣은 새 파일을 확인한다: `2 data_csv/통계_csv/방송/쳇지피팅용 병합_csv/△26.01-NN.csv`
2. 점검만 먼저 실행한다(dry-run, 기본값):
   `python "Claude outputs/update_stats_2026.py" "<새 파일 경로>"`
   - 종료 코드 2(현 잠정본의 의결번호가 새 파일에 없음)면 중단하고 사용자에게 보고한다.
   - 월별 행 수, 추가·변경·순번이 바뀐 행 수를 사용자에게 보고한다.
3. 점검이 통과하고 추가·변경이 1행 이상이면 `--apply`로 다시 실행한다. 스크립트가 잠정본 덮어쓰기, `SOURCE_REGISTRY.yaml`의 `stats_2026_recent` `period`·`notes` 갱신(백업, YAML 검증 포함), `log.md` 항목, `reindex.request`를 처리한다. `path`·보안 필드는 바뀌지 않는다.
4. 이전 △ 파일은 지우지 않는다. 위키 페이지의 기존 수치는 다시 계산하지 않는다(`AGENTS_통계기준.md` 7.1절). 재집계는 사용자가 요청할 때와 확정본을 반영할 때만 한다.
5. 끝나면 `data\reindex_last.log`의 `exit=0`을 확인하고(`reindex.failed`가 있으면 `index_failed.txt`부터 확인), `vault-commit` 스킬로 고친 파일만 커밋한다.
