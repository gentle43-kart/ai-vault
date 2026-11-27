---
name: "broadcast-review-ppt"
description: "방송 모니터 보고서(HWPX·HWP·DOCX·TXT·MD·PDF)를 방송사 자체심의·심의책임자회의용 '자체심의 참고사항' PPTX로 변환할 때 사용. 자체심의 PPT, 지적사항 PPT, 모니터 보고서 PPT 변환 요청에 적용."
---

# 방송 자체심의 PPT 자동화 (toolkit version: 2026-11-19)

모니터 보고서를 사례 단위로 추출하고, 회의용 제목·요약을 작성한 뒤, 지정 템플릿을 복제해 편집 가능한 PPTX와 감사 JSON을 만든다. 추출과 PPT 생성은 스크립트가 하고, 제목·요약 작성과 사실 대조는 Claude가 한다.

## 0. 준비물 찾기

1. **보고서**: 대화 첨부 파일 또는 연결된 PC 폴더의 파일. 원본은 읽기만 하고 덮어쓰지 않는다.
2. **템플릿**(필수): 아래 순서로 찾는다. 템플릿 없이 디자인을 새로 만들지 않는다.
   - ① 이번 대화에 첨부된 `.pptx` 중 템플릿으로 지정된 것
   - ② Claude 프로젝트 파일: 대화가 프로젝트에 연결되어 있으면 `Projects` 도구의 `project_info`로 파일 목록을 확인하고, 이름에 `템플릿`이 들어간 `.pptx`를 `project_read`(`original: true`)로 내려받아 작업 공간에 둔다. 후보가 여럿이면 어느 것을 쓸지 사용자에게 확인한다.
   - ③ PC의 기준 템플릿: `J:\AI 자료\4 스킬, 프로젝트\broadcast-review-ppt\자체심의PPT_도구\MBC_자체심의_템플릿_경량.pptx`(2026.11.18.~19. 수정판: 표지 기관명 줄 추가, 3번 슬라이드 '주요내용', 사진 카드 확대). 이 폴더가 연결되어 있지 않으면 `J:\AI 자료\4 스킬, 프로젝트\broadcast-review-ppt` 폴더 접근을 요청해(`device_request_folder_access`) 가져온다. 그 밖의 연결 폴더에서는 `*자체심의*템플릿*.pptx`를 검색(장치 셸의 `find`)한다
   - ④ 모두 없으면 템플릿 첨부를 요청하고 멈춘다
   - 어느 경로에서 가져온 템플릿을 썼는지 답변에 한 줄로 적는다.
   - 템플릿 계약: 1번 슬라이드=표지, 2번=구분 슬라이드, 3번=단일 사례, 4번=2사례 비교. 원본 전체 템플릿(14장)과 경량 템플릿(4장) 모두 쓸 수 있다.
3. **스크립트**: 템플릿과 같은 폴더에 `extract_report.py`, `build_deck.py`가 있고 둘째 줄 버전이 `2026-11-19`이면 그것을 쓴다. 없거나 버전이 다르면 부록 A·B를 작업 공간의 `tools/`에 그대로 저장해 쓴다(버전이 다르면 사용자에게 알린다).
4. 실행 환경: Python 3, `python-pptx`, `Pillow`, `lxml`(없으면 `pip install --break-system-packages python-pptx`). HWP 입력은 `pyhwp`(스크립트가 자동 설치 시도). 렌더링 검증은 LibreOffice(`soffice`)와 `pdftoppm`. 연결 폴더의 파일도 생성·렌더링은 작업 공간에서 실행하고 결과만 원래 폴더에 기록한다.
5. 다른 형식의 완성본 PPT가 함께 오면 사실 근거로 쓰지 말고 레이아웃·압축 수준 참고용으로만 쓴다.

## 1. 작업 순서

1. **추출**
   `python3 tools/extract_report.py 보고서 -o extracted.json --img-dir report_images`
   - 출력: 사례별 `station, program, date, span, time, related, content, opinion, images, review_warnings`. 제목·요약은 만들지 않는다.
   - HWPX·DOCX는 그림을 문서 순서대로 사례에 배정한다. 바이너리 HWP는 텍스트만 사례에 배정되고 그림은 `unassigned_images`로 나온다: 그림을 직접 열어 보고 배정이 확실할 때만 쓰고, 불확실하면 HWPX 저장본을 요청하거나 이미지 칸을 비운다.
   - HWP 읽기 실패(배포용·암호·보안 문서)면 한글에서 HWPX로 저장해 다시 첨부해 달라고 요청한다. 암호나 보안 정책을 우회하지 않는다.
   - `case_count`가 0이거나 보고서의 사례 수와 다르면 `raw_text`나 원문을 직접 읽고 사례를 다시 나눈다.
   - 추출된 그림은 모두 열어 보고, 해당 사례 화면이 맞는지 확인한다.
2. **deck_spec.json 작성**(2절 스키마, 3절 작성 규칙). 이 단계가 Claude의 핵심 작업이다.
3. **생성**
   `python3 tools/build_deck.py deck_spec.json 템플릿.pptx 출력.pptx`
   - 같은 이름의 `.audit.json`이 함께 생성된다. 슬라이드별 경고는 PPT 슬라이드 노트에도 `[자동 검토]`로 기록된다.
   - 출력 파일명 기본값: `<보고서 파일명>_자체심의_참고자료_YYYYMMDD.pptx`
