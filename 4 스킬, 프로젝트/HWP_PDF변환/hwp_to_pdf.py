"""HWP/HWPX -> PDF 일괄 변환 (한글 자체 PDF 저장 엔진 사용)

사용: py -3.12 hwp_to_pdf.py            (SOURCE -> OUTPUT, 하위 폴더 포함)
      py -3.12 hwp_to_pdf.py --force    (OUTPUT에 같은 이름 PDF가 있어도 다시 변환)
      py -3.12 hwp_to_pdf.py --src <폴더> --dst <폴더>

- 한글을 COM으로 열어 파일마다 '다른 이름으로 저장 -> PDF'를 실행한다.
- 하위 폴더 구조를 OUTPUT에 그대로 만든다.
- 결과는 OUTPUT\\변환로그_날짜.csv 에 남긴다.
"""
import argparse
import csv
import datetime as dt
import os
import pathlib
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
OPEN_OPTIONS = "forceopen:true;suspendpassword:true;versionwarning:false"


def hwp_pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Hwp.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True, encoding="cp949", errors="ignore").stdout
    pids = set()
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[1].isdigit():
            pids.add(int(parts[1]))
    return pids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "SOURCE"))
    ap.add_argument("--dst", default=str(ROOT / "OUTPUT"))
    ap.add_argument("--force", action="store_true", help="이미 있는 PDF도 다시 변환")
    args = ap.parse_args()

    src, dst = pathlib.Path(args.src), pathlib.Path(args.dst)
    src.mkdir(parents=True, exist_ok=True)
    dst.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.rglob("*")
                   if p.is_file() and p.suffix.lower() in (".hwp", ".hwpx") and not p.name.startswith("~"))
    print(f"입력: {src}\n출력: {dst}\n대상: {len(files)}개")

    results = []
    todo = []
    for f in files:
        out = dst / f.relative_to(src).with_suffix(".pdf")
        if out.exists() and not args.force:
            results.append((str(f.relative_to(src)), "건너뜀", "OUTPUT에 같은 이름의 PDF가 이미 있음"))
        else:
            todo.append((f, out))

    if todo:
        import pythoncom
        import win32com.client as win32

        before = hwp_pids()
        pythoncom.CoInitialize()
        hwp = None
        try:
            hwp = win32.Dispatch("HWPFrame.HwpObject")
            # 보안모듈이 등록돼 있으면 파일 접근 승인 창을 건너뛴다(없으면 무시)
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
            except Exception:
                pass
            # 메시지 창 자동 응답(확인)
            try:
                hwp.SetMessageBoxMode(0x00020000)
            except Exception:
                pass
            # 창을 숨기면 문서 열기에서 멈추는 경우가 있어 숨기지 않는다

            for i, (f, out) in enumerate(todo, 1):
                rel = str(f.relative_to(src))
                tmp = None
                t0 = time.time()
                try:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    tmp = out.parent / f"~tmp_{uuid.uuid4().hex}.pdf"
                    if not hwp.Open(str(f), "", OPEN_OPTIONS):
                        raise RuntimeError("한글에서 문서를 열지 못함(배포용·암호·손상 문서 또는 보안 승인 창 문제)")
                    if not hwp.SaveAs(str(tmp), "PDF", "") or not tmp.exists():
                        raise RuntimeError("PDF 저장 실패")
                    hwp.Clear(1)
                    for k in range(10):  # 한글이 파일을 놓을 때까지 대기 후 이름 변경
                        try:
                            os.replace(tmp, out)
                            break
                        except OSError:
                            if k == 9:
                                raise
                            time.sleep(0.5)
                    results.append((rel, "성공", ""))
                    print(f"[{i}/{len(todo)}] 성공 {rel} ({time.time() - t0:.1f}초)")
                except Exception as e:
                    results.append((rel, "실패", str(e)))
                    print(f"[{i}/{len(todo)}] 실패 {rel}: {e}")
                finally:
                    if tmp is not None and tmp.exists():
                        try:
                            tmp.unlink()
                        except OSError:
                            pass
                    try:
                        hwp.Clear(1)
                    except Exception:
                        pass
        except Exception as e:
            done = {r[0] for r in results}
            for f, _ in todo:
                rel = str(f.relative_to(src))
                if rel not in done:
                    results.append((rel, "실패", f"한글 실행 오류: {e}"))
        finally:
            if hwp is not None:
                try:
                    hwp.Quit()
                except Exception:
                    pass
            hwp = None
            pythoncom.CoUninitialize()
            time.sleep(2)
            # 이 스크립트가 띄운 한글만 정리(원래 열려 있던 한글은 건드리지 않음)
            for pid in hwp_pids() - before:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)

    log = dst / f"변환로그_{dt.datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(log, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일명", "결과", "사유"])
        w.writerows(results)

    n = lambda s: sum(1 for r in results if r[1] == s)
    print(f"\n완료: 성공 {n('성공')} / 건너뜀 {n('건너뜀')} / 실패 {n('실패')}\n로그: {log}")
    return 1 if n("실패") else 0


if __name__ == "__main__":
    sys.exit(main())
