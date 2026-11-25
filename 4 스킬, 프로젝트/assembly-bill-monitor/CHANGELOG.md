# assembly-bill-monitor 변경 이력

새 버전은 맨 위에 적는다.

## 2026-11-25

- 최초 작성. 국회 관심 법률안 모니터링 프로그램(`national_assembly_monitor\`)과 활용 스킬(B안)을 만들었다.
  - 설계 기준: 「국회 관심 법률안 모니터링 시스템 상세 기술설계서」 v2.0(LLM 미사용, 국회 원문 그대로 표시)
  - 의안 목록: 국회 Open API `TVBPMBILL11`(22대, 의안명 부분일치 검색)
  - 제안이유 및 주요내용: Open API에 없어 의안정보시스템 상세 화면 요청(`billInfo.do`)에서 원문을 받음. 나누지 않고 한 칸에 저장(사용자 승인)
  - 웹 화면(FastAPI, `run.bat`), 명령줄(`python -m app.cli`), 테스트 21개
- 프로그램을 `J:\national_assembly_monitor`에서 이 폴더로 옮기고 가상환경을 새로 만들었다(사용자 지시). 시험 조사로 받은 데이터는 사용자 지시로 삭제했다.
- `~/.claude/skills/assembly-bill-monitor/SKILL.md`는 이 폴더 SKILL.md의 사본이다. 정본을 고치면 사본도 같이 바꾼다.