4. **검증**(생략 금지)
   - 렌더링: `soffice --headless --convert-to pdf 출력.pptx` → `pdftoppm -r 60 -png 출력.pdf s` → 슬라이드 이미지를 모두 열어 글자 넘침·겹침, 사진과 사례의 대응, 표지 문구를 확인한다. 표지 첫 줄이 방송사명으로 바뀌고, 템플릿의 나머지 줄(`자체심의 참고사항`, 작은 글씨 `(방송미디어통신심의위원회 대구사무소)`)이 그대로 남았는지 본다(템플릿 표지가 다른 형식이면 사용자에게 알린다). LibreOffice 렌더링은 글꼴 대체 때문에 실제 PowerPoint와 줄바꿈이 약간 다를 수 있다.
   - 사실 대조: 아래 스니펫으로 프로그램명·방송일시·관련조항이 원문과 일치하는지 확인하고, 불일치는 원문 기준으로 고친다.
   - `분량 과다` 경고가 있으면 요약을 줄여 다시 생성한다.
   ```python
   import json, re
   ex = json.load(open("extracted.json", encoding="utf-8")); sp = json.load(open("deck_spec.json", encoding="utf-8"))
   norm = lambda s: re.sub(r"\s+", "", s or "")
   src = "|".join(norm(str(c.get(k, ""))) for c in ex["cases"] for k in ("program", "date", "time", "span", "related"))
   for s in sp["slides"]:
       for c in ([s] if s.get("type", "case") == "case" else s.get("cases", [])):
           for f in ("program", "broadcast_datetime", "related_provisions"):
               v = c.get(f, "")
               parts = v.split() if f == "broadcast_datetime" else [v]  # 일시는 날짜·시각을 따로, 나머지는 값 전체로 대조
               if v and v != "확인 필요" and not all(norm(t) in src for t in parts):
                   print("원문 불일치 확인:", s.get("title"), f, v)
   ```
5. **전달**: PPTX와 `.audit.json`을 보낸다. 보고서가 연결 폴더에서 왔으면 같은 폴더에 결과를 쓴다(원본·템플릿 덮어쓰기 금지). 답변에는 사례 수, 슬라이드 수, 남은 경고(누락 필드, 법령 확인, 그림 미배정, 분량)만 짧게 적는다.

## 2. deck_spec.json 스키마

```json
{
  "station": "대구MBC",
  "slides": [
    {"type": "section", "title": "방송사고 등", "subtitle": "자료화면 오송출 및 음향 사고 등 기술적/편집적 과실 사례"},
    {"type": "case",
     "title": "자료화면 오송출",
     "program": "대구MBC 뉴스투데이",
     "broadcast_datetime": "2023. 3.23.(목) 07:43경",
     "related_provisions": "제55조의2 (방송사고)",
     "main_violation": "프로농구 관련 보도를 전하던 중, 보도 내용과 무관한 **'지하철 승차권 발급' 화면이 약 16초간 오송출**됨.",
     "caveat": "(해당 자료화면 오송출에 대한 정정 멘트나 사과 등의 고지 없음)",
     "images": ["report_images/001_image1.png"],
     "review_warnings": ["방송일 연도 미기재(확인 필요)"],
     "source_content": "추출본의 content 원문", "source_opinion": "추출본의 opinion 원문"},
    {"type": "pair", "title": "기타 자료화면 오송출 및 음향 사고",
     "cases": [
       {"label": "[보도] 무관한 자료화면 송출", "program": "930 MBC뉴스", "related_provisions": "제55조의2 (방송사고)",
        "broadcast_datetime": "…", "main_violation": "…", "review_warnings": []},
       {"label": "[교양] 무음 및 프로그램 강제 종료", "program": "…", "related_provisions": "…", "main_violation": "…"}
     ]}
  ]
}
```
- `images` 경로는 deck_spec.json 위치 기준 상대경로 또는 절대경로. 최대 3장. 생성기가 템플릿 사진 카드 안에서 가장 작은 그림이 가장 커지는 배치를 자동으로 고른다(16:9 방송화면은 2~3장이면 위아래로 쌓고, 남는 세로 공간은 위아래로 고르게 나눈다).
- `**…**`는 굵게 표시된다(`main_violation`, `caveat`, `label`에서 사용 가능).
- 누락 필드는 생성기가 `확인 필요`로 채우고 경고를 남긴다. 직접 추정해 채우지 않는다.
- `section`의 번호는 자동으로 `1.`, `2.` …가 붙는다(제목이 이미 숫자로 시작하면 그대로 둔다).
- `pair` 레이아웃에는 방송일시 칸과 그림 칸이 없다. 방송일시는 노트에 기록된다.

## 3. 작성 규칙

**표지**: 생성기는 표지 제목 상자에서 글자가 있는 첫 문단(방송사명)만 `station`으로 바꾸고, 나머지 줄(`자체심의 참고사항`, 작은 글씨 `(방송미디어통신심의위원회 대구사무소)`)은 템플릿 문구·서식 그대로 둔다(2026.11.18. 기준 템플릿). 표지 문구를 바꾸려면 스크립트가 아니라 템플릿을 고친다. `station`에는 보고서에 적힌 방송사명만 넣는다. 예전 문구 `모니터 지적사항`, `관련 지적사항`, `(자체심의 참고사항)`은 쓰지 않는다. 방송사명이 불명확하면 `station_guess`와 파일명을 근거로 사용자에게 확인한다.

**사실 필드**(`program`, `broadcast_datetime`, `related_provisions`): 보고서 표기를 그대로 옮긴다. 날짜·요일·시각·`경` 표기를 보존하고, 없는 연도를 만들지 않는다. 방송일과 방송시각이 따로 있으면 `날짜 시각`으로 합친다. 프로그램명 끝의 등급 표기(`(15세 이상)` 등)만 뺄 수 있다. 관련조항이 여러 개면 `, `로 구분한다.

