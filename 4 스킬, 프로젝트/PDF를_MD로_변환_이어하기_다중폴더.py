# -*- coding: utf-8 -*-

from pathlib import Path
import pymupdf4llm


def get_target_folders() -> list[Path]:
    while True:
        raw = input("PDF가 들어있는 '상위' 폴더 경로를 입력하세요 (그 안의 모든 하위 폴더를 자동으로 순차 처리합니다): ").strip()
        raw = raw.strip('"').strip("'")

        if not raw:
            print("경로를 입력해주세요.\n")
            continue

        parent = Path(raw)

        if not parent.exists() or not parent.is_dir():
            print(f"존재하지 않거나 폴더가 아닙니다: {parent}\n")
            continue

        subfolders = sorted([p for p in parent.iterdir() if p.is_dir() and p.name != "MD_변환"])

        if not subfolders:
            print(f"'{parent}' 안에 하위 폴더가 없어, 이 폴더 자체를 대상으로 처리합니다.\n")
            return [parent]

        print(f"\n다음 {len(subfolders)}개 폴더를 이 순서대로 처리합니다 (중간에 추가 입력 없음):")
        for sf in subfolders:
            print(f"  - {sf.name}")
        print()

        return subfolders


def convert_folder(source_dir: Path) -> tuple[int, int, int]:
    """단일 폴더의 PDF들을 MD로 변환. (성공, 건너뜀, 실패) 개수 반환."""
    output_dir = source_dir / "MD_변환"
    output_dir.mkdir(exist_ok=True)

    pdf_files = sorted(source_dir.glob("*.pdf"))

    print()
    print("=" * 70)
    print(f"폴더 처리 중: {source_dir}")
    print(f"저장 폴더 : {output_dir}")
    print(f"PDF 파일 수 : {len(pdf_files)}개")
    print("=" * 70)

    success_count = 0
    skip_count = 0
    fail_count = 0

    if not pdf_files:
        print("변환할 PDF 파일이 없습니다.")
        return success_count, skip_count, fail_count

    for number, pdf_path in enumerate(pdf_files, start=1):
        md_path = output_dir / f"{pdf_path.stem}.md"
        temp_path = output_dir / f"{pdf_path.stem}.md.part"

        print()
        print("-" * 70)
        print(f"[{number}/{len(pdf_files)}] {pdf_path.name}")

        if md_path.exists() and md_path.stat().st_size > 0:
            print("건너뜀: 이미 변환된 MD 파일이 있습니다.")
            skip_count += 1
            continue

        if md_path.exists() and md_path.stat().st_size == 0:
            print("주의: 기존 MD 파일이 0바이트이므로 다시 변환합니다.")
            md_path.unlink()

        if temp_path.exists():
            temp_path.unlink()
            print("이전 중단 작업의 임시 파일(.part)을 삭제했습니다.")

        print("변환 중...")

        try:
            markdown = pymupdf4llm.to_markdown(
                str(pdf_path),
                ignore_images=True,
                show_progress=False
            )
            temp_path.write_text(markdown, encoding="utf-8")
            temp_path.replace(md_path)
            print(f"완료: {md_path.name}")
            success_count += 1

        except Exception as error:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            print(f"실패: {pdf_path.name}")
            print(f"오류: {error}")
            fail_count += 1

    return success_count, skip_count, fail_count


def main():
    target_folders = get_target_folders()

    total_success = 0
    total_skip = 0
    total_fail = 0

    print("#" * 70)
    print(f"전체 {len(target_folders)}개 폴더 자동 순차 변환을 시작합니다. (무인 실행 — 추가 입력 없음)")
    print("#" * 70)

    for i, folder in enumerate(target_folders, start=1):
        print()
        print(f">>> ({i}/{len(target_folders)}) 폴더 시작: {folder.name}")
        try:
            s, sk, f = convert_folder(folder)
        except KeyboardInterrupt:
            print("\n사용자 요청으로 중단했습니다. (Ctrl+C)")
            break
        except Exception as error:
            print(f">>> 폴더 처리 중 예상치 못한 오류 발생: {folder.name}")
            print(f"오류: {error}")
            s, sk, f = 0, 0, 0

        total_success += s
        total_skip += sk
        total_fail += f
        print(f">>> ({i}/{len(target_folders)}) 폴더 완료: {folder.name}  (성공 {s} / 건너뜀 {sk} / 실패 {f})")

    print()
    print("=" * 70)
    print("전체 작업 완료")
    print("=" * 70)
    print(f"처리한 폴더 수 : {len(target_folders)}개")
    print(f"새로 변환 성공 : {total_success}개")
    print(f"이미 변환되어 건너뜀 : {total_skip}개")
    print(f"실패 : {total_fail}개")
    print("=" * 70)

    input("\nEnter 키를 누르면 종료합니다.")


if __name__ == "__main__":
    main()
