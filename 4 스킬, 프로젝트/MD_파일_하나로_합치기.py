# -*- coding: utf-8 -*-

import hashlib
import re
from pathlib import Path


def get_source_dir() -> Path:
    while True:
        raw_input_value = input("합칠 MD 파일이 있는 폴더 경로를 입력하세요: ").strip()
        raw_input_value = raw_input_value.strip('"').strip("'")

        if not raw_input_value:
            print("경로를 입력해주세요.\n")
            continue

        path = Path(raw_input_value)

        if not path.exists():
            print(f"존재하지 않는 경로입니다: {path}\n")
            continue

        if not path.is_dir():
            print(f"폴더가 아닙니다: {path}\n")
            continue

        return path


def sort_key(path: Path):
    """'2011년_광고소위_회의록-2_11.md' -> (2011, [2, 11]) 로 연도·분할번호 정렬."""
    name = re.sub(r"^\d{10,}_", "", path.stem)          # 업로드 접두 숫자 제거
    match = re.search(r"(\d{4})\s*년", name) or re.search(r"(19|20)\d{2}", name)
    if not match:
        return (9999, [], name)
    year = int(match.group(1) if match.lastindex else match.group())
    tail = [int(n) for n in re.findall(r"\d+", name[match.end():])]   # -2_11 -> [2, 11]
    return (year, tail, name)


def title(path: Path) -> str:
    return re.sub(r"^\d{10,}_", "", path.stem)


def self_check():
    keys = [sort_key(Path(n)) for n in [
        "1788480788236_2022년_광고소위_회의록.md",
        "1788480788237_2010년_광고소위_회의록.md",
        "1788480788241_2021년_광고소위_회의록-2_11.md",
        "1788480788241_2021년_광고소위_회의록-2_2.md",
    ]]
    assert keys[1] < keys[3] < keys[2] < keys[0], keys   # 2010 < 2021-2_2 < 2021-2_11 < 2022


def main():
    self_check()

    source_dir = get_source_dir()
    output_dir = source_dir / "MD_통합"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{source_dir.name}_통합.md"

    md_files = sorted(source_dir.glob("*.md"), key=sort_key)

    print()
    print("=" * 70)
    print("MD 파일 통합 (연도순 정렬 · 빈 파일/중복 자동 제외)")
    print("=" * 70)
    print(f"대상 폴더 : {source_dir}")
    print(f"저장 폴더 : {output_dir}")
    print(f"MD 파일 수 : {len(md_files)}개")
    print("=" * 70)

    if not md_files:
        print("합칠 MD 파일이 없습니다.")
        input("\nEnter 키를 누르면 종료합니다.")
        return

    parts = []
    seen = {}
    skipped = []

    try:
        for number, md_path in enumerate(md_files, start=1):
            print()
            print("-" * 70)
            print(f"[{number}/{len(md_files)}] {md_path.name}")

            try:
                text = md_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # UTF-8이 아닌 파일은 CP949(한글 윈도우 기본)로 재시도
                text = md_path.read_text(encoding="cp949", errors="replace")
                print("주의: UTF-8이 아니어서 CP949로 읽었습니다.")

            text = text.replace("\r\n", "\n").strip()

            if not text:
                print("건너뜀: 내용이 비어 있는 파일입니다.")
                skipped.append((md_path.name, "빈 파일"))
                continue

            digest = hashlib.md5(text.encode("utf-8")).hexdigest()
            if digest in seen:
                print(f"건너뜀: 내용이 완전히 같은 중복 파일입니다. (= {seen[digest]})")
                skipped.append((md_path.name, f"중복 (= {seen[digest]})"))
                continue

            seen[digest] = md_path.name
            parts.append(
                f"---\n\n# {title(md_path)}\n\n<!-- source: {md_path.name} -->\n\n{text}\n"
            )
            print(f"합침 완료: {len(text):,}자")

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("사용자 요청으로 작업을 중단했습니다. (Ctrl+C)")
        print("=" * 70)
        print("통합 파일은 저장되지 않았습니다. 다시 실행해주세요.")
        print("=" * 70)
        input("\nEnter 키를 누르면 종료합니다.")
        return

    output_path.write_text("\n".join(parts), encoding="utf-8")

    print()
    print("=" * 70)
    print("전체 작업 완료")
    print("=" * 70)
    print(f"전체 MD 파일 : {len(md_files)}개")
    print(f"합쳐진 파일 : {len(parts)}개")
    print(f"제외된 파일 : {len(skipped)}개")
    for name, reason in skipped:
        print(f"    - {name}  ({reason})")
    print(f"저장 파일 : {output_path}")
    print(f"파일 크기 : {output_path.stat().st_size:,} bytes")
    print("=" * 70)

    input("\nEnter 키를 누르면 종료합니다.")


if __name__ == "__main__":
    main()