**제목**(`title`): 10~28자로 쟁점을 적는다. 프로그램명을 반복하지 않는다. 템플릿의 기존 제목 수준: `자료화면 오송출`, `자료화면 재사용 및 미고지`, `민감한 금융/개인정보 노출`, `과도한 신상 및 사유 공개`, `공연 관람등급 미고지`, `방송언어`, `법령 준수 위반 (도로교통법)`.

**요약**(`main_violation` + `caveat`):
- `main_violation`: 무엇을 방송했는지 → 어떤 사실·표현·장면이 문제인지 순서로 1~2문장. 90~130자를 목표로 하고, `~함`/`~됨`으로 끝맺는 개조식으로 쓴다. 핵심 문제 구절 1~2곳만 `**굵게**` 처리한다.
- `caveat`: 괄호로 감싼 한 문장. 고지 누락, 오인 가능성, 침해 우려처럼 판단에 필요한 단서만 넣는다. 단서를 빼면 평가가 달라지는 경우에는 반드시 남긴다. 필요 없으면 생략한다.
- 근거는 보고서뿐이다(사용자가 외부 확인을 요청한 경우만 예외). 수치·시간·고유명사·인용문은 원문 그대로 쓴다.
- 모니터 의견의 `위반 소지`, `오인 가능성`, `우려`를 확정된 위반처럼 강화하지 않는다. 의견(판단)과 방송 사실을 섞지 않는다.
- 조항의 법적 적용 범위와 실제 방송·시설·행위 사실을 구분한다(예: "소방기준 미적용"은 법 적용 여부, "스프링클러 미설치"는 시설 사실).
- 템플릿 예시 문체: `'민생회복 소비쿠폰' 관련 보도 중 시민의 **신용카드 번호 16자리, 유효기간, CVC 번호**가 모자이크 처리 없이 화면에 그대로 노출됨.` / `(본인 인증 및 결제가 가능한 개인정보로, 심각한 사생활 및 재산권 침해 우려 있음)`

**구성**:
- 기본은 사례 1건당 슬라이드 1장, 보고서 순서대로 배치한다.
- 구분 슬라이드는 보고서나 사용자가 분류를 제시했을 때만 넣는다. 사례가 많고 성격이 뚜렷이 갈리면 분류안을 제안하고 승인받은 뒤 넣는다.
- `pair`는 두 사례가 모두 짧고(요약 각 90자 이내) 그림이 필요 없을 때만 쓴다.
- 그림은 해당 사례의 방송화면만 쓴다. 장식용 그림을 넣지 않는다. 대응이 불확실하면 비우고 경고에 남긴다. 4장 이상이면 쟁점이 가장 잘 보이는 3장을 고른다. 3장이면 그림마다 작아지므로, 쟁점이 2장으로 드러나면 2장만 쓴다.

**경고**(`review_warnings`): 추출본의 경고를 이어받고, 작성 중 발견한 문제(누락, 그림 대응 불확실, 원문 모호)를 덧붙인다. 경고를 숨기거나 슬라이드 본문에 넣지 않는다.

## 4. 법령·조문 확인

- 기본값은 보고서 인용을 그대로 유지하고 경고만 남기는 것이다. 조 번호를 임의로 고치지 않는다.
- 추출기가 붙이는 경고: 외부 법령(도로교통법·공연법 등) 인용 시 `법령·조문 최신성 확인 필요`, 방송일이 2026.9.29. 이후이면 `2026.9.29. 시행 방송심의 규칙… 조 번호 확인 필요`. 방송심의 관련 규정은 방송미디어통신심의위원회규칙 제8~11호(방송심의·등급분류·광고·상품판매, 2026.9.21. 제정, 9.29. 시행)로 바뀌었고 조 번호도 달라졌으므로, 방송일 기준 적용 규정과 부칙의 경과규정을 함께 확인해야 한다.
- 사용자가 조문 확인을 요청하면 AI 자료창고 위키(ai-vault `search`/`fetch`)를 먼저 검색하고, 필요하면 법령 조회 도구(`search_law` → `get_law_text`)나 웹 검색으로 보완한다. 확인 결과는 경고 문구와 답변에 적고, 슬라이드 수정은 사용자 승인 후 반영한다.

## 5. 다른 템플릿에 맞추기

새 템플릿이면 먼저 도형 이름과 위치를 확인하고 `build_deck.py` 위쪽의 `MAP`(도형 이름)과 `FIT`(폭·최대 줄 수·글꼴 크기)만 고친다. 새 디자인을 덧씌우지 않는다.
```python
from pptx import Presentation
p = Presentation("템플릿.pptx")
for i, s in enumerate(p.slides, 1):
    for sh in s.shapes:
        print(i, repr(sh.name), round(sh.left.pt), round(sh.top.pt), round(sh.width.pt), round(sh.height.pt),
              sh.text_frame.text[:30].replace("\n", "/") if sh.has_text_frame else "")
```

## 6. 하지 않는 일

- 보고서·템플릿 원본을 덮어쓰거나 삭제하지 않는다.
- PPTX를 만들지 못했으면 만들었다고 말하지 않는다. 그 경우에도 `extracted.json`과 작성한 `deck_spec.json`은 전달한다.
- Windows 원클릭 프로그램(HWP_to_PPT_Auto.ps1)은 이 스킬과 별개다. 그 프로그램을 고치거나 유지·보수하는 일은 Claude Code에서 하도록 권한다.

## 부록 A. tools/extract_report.py

