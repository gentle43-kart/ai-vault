"""FastAPI 웹 화면(localhost 전용). F5는 DB만 읽고, 국회 조회는 POST /api/sync에서만 한다."""
from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db
from app.config import ROOT, load_settings
from app.services import sync_service

APP_DIR = ROOT / "app"
templates = Jinja2Templates(directory=APP_DIR / "templates")


def _auto_sync_loop() -> None:
    while True:
        s = load_settings()
        time.sleep(max(s.sync_interval_minutes, 5) * 60)
        if load_settings().auto_sync:
            sync_service.start_background_sync(load_settings())


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = load_settings()
    conn = db.connect(s.database_path)
    db.init_db(conn)
    conn.close()
    if s.auto_sync:
        threading.Thread(target=_auto_sync_loop, daemon=True).start()
    yield


app = FastAPI(title="국회 관심 법률안 모니터링", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


def _conn():
    s = load_settings()
    conn = db.connect(s.database_path)
    db.init_db(conn)
    return s, conn


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/api/bills")
def api_bills(keyword: str | None = None, status: str | None = Query(None, pattern="^(pending|processed)$"),
              q: str | None = None, date_from: str | None = None, date_to: str | None = None,
              new_only: bool = False, page: int = 1, page_size: int = 20):
    s, conn = _conn()
    try:
        return db.list_bills(conn, keywords=s.keywords, keyword=keyword, status=status, q=q,
                             date_from=date_from, date_to=date_to, new_only=new_only,
                             new_days=s.new_days, page=page, page_size=page_size)
    finally:
        conn.close()


@app.get("/api/bills/{bill_number}")
def api_bill(bill_number: str):
    s, conn = _conn()
    try:
        b = db.get_bill(conn, bill_number, s.new_days)
    finally:
        conn.close()
    if not b:
        raise HTTPException(404, "해당 의안이 DB에 없습니다.")
    return b


@app.post("/api/sync")
def api_sync(days: int | None = Query(None, ge=0, description="최근 N일(없으면 설정값, 0이면 전체)")):
    return sync_service.start_background_sync(load_settings(), days=days)


@app.get("/api/sync/status")
def api_sync_status():
    state = sync_service.current_state()
    if state.get("running"):
        return state
    s, conn = _conn()
    try:
        last = db.last_sync(conn)
        done = db.last_completed_sync(conn)
    finally:
        conn.close()
    if not last:
        return {"running": False, "status": None}
    keys = ("status", "total_found", "related_found", "inserted", "updated", "unchanged", "failed",
            "started_at", "finished_at", "error_message", "warning", "scope")
    out = {"running": last["status"] == "running", **{k: last.get(k) for k in keys}}
    if out["running"]:  # 명령줄에서 실행 중인 조사
        out["label"] = sync_service.PHASE_LABELS.get(last.get("phase") or "", "조사 중...")
    out["last_completed_at"] = done["finished_at"] if done else None
    return out


@app.get("/api/keywords")
def api_keywords():
    return {"keywords": load_settings().keywords}
