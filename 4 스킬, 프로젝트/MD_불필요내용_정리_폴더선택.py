# -*- coding: utf-8 -*-

from pathlib import Path
import csv
import re


# =========================================================
# 정리할 폴더 경로를 사용자에게 입력받기
# =========================================================

def get_source_dir() -> Path:
    while True:
        raw_input = input("정리할 MD 파일이 있는 폴더 경로를 입력하세요: ").strip()

        # 따옴표를 붙여서 붙여넣은 경우 제거
        raw_input = raw_input.strip('"').strip("'")

        if not raw_input:
            print("경로를 입력해주세요.\n")
            continue

        path = Path(raw_input)

        if not path.exists():
            print(f"존재하지 않는 경로입니다: {path}\n")
            continue

        if not path.is_dir():
            print(f"폴더가 아닙니다: {path}\n")
            continue

        return path


# =========================================================
# 정리 규칙
# =========================================================

# 숫자만 있는 줄: 1 ~ 9999
page_number_pattern = re.compile(r"^\s*\d{1,4}\s*$")

# 예: ∙ 90 ∙ / ⋅ 123 ⋅ / · 15 ·
decorated_page_number_pattern = re.compile(
    r"^\s*[∙⋅·•]\s*\d{1,4}\s*[∙⋅·•]\s*$"
)

# 예: 방송심의에 관한 규정 ⋅ 37
page_header_footer_pattern = re.compile(
    r"^\s*.{1,100}?\s+[⋅∙]\s+\d{1,4}\s*$"
)

# 예: -�2�- / �15� / -□12□-
broken_page_marker_pattern = re.compile(
    r"^\s*[-–—]?\s*[�□]\s*\d{1,4}\s*[�□]\s*[-–—]?\s*$"
)

# <u>, </u>, <mark>, </mark>
html_tag_pattern = re.compile(
    r"</?(?:u|mark)\s*>",
    flags=re.IGNORECASE
)

# <br>, <br/>, <br />
br_pattern = re.compile(
    r"<br\s*/?>",
    flags=re.IGNORECASE
)

# 그림 텍스트 변환 주석
picture_comment_pattern = re.compile(
    r"^\s*<!--\s*(?:Start|End)\s+of\s+picture\s+text\s*-->\s*$",
    flags=re.IGNORECASE
)


# =========================================================
# 한 파일 정리
# =========================================================

def clean_markdown(text: str, file_name: str):
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    result_lines = []
    log_rows = []

    for line_number, line in enumerate(text.split("\n"), start=1):
        original = line

        # 1. 그림 텍스트 시작/끝 주석 삭제
        if picture_comment_pattern.fullmatch(line):
            log_rows.append([
                file_name,
                line_number,
                "그림텍스트주석 삭제",
                original,
                ""
            ])
            continue

        # 2. 깨진 페이지 표식 삭제
        if broken_page_marker_pattern.fullmatch(line):
            log_rows.append([
                file_name,
                line_number,
                "깨진 페이지 표식 삭제",
                original,
                ""
            ])
            continue

        # 3. 장식형 페이지 번호 삭제
        if decorated_page_number_pattern.fullmatch(line):
            log_rows.append([
                file_name,
                line_number,
                "장식형 페이지 번호 삭제",
                original,
                ""
            ])
            continue

        # 4. 문서명 + 페이지 번호 형태 삭제
        if page_header_footer_pattern.fullmatch(line):
            log_rows.append([
                file_name,
                line_number,
                "페이지 머리말/꼬리말 삭제",
                original,
                ""
            ])
            continue

        # 5. 숫자만 있는 줄 삭제
        if page_number_pattern.fullmatch(line):
            log_rows.append([
                file_name,
                line_number,
                "단독 페이지 번호 삭제",
                original,
                ""
            ])
            continue

        # 6. <u>, <mark> 태그만 제거하고 내용은 보존
        new_line = html_tag_pattern.sub("", line)

        if new_line != line:
            log_rows.append([
                file_name,
                line_number,
                "HTML 태그 제거",
                line,
                new_line
            ])
            line = new_line

        # 7. <br>은 공백으로 변경
        new_line = br_pattern.sub(" ", line)

        if new_line != line:
            log_rows.append([
                file_name,
                line_number,
                "BR 태그 공백 변환",
                line,
                new_line
            ])
            line = new_line

        # 8. 줄 끝 공백 제거
        line = line.rstrip()

        result_lines.append(line)

    # =====================================================
    # 빈 줄이 너무 많이 연속되는 경우 최대 2줄까지만 유지
    # =====================================================

    final_lines = []
    blank_count = 0

    for line in result_lines:
        if line.strip() == "":
            blank_count += 1

            if blank_count <= 2:
                final_lines.append("")
        else:
            blank_count = 0
            final_lines.append(line)

    cleaned_text = "\n".join(final_lines).rstrip() + "\n"

    return cleaned_text, log_rows