```python
#!/usr/bin/env python3
# broadcast-review-ppt toolkit version: 2026-11-19
"""모니터 보고서(HWPX/HWP/DOCX/TXT/MD/PDF)를 사례 단위 JSON으로 추출한다.

출력은 '원자료 추출본'이며 요약·제목은 만들지 않는다(제목·요약은 Claude가 작성).
usage: python3 extract_report.py REPORT -o extracted.json --img-dir images/
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote

PREFIX = r"^\s*(?:[■□●○▪▶◦·\-]|\d{1,2}[.)])*\s*"
# 라벨 뒤에는 공백·콜론·줄끝만 허용한다('의견을 수렴' 같은 본문 문장을 라벨로 오인하지 않도록).
_LABELS = [
    ("ignore", r"심의규정\s*위반사항\s*및\s*특이사항"),
    ("program", r"(?:프로그램\s*(?:명칭|명)|프로그램\s*\(등급\)|프\s*로\s*그\s*램\s*(?:명|\(등급\))?)"),
    ("date", r"방송\s*(?:일자|일시|일)"),
    ("span", r"방송\s*시간"),
    ("time", r"(?:방송\s*시각|시\s*각)"),
    ("related", r"(?:심의\s*규정|심\s*의\s*규\s*정|관련\s*조항|관련\s*규정|위반\s*조항)"),
    ("content", r"방송\s*내용(?:\s*-\s*특이사항)?"),
    ("opinion", r"(?:(?:문제\s*제기\s*및\s*)?의견|검토\s*의견|모니터\s*의견)"),
    ("images", r"방송\s*화면(?:\s*\(필요시\s*첨부\))?"),
    ("ignore", r"(?:프로그램\s*(?:유형|종류|장르|성격|형태)|방송\s*(?:지역|구분|형태|분야|시점)|방\s*송\s*광\s*고|필\s*러|특\s*이\s*사\s*항)"),
    ("station", r"(?:방송사\s*명칭|방송사명|방송사|채널명|채\s*널)"),
]
LABELS = [(k, re.compile(PREFIX + p + r"(?=$|[\s:：])\s*[:：]?\s*(.*)$")) for k, p in _LABELS]
STATION_RE = re.compile(r"(대구\s*MBC|안동\s*MBC|포항\s*MBC|TBC|KBS\s*대구|대구\s*KBS|KBS|MBC|SBS|EBS|대구\s*CBS|CBS|TBN|BBS|PBC|YTN|JTBC|MBN|TV조선|채널A)")
IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def clean(text: str) -> str:
    text = (text or "").replace("\r", "").replace("\t", " ")
    text = re.sub(r"[\x00\x0b\x0c]", " ", text)
    text = re.sub(r"[  　]+", " ", text)
    return text.strip()


# ---------- readers: 모두 [(text, [image_path...]), ...] 블록 목록을 돌려준다 ----------

def read_hwpx(path: Path, img_dir: Path) -> list[tuple[str, list[str]]]:
    from lxml import etree

    blocks: list[tuple[str, list[str]]] = []
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        items: dict[str, str] = {}
        for man in [n for n in names if n.lower().endswith("content.hpf")]:
            root = etree.fromstring(zf.read(man))
            base = str(Path(man).parent)
            for it in root.iter("{*}item"):
                iid, href = it.get("id"), it.get("href")
                if not iid or not href:
                    continue
                href = unquote(href)
                for cand in (href, f"{base}/{href}".lstrip("./")):
                    if cand in names:
                        items[iid] = cand
                        break
        copied: dict[str, str] = {}

        def export(member: str) -> str | None:
            if Path(member).suffix.lower() not in IMG_EXT | {".wmf", ".emf"}:
                return None
            if member not in copied:
                img_dir.mkdir(parents=True, exist_ok=True)
                out = img_dir / f"{len(copied) + 1:03d}_{Path(member).name}"
                out.write_bytes(zf.read(member))
                copied[member] = str(out)
            return copied[member]

        sections = sorted(
            [n for n in names if re.search(r"(^|/)section\d+\.xml$", n, re.I)],
            key=lambda n: int(re.search(r"section(\d+)", n, re.I).group(1)),
        )
        for sec in sections:
            root = etree.fromstring(zf.read(sec))
            for p in root.iter("{*}p"):
                # 이 문단에 직접 속한 텍스트·그림만 취한다(표 안 문단은 따로 순회되므로 중복 방지)
                texts, imgs = [], []
                for node in p.iter("{*}t", "{*}img"):
                    owner = next((a for a in node.iterancestors() if etree.QName(a).localname == "p"), None)
                    if owner is not p:
                        continue
                    if etree.QName(node).localname == "t":
                        texts.append("".join(node.itertext()))
                    else:
                        ref = node.get("binaryItemIDRef") or node.get("binaryItemID") or node.get("idRef")
                        member = items.get(ref) if ref else None
                        if member is None and ref:
                            member = next((n for n in names if Path(n).stem == ref), None)
                        exported = export(member) if member else None
                        if exported and exported not in imgs:
                            imgs.append(exported)
                txt = clean("".join(texts))
                if txt or imgs:
                    blocks.append((txt, imgs))
    return blocks


def read_hwp(path: Path, img_dir: Path) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """바이너리 HWP: 텍스트는 hwp5txt, 그림은 BinData 일괄 추출(사례 매핑 불가)."""
    notes = []
    exe = shutil.which("hwp5txt")
    if not exe:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "pyhwp"], check=False)
        exe = shutil.which("hwp5txt")
    if not exe:
        raise SystemExit("HWP 읽기 실패: pyhwp 설치 불가. 한글에서 HWPX로 저장해 다시 첨부해 달라고 요청할 것.")
    res = subprocess.run([exe, str(path)], capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        raise SystemExit(f"HWP 읽기 실패({res.stderr.strip()[:200]}). 배포용·암호 문서일 수 있음. HWPX 저장본을 요청할 것.")
    blocks = [(clean(line), []) for line in res.stdout.splitlines() if clean(line)]
    try:
        import olefile, zlib

        ole = olefile.OleFileIO(str(path))
        bins = [e for e in ole.listdir() if e and e[0] == "BinData"]
        img_dir.mkdir(parents=True, exist_ok=True)
        for e in bins:
            raw = ole.openstream(e).read()
            for fn in (lambda b: zlib.decompress(b, -15), lambda b: b):
                try:
                    data = fn(raw)
                    break
                except Exception:
                    continue
            (img_dir / e[-1]).write_bytes(data)
        if bins:
            notes.append(f"HWP 원본에서 그림 {len(bins)}개를 추출했으나 사례별 위치는 알 수 없음(unassigned_images). 사례 매핑이 필요하면 HWPX 저장본을 요청하거나 그림을 직접 확인해 배정할 것.")
    except Exception as exc:  # 그림 추출 실패는 치명적이지 않음
        notes.append(f"HWP 그림 추출 실패: {exc}")
    return blocks, notes


def read_docx(path: Path, img_dir: Path) -> list[tuple[str, list[str]]]:
    from lxml import etree

    blocks = []
    with zipfile.ZipFile(path) as zf:
        rels = etree.fromstring(zf.read("word/_rels/document.xml.rels"))
        rmap = {r.get("Id"): "word/" + r.get("Target").lstrip("/").replace("word/", "") for r in rels}
        root = etree.fromstring(zf.read("word/document.xml"))
        n = 0
        for p in root.iter("{*}p"):
            txt = clean("".join(t.text or "" for t in p.iter("{*}t")))
            imgs = []
            for blip in p.iter("{*}blip"):
                rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                member = rmap.get(rid)
                if member and member in zf.namelist():
                    n += 1
                    img_dir.mkdir(parents=True, exist_ok=True)
                    out = img_dir / f"{n:03d}_{Path(member).name}"
                    out.write_bytes(zf.read(member))
                    imgs.append(str(out))
            if txt or imgs:
                blocks.append((txt, imgs))
    return blocks


def read_plain(path: Path) -> list[tuple[str, list[str]]]:
    if path.suffix.lower() == ".pdf":
        text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    else:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    return [(clean(l), []) for l in text.splitlines() if clean(l)]


# ---------- parser ----------

def fix_split_labels(blocks):
    """'심/의/규/정'처럼 한 글자씩 줄바꿈된 라벨을 합친다."""
    out, i = [], 0
    while i < len(blocks):
        merged = False
        for n in (4, 3, 2):
            seg = blocks[i:i + n]
            if len(seg) == n and all(len(t) == 1 and not im for t, im in seg):
                word = "".join(t for t, _ in seg)
                if word in {"심의규정", "특이사항", "프로그램", "방송일시", "관련조항", "방송내용"}:
                    out.append((word, []))
                    i += n
                    merged = True
                    break
        if not merged:
            out.append(blocks[i])
            i += 1
    return out


def new_case(station=""):
    return {"station": station, "program": "", "date": "", "span": "", "time": "", "related": "",
            "content": "", "opinion": "", "images": []}


def parse(blocks):
    cases, cur, active = [], new_case(), None
    for text, imgs in fix_split_labels(blocks):
        hit = None
        for line in [text]:
            for key, pat in LABELS:
                m = pat.match(line)
                if m:
                    hit = (key, m.group(1).strip())
                    break
        if hit:
            key, rest = hit
            if key in {"program", "station"} and cur["program"] and (cur["content"] or cur["opinion"]):
                cases.append(cur)
                cur = new_case(cur["station"])
            active = key
            if key not in {"images", "ignore"}:
                cur[key] = rest
        elif text and active and active not in {"images", "ignore"}:
            if active == "station" and cur["station"]:
                active = None  # 방송사는 한 줄 필드: 값이 이미 있으면 이어지는 줄을 붙이지 않음
            elif not (active == "program" and text == "(등급)"):
                cur[active] = f"{cur[active]}\n{text}".strip()
        for im in imgs:
            if im not in cur["images"]:
                cur["images"].append(im)
    if cur["program"] or cur["content"] or cur["opinion"]:
        cases.append(cur)
    return cases


def warnings_for(c):
    w = []
    for key, label in (("program", "프로그램명"), ("date", "방송일"), ("related", "관련조항"), ("content", "방송내용")):
        if not c[key].strip():
            w.append(f"{label} 누락(확인 필요)")
    if re.search(r"법|시행령|시행규칙", c["related"]):
        w.append("외부 법령 인용: 법령·조문 최신성 확인 필요")
    if re.match(r"^\s*\d{1,2}\s*[./-]\s*\d{1,2}", c["date"]):
        w.append("방송일 연도 미기재(확인 필요)")
    m = re.match(r"^\s*(20\d{2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})", c["date"])
    if m and tuple(map(int, m.groups())) >= (2026, 9, 29) and c["related"].strip():
        w.append("2026.9.29. 시행 방송심의 규칙(방미심위규칙 제8~11호) 적용 시기: 조 번호가 현행 규칙과 맞는지 확인 필요")
    if not c["images"]:
        w.append("방송화면 미추출")
    if len(c["images"]) > 3:
        w.append(f"방송화면 {len(c['images'])}장: 슬라이드에는 최대 3장, 선별 필요")
    if any(Path(p).suffix.lower() in {".wmf", ".emf"} for p in c["images"]):
        w.append("WMF/EMF 그림은 자동 삽입 불가")
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("extracted.json"))
    ap.add_argument("--img-dir", type=Path, default=Path("report_images"))
    a = ap.parse_args()
    ext = a.report.suffix.lower()
    notes, unassigned = [], []
    if ext == ".hwpx":
        blocks = read_hwpx(a.report, a.img_dir)
    elif ext == ".hwp":
        blocks, notes = read_hwp(a.report, a.img_dir)
        unassigned = sorted(str(p) for p in a.img_dir.glob("*")) if a.img_dir.exists() else []
    elif ext == ".docx":
        blocks = read_docx(a.report, a.img_dir)
    elif ext in {".txt", ".md", ".pdf"}:
        blocks = read_plain(a.report)
    else:
        raise SystemExit("지원 형식: HWPX, HWP, DOCX, TXT, MD, PDF")

    cases = parse(blocks)
    full = "\n".join(t for t, _ in blocks)
    m = STATION_RE.search(full[:400]) or STATION_RE.search(a.report.stem)
    guess = re.sub(r"\s+", "", m.group(1)) if m else ""
    for i, c in enumerate(cases, 1):
        c["case_no"] = i
        if not c["station"]:
            c["station"] = guess
        c["review_warnings"] = warnings_for(c)
    payload = {"schema_version": "2.0", "source": str(a.report), "station_guess": guess,
               "case_count": len(cases), "notes": notes, "unassigned_images": unassigned, "cases": cases}
    if not cases:
        payload["notes"].append("'프로그램명/방송내용/의견' 구조를 찾지 못함. raw_text를 직접 읽고 사례를 나눌 것.")
        payload["raw_text"] = full
    a.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"cases={len(cases)} images={sum(len(c['images']) for c in cases)} unassigned={len(unassigned)} -> {a.output}")
    for c in cases:
        print(f"  #{c['case_no']} {c['program'][:30]!r} imgs={len(c['images'])} warn={c['review_warnings']}")


if __name__ == "__main__":
    main()
```

