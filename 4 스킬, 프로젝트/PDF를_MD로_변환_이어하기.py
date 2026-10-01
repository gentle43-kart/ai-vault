# -*- coding: utf-8 -*-

from pathlib import Path
import pymupdf4llm


def get_source_dir() -> Path:
    while True:
        raw_input = input("변환할 폴더 경로를 입력하세요: ").strip()
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


def main():
    source_dir = get_source_dir()
    output_dir = source_dir / "MD_변환"
    output_dir.mkdir(exist_ok=True)

    pdf_files = sorted(source_dir.glob("*.pdf"))

    print()
    print("=" * 70)
    print("PDF → Markdown 변환 (이어하기 지원)")
    print("=" * 70)
    print(f"대상 폴더 : {source_dir}")
    print(f"저장 폴더 : {output_dir}")
    print(f"PDF 파일 수 : {len(pdf_files)}개")
    print("=" * 70)

    if not pdf_files:
        print("변환할 PDF 파일이 없습니다.")
        input("\nEnter 키를 누르면 종료합니다.")
        return

    success_count = 0
    skip_count = 0
    fail_count = 0

    try:
        for number, pdf_path in enumerate(pdf_files, start=1):
            md_path = output_dir / f"{pdf_path.stem}.md"
            temp_path = output_dir / f"{pdf_path.stem}.md.part"

            print()
            print("-" * 70)
            print(f"[{number}/{len(pdf_files)}] {pdf_path.name}")

            # 이미 변환 완료된 MD 파일이 있으면 자동 건너뜀
            if md_path.exists() and md_path.stat().st_size > 0:
                print("건너뜀: 이미 변환된 MD 파일이 있습니다.")
                print(f"MD : {md_path.name}")
                skip_count += 1
                continue

            # 0바이트 MD는 완료본으로 보지 않고 다시 변환
            if md_path.exists() and md_path.stat().st_size == 0:
                print("주의: 기존 MD 파일이 0바이트이므로 다시 변환합니다.")
                md_path.unlink()

            # 이전 중단에서 남은 임시 파일 삭제
            if temp_path.exists():
                temp_path.unlink()
                print("이전 중단 작업의 임시 파일(.part)을 삭제했습니다.")

            print("변환 중...")
            print(f"PDF : {pdf_path.name}")

            try:
                markdown = pymupdf4llm.to_markdown(
                    str(pdf_path),
                    ignore_images=True,
                    show_progress=False
                )

                # 먼저 임시 파일에 저장
                temp_path.write_text(markdown, encoding="utf-8")

                # 정상 저장이 끝난 경우에만 최종 MD 파일로 확정
                temp_path.replace(md_path)

                print(f"완료: {md_path.name}")
                success_count += 1

            except KeyboardInterrupt:
                # Ctrl+C 시 불완전 임시 파일 제거
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

                print()
                print("=" * 70)
                print("사용자 요청으로 변환을 중단했습니다. (Ctrl+C)")
                print("=" * 70)
                print(f"이번 실행에서 완료 : {success_count}개")
                print(f"이미 완료되어 건너뜀 : {skip_count}개")
                print(f"실패 : {fail_count}개")
                print()
                print("이미 완료된 MD 파일은 그대로 유지됩니다.")
                print("나중에 다시 실행하면 완료된 파일은 자동으로 건너뛰고")
                print("아직 완료되지 않은 PDF부터 계속 처리합니다.")
                print("=" * 70)

                input("\nEnter 키를 누르면 종료합니다.")
                return

            except Exception as error:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

                print(f"실패: {pdf_path.name}")
                print(f"오류: {error}")
                fail_count += 1

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("사용자 요청으로 작업을 중단했습니다. (Ctrl+C)")
        print("=" * 70)
        print(f"이번 실행에서 완료 : {success_count}개")
        print(f"이미 완료되어 건너뜀 : {skip_count}개")
        print(f"실패 : {fail_count}개")
        print("=" * 70)

        input("\nEnter 키를 누르면 종료합니다.")
        return

    print()
    print("=" * 70)
    print("전체 작업 완료")
    print("=" * 70)
    print(f"전체 PDF : {len(pdf_files)}개")
    print(f"이번 실행에서 새로 변환 : {success_count}개")
    print(f"이미 변환되어 건너뜀 : {skip_count}개")
    print(f"실패 : {fail_count}개")
    print(f"저장 위치 : {output_dir}")
    print("=" * 70)

    input("\nEnter 키를 누르면 종료합니다.")


if __name__ == "__main__":
    main()
