---
name: vault-commit
description: AI 자료창고(J:\AI 자료)·J:\MCP\ai-vault-mcp에서 세션을 마치며 커밋하거나, 코워크가 남긴 log.md 항목의 "커밋 대상 파일"을 커밋할 때 사용. 커밋·push 안내 요청에 적용.
---

# 자료창고 커밋 절차 (Claude Code 전용)

정본은 `CLAUDE.md`의 "git 커밋(방식A)" 항목이다. 이 스킬은 그 절차를 따라 하기 위한 체크리스트이며, 규칙이 다르면 `CLAUDE.md`를 따른다.

1. 상태 확인: `git -c core.autocrlf=true -c core.quotepath=false status --porcelain`
2. 대상 정하기
   - 이번 세션에서 고친 파일만 고른다.
   - 코워크 항목은 `0 wiki/log.md`(달이 바뀐 직후면 직전 달 `0 wiki/log/YYYY-MM.md`도)에서 커밋되지 않은 항목을 찾아, 그 "커밋 대상 파일" 목록의 파일만 고른다.
   - 사용자 클리핑·`@Inbox` 새 메모·`@templates`·json·`4 스킬, 프로젝트/` 등 출처가 log.md로 확인되지 않는 파일은 넣지 않고 목록으로 사용자에게 보고한다.
   - `3 source_raw/`는 `.gitignore` 대상이면 제외한다.
3. `git -c core.autocrlf=true add -- <파일들>` (`git add -A`·`.` 금지)
4. 커밋 메시지: 작업 요약 + 끝 줄 `Co-Authored-By: {사용한 모델명} <noreply@anthropic.com>`. 코워크 항목은 log.md의 "커밋 메시지 초안"을 쓴다.
5. 저장소가 둘이다: `J:\AI 자료`(위키·스키마), `J:\MCP\ai-vault-mcp`(스크립트). 바꾼 쪽마다 따로 커밋한다.
6. push는 하지 않는다. 미push 커밋이 한 저장소에 10개 이상이거나 가장 오래된 미push 커밋이 7일을 넘으면 사용자에게 push를 권하고 PowerShell 명령을 단계별로 안내한다(`cd`, `git status -sb`, `git push origin main`).
7. 끝나면 남은 미커밋 파일이 모두 "사용자 파일"인지 보고한다.