## 부록 B. tools/build_deck.py

```python
#!/usr/bin/env python3
# broadcast-review-ppt toolkit version: 2026-11-19
"""deck_spec.json + 자체심의 템플릿 → 편집 가능한 PPTX와 감사 JSON.

usage: python3 build_deck.py deck_spec.json TEMPLATE.pptx OUT.pptx
템플릿의 원형 슬라이드(표지 1, 구분 2, 단일사례 3, 2사례 4)를 복제해 채우고 원래 슬라이드는 표지만 남긴다.
"""
from __future__ import annotations

import copy
import io
import json
import re
import sys
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Pt

# ---- 템플릿 도형 매핑(다른 템플릿이면 이 부분만 수정) ----
MAP = {
    "cover": {"slide": 1, "title": "직사각형 6"},
    "section": {"slide": 2, "title": "Google Shape;93;p14", "subtitle": "Google Shape;94;p14"},
    "case": {"slide": 3, "title": "Google Shape;112;p15", "program": "Google Shape;107;p15",
             "datetime": "Google Shape;109;p15", "related": "Google Shape;111;p15",
             "summary": "Google Shape;103;p15", "image": "Picture 3",  # 예시 사진(있으면 삭제)
             "image_card": "Google Shape;101;p15",  # 사진 카드 배경: 이 안쪽에 사진 배치
             "image_box": (545, 136, 362, 378)},  # pt, 카드를 못 찾을 때 쓰는 영역
    "pair": {"slide": 4, "title": "Google Shape;131;p16",
             "left": {"label": "Google Shape;123;p16", "program": "Google Shape;127;p16",
                      "related": "Google Shape;128;p16", "summary": "Google Shape;124;p16"},
             "right": {"label": "Google Shape;125;p16", "program": "Google Shape;129;p16",
                       "related": "Google Shape;130;p16", "summary": "Google Shape;126;p16"}},
}
# 텍스트 상자 수용 한계(폭 pt, 최대 줄 수, 기본 글꼴 pt, 줄간격 배수)
FIT = {
    "title": (914, 1, 30, 1.2), "program": (338, 1, 16, 1.2), "datetime": (338, 1, 16, 1.2),
    "related": (338, 2, 16, 1.2), "summary": (454, 6, 18, 1.6),
    "pair_label": (372, 1, 21, 1.2), "pair_program": (328, 1, 16, 1.2), "pair_summary": (355, 6, 18, 1.2),
}
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


# ---------------- 슬라이드 복제·삭제 ----------------
def duplicate(prs, src):
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    rid_map = {}
    for rid, rel in src.part.rels.items():
        if rel.reltype in (RT.SLIDE_LAYOUT, RT.NOTES_SLIDE):
            continue
        if rel.is_external:
            rid_map[rid] = new.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            rid_map[rid] = new.part.relate_to(rel.target_part, rel.reltype)
    src_csld, new_csld = src._element.cSld, new._element.cSld
    bg = src_csld.find("{http://schemas.openxmlformats.org/presentationml/2006/main}bg")
    if bg is not None:
        new_csld.insert(0, copy.deepcopy(bg))
    tree = new.shapes._spTree
    for el in src.shapes._spTree:
        if etree.QName(el).localname in ("nvGrpSpPr", "grpSpPr"):
            continue
        dup = copy.deepcopy(el)
        for node in dup.iter():
            for attr in list(node.attrib):
                if attr.startswith("{%s}" % R_NS) and node.attrib[attr] in rid_map:
                    node.attrib[attr] = rid_map[node.attrib[attr]]
        tree.append(dup)
    return new


def delete_slides(prs, slides):
    targets = {id(s.part) for s in slides}
    lst = prs.slides._sldIdLst
    doomed = [sid for sid in lst if id(prs.part.related_part(sid.rId)) in targets]
    for sid in doomed:
        rid = sid.rId
        lst.remove(sid)
        prs.part.drop_rel(rid)


def shape(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    raise KeyError(f"템플릿 도형 없음: {name} (MAP 수정 필요)")


# ---------------- 텍스트 ----------------
def segments(text):
    """'**굵게**' 표기를 (텍스트, 굵게여부) 목록으로."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, None) for p in parts if p]


def set_text(shp, paragraphs, size=None, keep_bold=True):
    """첫 문단·첫 런 서식을 유지하며 문단 목록으로 교체. paragraphs: [str] ('**굵게**' 허용)."""
    txBody = shp.text_frame._txBody
    ps = txBody.findall(A + "p")
    proto_p = ps[0]
    proto_r = proto_p.find(A + "r")
    for p in ps:
        txBody.remove(p)
    for text in paragraphs:
        p = copy.deepcopy(proto_p)
        for child in list(p):
            if etree.QName(child).localname in ("r", "br", "fld"):
                p.remove(child)
        end = p.find(A + "endParaRPr")
        for seg, bold in segments(text):
            r = copy.deepcopy(proto_r)
            r.find(A + "t").text = seg
            rpr = r.find(A + "rPr")
            if bold is not None:
                rpr.set("b", "1")
            elif not keep_bold:
                rpr.set("b", "0")
            if size:
                rpr.set("sz", str(int(size * 100)))
            if end is not None:
                end.addprevious(r)
            else:
                p.append(r)
        txBody.append(p)


def est_lines(text, width_pt, size_pt):
    plain = re.sub(r"\*\*", "", text)
    total = 0
    for para in plain.split("\n"):
        w = 0.0
        for ch in para:
            if ch == " ":
                w += 0.3
            elif ord(ch) < 128:
                w += 0.58
            else:
                w += 1.0
        total += max(1, -(-int(w * size_pt) // int(width_pt)))
    return total


def fit(kind, paragraphs, warns, label):
    width, max_lines, base, _ = FIT[kind]
    text = "\n".join(paragraphs)
    for size in (base, base - 1, base - 2):
        if est_lines(text, width, size) <= max_lines:
            return None if size == base else size
    warns.append(f"{label}: 분량 과다로 넘칠 가능성(추정 {est_lines(text, width, base - 2)}줄/{max_lines}줄), 요약 축약 필요")
    return base - 2


# ---------------- 그림 ----------------
def prepared_image(path):
    im = Image.open(path)
    im.load()
    if im.mode not in ("RGB", "L"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.convert("RGBA").split()[-1])
        im = bg
    im.thumbnail((1600, 1600))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=88)
    buf.seek(0)
    return buf, im.size


def place_images(slide, paths, box, warns):
    """사진 카드 안에 그림을 최대한 크게 배치한다.
    열 수(1~n)를 바꿔 가며 같은 크기 칸으로 나눠 보고, 가장 작게 나오는 그림이 가장 커지는 배치를 고른다.
    16:9 화면 2~3장이면 보통 위아래 한 줄씩 쌓인다. 남는 세로 공간은 위아래로 고르게 나눈다."""
    left, top, width, height = box
    ok = []
    for p in paths[:3]:
        try:
            ok.append(prepared_image(p))
        except Exception as exc:
            warns.append(f"그림 삽입 실패({Path(p).name}): {exc}")
    if not ok:
        return
    gap, n, best = 6, len(ok), None
    for cols in range(1, n + 1):
        rows = -(-n // cols)
        cw, ch = (width - gap * (cols - 1)) / cols, (height - gap * (rows - 1)) / rows
        sizes = [(iw * min(cw / iw, ch / ih), ih * min(cw / iw, ch / ih)) for _, (iw, ih) in ok]
        score = min(w * h for w, h in sizes)
        if best is None or score > best[0]:
            best = (score, cols, cw, sizes)
    _, cols, cw, sizes = best
    row_h = [max(h for _, h in sizes[r:r + cols]) for r in range(0, n, cols)]
    y = top + (height - sum(row_h) - gap * (len(row_h) - 1)) / 2
    for r, rh in enumerate(row_h):
        for c in range(cols):
            k = r * cols + c
            if k >= n:
                break
            buf, _ = ok[k]
            w, h = sizes[k]
            x = left + c * (cw + gap) + (cw - w) / 2
            slide.shapes.add_picture(buf, Pt(x), Pt(y + (rh - h) / 2), Pt(w), Pt(h))
        y += rh + gap


def set_notes(slide, lines):
    if lines:
        slide.notes_slide.notes_text_frame.text = "\n".join(lines)


# ---------------- 슬라이드 종류별 ----------------
def build_case(prs, proto, s, base_dir):
    m, warns = MAP["case"], list(s.get("review_warnings", []))
    slide = duplicate(prs, proto)
    for key in ("title", "program", "broadcast_datetime", "related_provisions", "main_violation"):
        if not str(s.get(key, "")).strip():
            s[key] = "확인 필요"
            warns.append(f"{key} 누락 → '확인 필요' 표기")
    set_text(shape(slide, m["title"]), [s["title"]], fit("title", [s["title"]], warns, "제목"))
    set_text(shape(slide, m["program"]), [s["program"]], fit("program", [s["program"]], warns, "프로그램명"))
    set_text(shape(slide, m["datetime"]), [s["broadcast_datetime"]], fit("datetime", [s["broadcast_datetime"]], warns, "방송일시"))
    set_text(shape(slide, m["related"]), [s["related_provisions"]], fit("related", [s["related_provisions"]], warns, "관련조항"))
    summary = [s["main_violation"]] + ([s["caveat"]] if s.get("caveat") else [])
    set_text(shape(slide, m["summary"]), summary, fit("summary", summary, warns, "주요 위반내용"), keep_bold=False)
    box = m["image_box"]
    try:
        card = shape(slide, m["image_card"])
        pad = 8
        box = (card.left.pt + pad, card.top.pt + pad, card.width.pt - 2 * pad, card.height.pt - 2 * pad)
    except KeyError:
        pass
    try:
        old = shape(slide, m["image"])
        old._element.getparent().remove(old._element)
    except KeyError:
        pass
    imgs = [str((base_dir / p).resolve()) if not Path(p).is_absolute() else p for p in s.get("images", [])]
    place_images(slide, imgs, box, warns)
    if not imgs:
        warns.append("방송화면 없음(이미지 영역 비움)")
    set_notes(slide, ["[자동 검토]"] + [f"- {w}" for w in warns] if warns else [])
    return slide, warns


def build_pair(prs, proto, s):
    m, warns = MAP["pair"], list(s.get("review_warnings", []))
    slide = duplicate(prs, proto)
    set_text(shape(slide, m["title"]), [s["title"]], fit("title", [s["title"]], warns, "제목"))
    for side, c in zip(("left", "right"), s["cases"]):
        mm = m[side]
        set_text(shape(slide, mm["label"]), [c["label"]], fit("pair_label", [c["label"]], warns, f"{side} 소제목"))
        prog = f"프로그램: {c.get('program') or '확인 필요'}"
        rel = f"관련조항: {c.get('related_provisions') or '확인 필요'}"
        set_text(shape(slide, mm["program"]), [prog], fit("pair_program", [prog], warns, f"{side} 프로그램"))
        set_text(shape(slide, mm["related"]), [rel], fit("pair_program", [rel], warns, f"{side} 관련조항"))
        set_text(shape(slide, mm["summary"]), [c["main_violation"]], fit("pair_summary", [c["main_violation"]], warns, f"{side} 요약"), keep_bold=False)
        if c.get("broadcast_datetime"):
            pass  # 2사례 레이아웃에는 방송일시 칸이 없음 → 노트에 기록
        warns += [f"{side}: {w}" for w in c.get("review_warnings", [])]
    notes = ["[자동 검토]"] + [f"- {w}" for w in warns] if warns else []
    notes += [f"{c['label']} 방송일시: {c.get('broadcast_datetime', '확인 필요')}" for c in s["cases"]]
    set_notes(slide, notes)
    return slide, warns


def main():
    spec_path, tpl, out = map(Path, sys.argv[1:4])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    prs = Presentation(str(tpl))
    originals = list(prs.slides)
    protos = {k: originals[v["slide"] - 1] for k, v in MAP.items() if v["slide"] <= len(originals)}
    cover = protos["cover"]
    station = spec.get("station") or "방송사"
    set_cover_station(shape(cover, MAP["cover"]["title"]), station)

    audit = {"schema_version": "2.0", "template": str(tpl), "output": str(out), "station": station, "slides": []}
    sec_no = 0
    for s in spec["slides"]:
        kind = s.get("type", "case")
        if kind == "section":
            sec_no += 1
            slide = duplicate(prs, protos["section"])
            title = s["title"] if re.match(r"^\d+\.", s["title"]) else f"{sec_no}. {s['title']}"
            set_text(shape(slide, MAP["section"]["title"]), [title])
            set_text(shape(slide, MAP["section"]["subtitle"]), [s.get("subtitle", "")])
            audit["slides"].append({"type": "section", "title": title})
        elif kind == "pair":
            _, w = build_pair(prs, protos["pair"], s)
            audit["slides"].append({"type": "pair", "title": s["title"], "review_warnings": w})
        else:
            _, w = build_case(prs, protos["case"], s, spec_path.parent)
            audit["slides"].append({"type": "case", "title": s.get("title"), "program": s.get("program"),
                                    "broadcast_datetime": s.get("broadcast_datetime"),
                                    "related_provisions": s.get("related_provisions"),
                                    "images": s.get("images", []), "review_warnings": w,
                                    "source_content": s.get("source_content", ""),
                                    "source_opinion": s.get("source_opinion", "")})
    delete_slides(prs, [sl for sl in originals if sl is not cover])
    prs.save(str(out))
    audit["slide_count"] = len(prs.slides)
    audit["warning_count"] = sum(len(x.get("review_warnings", [])) for x in audit["slides"])
    out.with_suffix(".audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {out} slides={audit['slide_count']} warnings={audit['warning_count']}")
    for x in audit["slides"]:
        if x.get("review_warnings"):
            print(f"  [{x['type']}] {x['title']}: {x['review_warnings']}")


def set_cover_station(shp, station):
    """표지: 템플릿의 문단·서식(부제·기관명 줄 등)은 그대로 두고, 글자가 있는 첫 문단(방송사명)만 바꾼다."""
    for p in shp.text_frame.paragraphs:
        if p.runs and p.text.strip():
            p.runs[0].text = station
            for r in p.runs[1:]:
                r._r.getparent().remove(r._r)
            return
    raise KeyError("표지 제목 상자에 방송사명 문단이 없음 (템플릿 확인 필요)")


if __name__ == "__main__":
    main()
```