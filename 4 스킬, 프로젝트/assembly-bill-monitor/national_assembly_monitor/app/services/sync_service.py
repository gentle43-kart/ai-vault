"""[최신 조사] 전체 흐름.

키워드 로드 → 의안명 검색(Open API) → 중복 제거 → 신규·변경 의안만 원문 수집(의안정보시스템)
→ 변경 감지 → DB 저장 → sync_logs 기록.
LLM은 어디에서도 호출하지 않는다.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from app import db
from app.config import Settings
from app.services.bill_service import make_content_hash, make_source_hash, merge_bills, normalize_list_row
from app.services.national_assembly import AssemblyApiError, AssemblyAuthError, NationalAssemblyClient
from app.services.search_service import contains_keyword

PHASE_LABELS = {
    "starting": "조사 준비 중...",
    "fetching_list": "국회 의안 목록 조회 중...",
    "filtering": "관련 의안 확인 중...",
    "fetching_detail": "의안 상세정보(제안이유 및 주요내용) 조회 중...",
    "saving": "공식 내용 저장 중...",
    "completed": "완료",
    "failed": "실패",
}

# 웹 화면용 진행 상태(같은 프로세스 안에서만 공유)
_state_lock = threading.Lock()
_state: dict[str, Any] = {"running": False}


def current_state() -> dict[str, Any]:
    with _state_lock:
        return dict(_state)


def _set_state(**kw: Any) -> None:
    with _state_lock:
        _state.update(kw)


def run_sync(settings: Settings, progress: Callable[[str, dict], None] | None = None) -> dict[str, Any]:
    """조사 1회 실행. 이미 실행 중이면 {"status": "already_running"}."""
    conn = db.connect(settings.database_path)
    db.init_db(conn)
    sync_id = db.try_start_sync(conn)
    if sync_id is None:
        conn.close()
        return {"status": "already_running"}

    counts = {"total_found": 0, "related_found": 0, "inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    result: dict[str, Any] = {"sync_id": sync_id, "new_bills": [], "updated_bills": [], "failed_bills": []}
    warning = None if settings.assembly_api_key else "인증키가 없어 샘플 모드(키워드당 최대 5건)로 조회했습니다."

    def phase(name: str, **extra: Any) -> None:
        _set_state(running=True, status=name, label=PHASE_LABELS.get(name, name), **counts, **extra)
        db.update_sync(conn, sync_id, phase=name, **counts)
        if progress:
            progress(name, {**counts, **extra})

    raw_logger = (lambda api, no, text: db.save_raw(conn, api, no, text)) if settings.save_raw_response else None
    client = NationalAssemblyClient(settings, raw_logger=raw_logger)
    _set_state(running=True, started_at=db.now_iso(), finished_at=None, error_message=None)

    try:
        if not settings.keywords:
            raise AssemblyApiError("관심 키워드가 없습니다. config/keywords.yaml을 확인하세요.")

        # 1. 키워드별 의안명 검색
        phase("fetching_list")
        found: list[tuple[str, dict]] = []
        for kw in settings.keywords:
            rows = client.search_bills(kw)
            counts["total_found"] += len(rows)
            # 2. API 부분일치 결과를 다시 한 번 확인
            for row in rows:
                bill = normalize_list_row(row)
                if contains_keyword(bill["bill_name"], kw):
                    found.append((kw, bill))
        phase("filtering")
        bills = merge_bills(found)
        counts["related_found"] = len(bills)

        # 3. 신규·변경 의안만 원문 수집 후 저장
        phase("fetching_detail", detail_done=0, detail_total=len(bills))
        for i, (no, bill) in enumerate(sorted(bills.items(), reverse=True), 1):
            try:
                outcome = _sync_one(conn, client, settings, bill)
            except Exception as e:  # 의안 하나가 실패해도 전체 조사는 계속
                conn.rollback()
                outcome = ("failed", str(e))
            kind = outcome[0]
            if kind == "failed":
                counts["failed"] += 1
                result["failed_bills"].append({"bill_number": no, "bill_name": bill.get("bill_name"),
                                               "error": outcome[1]})
            else:
                counts[kind] += 1
                if outcome[1]:  # 원문 수집 실패(의안 기본정보는 저장됨)
                    counts["failed"] += 1
                    result["failed_bills"].append({"bill_number": no, "bill_name": bill.get("bill_name"),
                                                   "error": outcome[1]})
                if kind == "inserted":
                    result["new_bills"].append({"bill_number": no, "bill_name": bill.get("bill_name")})
                elif kind == "updated":
                    result["updated_bills"].append({"bill_number": no, "bill_name": bill.get("bill_name")})
            if i % 5 == 0 or i == len(bills):
                phase("fetching_detail", detail_done=i, detail_total=len(bills))

        phase("saving")
        finished = db.now_iso()
        db.update_sync(conn, sync_id, status="completed", phase="completed", finished_at=finished,
                       warning=warning, **counts)
        _set_state(running=False, status="completed", label=PHASE_LABELS["completed"], finished_at=finished,
                   warning=warning, **counts)
        result.update(status="completed", warning=warning, finished_at=finished, **counts)
    except Exception as e:
        msg = str(e)
        if isinstance(e, AssemblyAuthError):
            msg += " (.env의 ASSEMBLY_API_KEY를 확인하세요)"
        finished = db.now_iso()
        db.update_sync(conn, sync_id, status="failed", phase="failed", finished_at=finished,
                       error_message=msg, **counts)
        _set_state(running=False, status="failed", label=PHASE_LABELS["failed"], finished_at=finished,
                   error_message=msg, **counts)
        result.update(status="failed", error_message=msg, finished_at=finished, **counts)
    finally:
        conn.close()
    return result


def _sync_one(conn, client: NationalAssemblyClient, settings: Settings, bill: dict) -> tuple[str, str | None]:
    """의안 1건 저장. (inserted|updated|unchanged, 원문 수집 오류 메시지 또는 None)."""
    no = bill["bill_no"]
    existing = db.get_bill_row(conn, no)
    content = db.get_content(conn, no)
    # 목록 정보(상태·위원회 등)만으로 만든 해시: 바뀌었으면 '내용 없음' 의안의 원문을 다시 확인
    list_hash = make_source_hash(bill, None)
    old_list_hash = make_source_hash(dict(existing), None) if existing is not None else None

    need_fetch = (
        content is None
        or content["fetch_status"] == "failed"
        or (content["fetch_status"] == "none" and old_list_hash != list_hash)
    )
    summary_text = content["summary_text"] if content else None
    fetch_error = None
    if need_fetch and bill.get("bill_id"):
        try:
            summary_text = client.get_official_summary(bill["bill_id"])
            fetch_status = "ok" if summary_text else "none"
        except Exception as e:
            fetch_error = f"원문 수집 실패: {e}"
            fetch_status = "failed"
        time.sleep(settings.detail_delay_seconds)
    else:
        fetch_status = content["fetch_status"] if content else "none"

    outcome = db.upsert_bill(conn, bill, make_source_hash(bill, summary_text))
    if need_fetch:
        if fetch_status == "failed" and content is not None and content["summary_text"]:
            pass  # 이전에 받은 원문은 유지
        else:
            db.save_content(conn, no, summary_text, fetch_status, make_content_hash(summary_text), fetch_error)
    db.save_keywords(conn, no, bill["keywords"])
    conn.commit()
    return outcome, fetch_error


def start_background_sync(settings: Settings) -> dict[str, Any]:
    """웹에서 호출: 별도 스레드로 조사 시작."""
    if current_state().get("running"):
        return {"status": "already_running"}
    conn = db.connect(settings.database_path)
    db.init_db(conn)
    running = conn.execute("SELECT 1 FROM sync_logs WHERE status = 'running'").fetchone()
    conn.close()
    if running:
        return {"status": "already_running"}
    _set_state(running=True, status="starting", label=PHASE_LABELS["starting"], error_message=None)

    def worker() -> None:
        try:
            if run_sync(settings).get("status") == "already_running":  # 명령줄 조사와 겹친 경우
                _set_state(running=False, status="already_running", label="다른 조사가 실행 중입니다")
        except Exception as e:
            _set_state(running=False, status="failed", label=PHASE_LABELS["failed"], error_message=str(e))

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "started"}
