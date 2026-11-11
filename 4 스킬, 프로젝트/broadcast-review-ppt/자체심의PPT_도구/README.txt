자체심의 PPT 도구 폴더 (toolkit version: 2026-10-26)

이 폴더를 PC의 고정 위치에 두고, Claude 작업 시 이 폴더(또는 상위 폴더)를 연결하면
broadcast-review-ppt 스킬이 템플릿과 스크립트를 자동으로 찾습니다.

- MBC_자체심의_템플릿_경량.pptx : 원본 템플릿에서 예시 사례(5~14번)와 예시 사진을 뺀 4장짜리 원형
                                  (1 표지, 2 구분, 3 단일 사례, 4 2사례 비교)
                                  원본 14장 템플릿을 그대로 써도 됩니다. 파일명에 '자체심의'와 '템플릿'이 들어가야 검색됩니다.
- extract_report.py : 보고서(HWPX/HWP/DOCX/TXT/MD/PDF) → 사례 JSON + 방송화면 추출
- build_deck.py     : deck_spec.json + 템플릿 → PPTX + 감사 JSON

스크립트는 스킬 본문에도 같은 버전이 들어 있어서, 이 폴더가 없어도 템플릿만 첨부하면 작동합니다.