# =========================================================
# 파일 읽기
# =========================================================

def read_markdown(path: Path):
    # 일반적인 한국어 파일 인코딩을 순서대로 시도
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError:
            pass

    raise UnicodeError("지원하는 인코딩으로 파일을 읽을 수 없습니다.")


# =========================================================
# 메인 실행
# =========================================================

source_dir = get_source_dir()

# 정리된 MD 파일 저장 폴더
output_dir = source_dir / "MD_정리"

# 결과 폴더 생성
output_dir.mkdir(exist_ok=True)

# =========================================================
# 대상 MD 파일 찾기
#
# 하위 폴더까지 모두 검색합니다.
# 단, 이전 실행 결과인 MD_정리 폴더 안의 파일은 제외합니다.
# =========================================================

md_files = []

for md_path in source_dir.rglob("*.md"):

    # 출력 폴더 내부에 있는 파일은 대상에서 제외
    try:
        md_path.relative_to(output_dir)
        continue
    except ValueError:
        pass

    if md_path.is_file():
        md_files.append(md_path)

md_files = sorted(md_files)


print()
print("=" * 70)
print("Markdown 불필요 내용 정리")
print("=" * 70)
print(f"대상 폴더 : {source_dir}")
print(f"저장 폴더 : {output_dir}")
print(f"MD 파일 수 : {len(md_files)}개")
print("하위 폴더 : 포함")
print("=" * 70)


# =========================================================
# 처리
# =========================================================

success_count = 0
fail_count = 0
changed_count = 0
all_logs = []


if not md_files:
    print("정리할 MD 파일이 없습니다.")

else:
    for number, md_path in enumerate(md_files, start=1):

        relative_path = md_path.relative_to(source_dir)

        # 원래 하위 폴더 구조 유지
        output_path = output_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print()
        print(f"[{number}/{len(md_files)}] 처리 중")
        print(f"파일 : {relative_path}")

        try:
            original_text, used_encoding = read_markdown(md_path)

            cleaned_text, logs = clean_markdown(
                original_text,
                str(relative_path)
            )

            output_path.write_text(
                cleaned_text,
                encoding="utf-8"
            )

            all_logs.extend(logs)

            normalized_original = original_text.replace(
                "\r\n", "\n"
            ).replace(
                "\r", "\n"
            )

            if cleaned_text != normalized_original:
                changed_count += 1
                print(f"완료: 변경 {len(logs)}건")
            else:
                print("완료: 변경 없음")

            print(f"인코딩: {used_encoding}")

            success_count += 1

        except Exception as error:

            print(f"실패: {relative_path}")
            print(f"오류: {error}")

            fail_count += 1


# =========================================================
# CSV 로그 저장
# =========================================================

log_path = output_dir / "_정리로그.csv"

with log_path.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.writer(file)

    writer.writerow([
        "파일",
        "원본 줄번호",
        "작업",
        "변경 전",
        "변경 후"
    ])

    writer.writerows(all_logs)


# =========================================================
# 작업 요약 저장
# =========================================================

summary_path = output_dir / "_정리요약.txt"

summary_text = f"""MD 불필요 내용 정리 결과

대상 폴더: {source_dir}
저장 폴더: {output_dir}

전체 MD 파일: {len(md_files)}개
성공: {success_count}개
실패: {fail_count}개
내용이 변경된 파일: {changed_count}개
전체 변경 건수: {len(all_logs)}건

정리한 주요 항목
----------------
- 숫자만 있는 페이지 번호
- ∙ 90 ∙ 형태의 페이지 번호
- 문서명 ⋅ 37 형태의 페이지 머리말/꼬리말
- -�2�- 형태의 깨진 페이지 번호
- <u>, <mark> 태그
- <br> 태그
- 그림 텍스트 시작/끝 변환 주석
- 과도하게 연속된 빈 줄

주의
----
본문의 띄어쓰기, 문장 내용, 법조문 번호, 목차, 표 내용은 자동 교정하지 않습니다.
원본 MD 파일은 변경하지 않습니다.
"""

summary_path.write_text(
    summary_text,
    encoding="utf-8-sig"
)


# =========================================================
# 완료 메시지
# =========================================================

print()
print("=" * 70)
print("전체 작업 완료")
print("=" * 70)
print(f"전체 : {len(md_files)}개")
print(f"성공 : {success_count}개")
print(f"실패 : {fail_count}개")
print(f"변경된 파일 : {changed_count}개")
print(f"전체 변경 건수 : {len(all_logs)}건")
print()
print(f"정리본 저장 위치 : {output_dir}")
print(f"로그 파일 : {log_path}")
print(f"요약 파일 : {summary_path}")
print("=" * 70)

input("\nEnter 키를 누르면 종료합니다.")
