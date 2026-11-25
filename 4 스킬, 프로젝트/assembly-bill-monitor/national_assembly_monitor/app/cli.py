"""명령줄 실행(스킬에서 사용).

  python -m app.cli sync                 최신 조사(기본: 최근 7일 제안분) 후 결과 요약
  python -m app.cli sync --days 30       최근 30일 / --all 이면 해당 대수 전체
  python -m app.cli list [--new] ...     저장된 관련 의안 목록
  python -m app.cli show 의안번호         의안 1건 + 제안이유 및 주요내용 원문
  python -m app.cli status               마지막 조사 결과
  python -m app.cli serve [--port 8000]  웹 화면 실행

출력 텍스트 중 국회 원문은 그대로 옮긴다(가공하지 않음).
--out 파일경로 를 주면 UTF-8 파일로 저장한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app import db
from app.config import load_settings
from app.services import sync_service


def _status_label(b: dict) -> str:
    return b.get("proc_result") or "계류(처리 전)"


def _fmt_bill_line(b: dict) -> str:
    new = "[NEW] " if b.get("is_new") else ""
    return (f"{new}{b['bill_number']} | {b['bill_name']} | {b.get('proposer') or '-'} | "
            f"{b.get('propose_date') or '-'} | {_status_label(b)} | 위원회: {b.get('committee') or '-'} | "
            f"키워드: {','.join(b.get('keywords') or [])}")


def _fmt_bill_full(b: dict) -> str:
    lines = [
        f"의안명: {b['bill_name']}",
        f"의안번호: {b['bill_number']}",
        f"제안자: {b.get('proposer') or '-'}",
        f"제안일: {b.get('propose_date') or '-'}",
        f"소관위원회: {b.get('committee') or '-'}",
        f"처리상태: {_status_label(b)}",
        f"관심 키워드: {', '.join(b.get('keywords') or [])}",
        f"국회 상세정보: {b.get('source_url') or '-'}",
        f"최초 발견: {b.get('first_seen_at')}",
        "",
        "■ 제안이유 및 주요내용 (국회 의안정보시스템 원문)",
    ]
    st = b.get("summary_status")
    if st == "ok" and b.get("summary_text"):
        lines.append(b["summary_text"])
    elif st == "failed":
        lines.append("(원문을 가져오지 못했습니다. 다음 조사 때 다시 시도합니다.)")
    else:
        lines.append("국회에서 별도의 제안이유 및 주요내용이 제공되지 않습니다.")
    return "\n".join(lines)


def _emit(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"saved: {out}")
    else:
        sys.stdout.reconfigure(errors="replace")
        print(text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("sync")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--days", type=int, help="제안일 기준 최근 N일만 조사(기본: keywords.yaml의 recent_days)")
    g.add_argument("--all", action="store_true", help="해당 대수 전체 조사(오래 걸림)")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--out")

    lp = sub.add_parser("list")
    lp.add_argument("--keyword")
    lp.add_argument("--new", action="store_true", help="최근 발견(NEW)만")
    lp.add_argument("--status", choices=["pending", "processed"])
    lp.add_argument("--q", help="의안명 검색어")
    lp.add_argument("--from", dest="date_from")
    lp.add_argument("--to", dest="date_to")
    lp.add_argument("--limit", type=int, default=50)
    lp.add_argument("--full", action="store_true", help="원문까지 출력")
    lp.add_argument("--json", action="store_true")
    lp.add_argument("--out")

    shp = sub.add_parser("show")
    shp.add_argument("bill_number")
    shp.add_argument("--json", action="store_true")
    shp.add_argument("--out")

    stp = sub.add_parser("status")
    stp.add_argument("--json", action="store_true")

    sv = sub.add_parser("serve")
    sv.add_argument("--port", type=int, default=8000)

    a = p.parse_args(argv)
    s = load_settings()

    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("app.main:app", host="127.0.0.1", port=a.port)
        return 0

    if a.cmd == "sync":
        def progress(name: str, c: dict) -> None:
            extra = f" {c['detail_done']}/{c['detail_total']}" if "detail_done" in c else ""
            print(f"[{sync_service.PHASE_LABELS.get(name, name)}]{extra}", file=sys.stderr, flush=True)
        r = sync_service.run_sync(s, progress=progress, days=0 if a.all else a.days)
        if a.json:
            _emit(json.dumps(r, ensure_ascii=False, indent=2), a.out)
        else:
            if r["status"] == "already_running":
                text = "이미 다른 조사가 실행 중입니다."
            elif r["status"] == "failed":
                text = f"조사 실패: {r.get('error_message')}"
            else:
                text = "\n".join([
                    f"조사 완료 ({r['finished_at']}) · 조사 범위: {r['scope']}",
                    f"검색 결과 {r['total_found']}건 → 관련 의안 {r['related_found']}건: "
                    f"신규 {r['inserted']} / 변경 {r['updated']} / 변동 없음 {r['unchanged']} / 실패 {r['failed']}",
                    *([f"주의: {r['warning']}"] if r.get("warning") else []),
                    *(["", "신규 의안:"] + [f"  {b['bill_number']} {b['bill_name']}" for b in r["new_bills"]]
                      if r["new_bills"] else []),
                    *(["", "변경된 의안:"] + [f"  {b['bill_number']} {b['bill_name']}" for b in r["updated_bills"]]
                      if r["updated_bills"] else []),
                    *(["", "실패:"] + [f"  {b['bill_number']} {b['bill_name']}: {b['error']}"
                                      for b in r["failed_bills"]] if r["failed_bills"] else []),
                ])
            _emit(text, a.out)
        return 0 if r["status"] == "completed" else 1

    conn = db.connect(s.database_path)
    db.init_db(conn)
    try:
        if a.cmd == "list":
            r = db.list_bills(conn, keywords=s.keywords, keyword=a.keyword, status=a.status, q=a.q,
                              date_from=a.date_from, date_to=a.date_to, new_only=a.new,
                              new_days=s.new_days, page=1, page_size=a.limit, with_text=a.full or a.json)
            if a.json:
                _emit(json.dumps(r, ensure_ascii=False, indent=2), a.out)
            else:
                head = f"관련 의안 {r['total']}건 중 {len(r['items'])}건 (최신 제안일 순)"
                body = [(_fmt_bill_full(b) + "\n" + "-" * 60) if a.full else _fmt_bill_line(b) for b in r["items"]]
                _emit("\n".join([head, *body]), a.out)
        elif a.cmd == "show":
            b = db.get_bill(conn, a.bill_number, s.new_days)
            if not b:
                print(f"DB에 없는 의안번호입니다: {a.bill_number}", file=sys.stderr)
                return 1
            _emit(json.dumps(b, ensure_ascii=False, indent=2) if a.json else _fmt_bill_full(b), a.out)
        elif a.cmd == "status":
            r = db.last_sync(conn)
            if a.json or not r:
                _emit(json.dumps(r, ensure_ascii=False, indent=2), None)
            else:
                _emit(f"마지막 조사: {r['started_at']} ~ {r.get('finished_at') or '-'} [{r['status']}] "
                      f"범위 {r.get('scope') or '-'} / "
                      f"관련 {r['related_found']} / 신규 {r['inserted']} / 변경 {r['updated']} / "
                      f"실패 {r['failed']}" + (f"\n오류: {r['error_message']}" if r.get("error_message") else "")
                      + (f"\n주의: {r['warning']}" if r.get("warning") else ""), None)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
