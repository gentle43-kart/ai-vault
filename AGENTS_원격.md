# AGENTS_원격.md — 원격(HTTP) 관련 규칙 (AGENTS.md 부록)

이 파일은 AGENTS.md에서 옮긴 규칙이며 AGENTS.md와 같은 효력을 가진다(0절 1항). 현재 원격(HTTP) 경로는 연결하지 않는다(사용자 결정 2026-10-05). 원격 경로를 쓰게 되면 아래 규칙을 따른다.

## 0절 3항 (원문)

3. `SOURCE_REGISTRY.yaml`에서 `remote_allowed: false`인 자료는 원격(HTTP) 경로로 제공하지 않는다. 단, MCP 서버의 `AIVAULT_REMOTE_EXTRA_IDS` 환경변수로 관리자가 지정한 `registry_id`는 예외로 제공할 수 있다. 이 예외는 항목마다 개별 승인(③등급)을 받아야 하며, 결과 제목에 보안등급 표시(`[internal]` 등)를 유지한다.
