---
name: assembly-bill-monitor
description: "국회에 발의된 방송·통신·시청각 관련 법률안을 조사하고, 국회가 제공한 '제안이유 및 주요내용' 원문을 그대로 보여줄 때 사용. '국회 방송 법안 확인해줘', '새로 발의된 방송 관련 법률안 있어?', '관심 법률안 최신 조사', '의안번호 2223020 내용 보여줘', '방송법 개정안 목록', '법안 모니터링 화면 열어줘' 같은 요청에 적용. 국회 원문은 고쳐 쓰거나 요약하지 않는다."
---

# 국회 관심 법률안 모니터링

정본 폴더: `J:\AI 자료\4 스킬, 프로젝트\assembly-bill-monitor` (SKILL.md·CHANGELOG.md 정본. 이 파일은 `~/.claude/skills`에 둔 사본이다)
프로그램 폴더: `J:\AI 자료\4 스킬, 프로젝트\assembly-bill-monitor\national_assembly_monitor` (설명: 그 폴더의 README.md)
관심 키워드는 `config\keywords.yaml`(기본: 방송·통신·시청각), 인증키는 `.env`의 `ASSEMBLY_API_KEY`. 키 값은 읽거나 출력하지 않는다.

## 원칙 (가장 중요)
- 이 도구의 목적은 **국회가 쓴 문장을 그대로 보여주는 것**이다. `제안이유 및 주요내용`은 파일에서 읽은 그대로 옮긴다. 줄이거나, 다듬거나, 요약하거나, 해석을 섞지 않는다.
- 원문이 길면 전부 옮기거나, 의안명·번호·링크만 보여주고 "원문은 `show`로 볼 수 있다"고 안내한다. 일부만 옮길 때는 생략했다고 밝힌다.
- 사용자가 직접 요약이나 분석을 요청하면 해도 된다. 다만 그때는 "Claude가 작성한 요약이며 국회 공식 문서가 아님"을 첫 줄에 밝히고, 원문과 섞지 않는다.
- 처리상태가 비어 있는 의안은 '계류(처리 전)'로 표시된다. 국회 데이터에 없는 정보(통과 전망, 발의 배경 등)를 지어내지 않는다.

## 실행 방법
모든 명령은 프로그램 폴더에서 실행한다(경로에 공백·쉼표가 있으니 따옴표로 감싼다). 한글이 깨지지 않도록 **결과는 `--out`으로 UTF-8 파일에 저장한 뒤 Read로 읽는다.** 임시 파일은 `data\_*.txt`(Git 제외 대상)를 쓴다.

```powershell
cd "J:\AI 자료\4 스킬, 프로젝트\assembly-bill-monitor\national_assembly_monitor"
.\.venv\Scripts\python -m app.cli sync --out data\_sync.txt          # 최신 조사(국회 서버 조회)
.\.venv\Scripts\python -m app.cli list --new --out data\_list.txt     # 최근 발견(NEW) 목록
.\.venv\Scripts\python -m app.cli list --keyword 방송 --limit 30 --out data\_list.txt
.\.venv\Scripts\python -m app.cli list --q 방송법 --status pending --out data\_list.txt
.\.venv\Scripts\python -m app.cli show 2223020 --out data\_show.txt   # 1건 + 원문
.\.venv\Scripts\python -m app.cli status                              # 마지막 조사 결과
```

`list` 옵션: `--new`(NEW만), `--keyword`, `--status pending|processed`, `--q 의안명검색어`, `--from/--to YYYY-MM-DD`(제안일), `--limit`, `--full`(원문 포함), `--json`.

## 요청별 처리
1. **"새 법안 있어? / 최신 조사"** → `sync`를 실행한다(첫 조사는 수 분 걸리므로 백그라운드로 돌린다). 결과 파일에서 신규·변경·실패 건수와 신규 의안 목록을 표로 보고한다. 그다음 신규 의안의 원문을 볼지 묻는다.
2. **"목록 보여줘"** → `list`로 조회해 의안번호·의안명·제안자·제안일·상태·키워드를 표로 보여준다. 국회 상세정보 링크는 `show` 결과에 있다.
3. **"○○ 의안 내용"** → `show`로 조회해 기본정보와 `■ 제안이유 및 주요내용` 원문을 코드블록 없이 그대로 옮긴다. 마지막에 국회 상세정보 링크를 붙인다.
4. **"화면 열어줘"** → `run.bat`을 안내하거나 `.\.venv\Scripts\python -m app.cli serve`를 백그라운드로 실행하고 `http://localhost:8000`을 알려준다.
5. **키워드 추가/삭제** → `config\keywords.yaml`의 `keywords:` 목록을 사용자 확인 후 수정하고, 다음 조사부터 반영된다고 알린다.

## 오류 대응
- `ERROR-290` / "인증키 오류" → `.env`의 `ASSEMBLY_API_KEY`가 잘못됨. 사용자에게 열린국회정보(open.assembly.go.kr) 마이페이지의 키를 다시 넣어 달라고 안내한다(키를 채팅에 붙여넣게 하지 않는다).
- "샘플 모드" 경고 → 인증키가 비어 있어 키워드당 5건만 조회된 것. 위와 같이 안내한다.
- "원문 수집 실패"가 많음 → 국회 의안정보시스템 개편 가능성. 의안 기본정보는 저장됐다고 알리고, `app\services\national_assembly.py`의 `get_official_summary` 점검이 필요하다고 보고한다(사용자 지시 없이 코드 수정하지 않는다).
- "이미 다른 조사가 실행 중" → 웹 화면이나 다른 명령의 조사가 끝난 뒤 다시 실행한다.
