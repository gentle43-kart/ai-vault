"""SQLite 스키마와 저장소(CRUD)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no TEXT NOT NULL UNIQUE,          -- 의안번호
    bill_id TEXT,                          -- 국회 내부 의안 ID(PRC_...)
    bill_name TEXT,
    proposer TEXT,                         -- 예: 홍길동의원 등 10인
    proposer_kind TEXT,                    -- 의원/위원장/정부
    propose_date TEXT,
    committee TEXT,                        -- 소관위원회(CURR_COMMITTEE)
    proc_result TEXT,                      -- 처리결과(PROC_RESULT_CD). 비어 있으면 처리 전
    source_url TEXT,                       -- API가 준 공식 링크(LINK_URL)
    list_data TEXT,                        -- 목록 API 원본 행(JSON)
    source_hash TEXT,
    created_at TEXT NOT NULL,              -- 최초 발견 시각(NEW 판단 기준)
    updated_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bill_official_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no TEXT NOT NULL UNIQUE REFERENCES bills(bill_no),
    summary_text TEXT,                     -- '제안이유 및 주요내용' 원문(가공하지 않음)
    fetch_status TEXT NOT NULL,            -- ok / none(국회 제공 내용 없음) / failed
    source_api TEXT,
    source_hash TEXT,
    error_message TEXT,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bill_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_no TEXT NOT NULL REFERENCES bills(bill_no),
    keyword TEXT NOT NULL,
    UNIQUE(bill_no, keyword)
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,                  -- running / completed / failed / aborted
    phase TEXT,
    total_found INTEGER DEFAULT 0,
    related_found INTEGER DEFAULT 0,
    inserted INTEGER DEFAULT 0,
    updated INTEGER DEFAULT 0,
    unchanged INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    warning TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS api_raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_name TEXT NOT NULL,
    bill_number TEXT,
    response_json TEXT,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bills_propose_date ON bills(propose_date);
CREATE INDEX IF NOT EXISTS idx_bill_keywords_keyword ON bill_keywords(keyword);
"""

STALE_SYNC_MINUTES = 60


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    # 2026-11-25 추가 열: 조사 범위(예: "최근 7일(2026-11-18 이후)")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sync_logs)")}
    if "scope" not in cols:
        conn.execute("ALTER TABLE sync_logs ADD COLUMN scope TEXT")
    conn.commit()


# ---------------------------------------------------------------- bills
def get_bill_row(conn: sqlite3.Connection, bill_no: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM bills WHERE bill_no = ?", (bill_no,)).fetchone()


def upsert_bill(conn: sqlite3.Connection, bill: dict[str, Any], source_hash: str) -> str:
    """'inserted' / 'updated' / 'unchanged'."""
    ts = now_iso()
    cur = get_bill_row(conn, bill["bill_no"])
    cols = ["bill_id", "bill_name", "proposer", "proposer_kind", "propose_date",
            "committee", "proc_result", "source_url", "list_data"]
    values = [bill.get(c) for c in cols]
    if cur is None:
        conn.execute(
            f"INSERT INTO bills (bill_no, {', '.join(cols)}, source_hash, created_at, updated_at, last_seen_at)"
            f" VALUES (?, {', '.join('?' * len(cols))}, ?, ?, ?, ?)",
            [bill["bill_no"], *values, source_hash, ts, ts, ts])
        return "inserted"
    if cur["source_hash"] == source_hash:
        conn.execute("UPDATE bills SET last_seen_at = ? WHERE bill_no = ?", (ts, bill["bill_no"]))
        return "unchanged"
    conn.execute(
        f"UPDATE bills SET {', '.join(c + ' = ?' for c in cols)}, source_hash = ?, updated_at = ?, last_seen_at = ?"
        " WHERE bill_no = ?", [*values, source_hash, ts, ts, bill["bill_no"]])
    return "updated"


def get_content(conn: sqlite3.Connection, bill_no: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM bill_official_content WHERE bill_no = ?", (bill_no,)).fetchone()


def save_content(conn: sqlite3.Connection, bill_no: str, summary_text: str | None, fetch_status: str,
                 source_hash: str | None, error_message: str | None = None,
                 source_api: str = "likms.billInfo") -> None:
    conn.execute(
        """INSERT INTO bill_official_content
               (bill_no, summary_text, fetch_status, source_api, source_hash, error_message, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(bill_no) DO UPDATE SET
               summary_text = excluded.summary_text, fetch_status = excluded.fetch_status,
               source_api = excluded.source_api, source_hash = excluded.source_hash,
               error_message = excluded.error_message, fetched_at = excluded.fetched_at""",
        (bill_no, summary_text, fetch_status, source_api, source_hash, error_message, now_iso()))


def save_keywords(conn: sqlite3.Connection, bill_no: str, keywords: Iterable[str]) -> None:
    conn.execute("DELETE FROM bill_keywords WHERE bill_no = ?", (bill_no,))
    conn.executemany("INSERT OR IGNORE INTO bill_keywords (bill_no, keyword) VALUES (?, ?)",
                     [(bill_no, k) for k in keywords])


def save_raw(conn: sqlite3.Connection, api_name: str, bill_no: str | None, text: str) -> None:
    conn.execute("INSERT INTO api_raw_data (api_name, bill_number, response_json, fetched_at) VALUES (?, ?, ?, ?)",
                 (api_name, bill_no, text, now_iso()))


def _bill_dict(conn: sqlite3.Connection, row: sqlite3.Row, new_days: int, with_text: bool = True) -> dict:
    content = get_content(conn, row["bill_no"])
    kws = [r["keyword"] for r in conn.execute(
        "SELECT keyword FROM bill_keywords WHERE bill_no = ? ORDER BY keyword", (row["bill_no"],))]
    is_new = row["created_at"] >= (datetime.now() - timedelta(days=new_days)).isoformat()
    d = {
        "bill_number": row["bill_no"],
        "bill_id": row["bill_id"],
        "bill_name": row["bill_name"],
        "proposer": row["proposer"],
        "proposer_kind": row["proposer_kind"],
        "propose_date": row["propose_date"],
        "committee": row["committee"] or None,
        "proc_result": row["proc_result"] or None,
        "keywords": kws,
        "source_url": row["source_url"],
        "is_new": is_new,
        "first_seen_at": row["created_at"],
        "updated_at": row["updated_at"],
        "summary_status": content["fetch_status"] if content else None,
    }
    if with_text:
        d["summary_text"] = content["summary_text"] if content else None
    return d


def list_bills(conn: sqlite3.Connection, *, keywords: list[str], keyword: str | None = None,
               status: str | None = None, q: str | None = None, date_from: str | None = None,
               date_to: str | None = None, new_only: bool = False, new_days: int = 7,
               page: int = 1, page_size: int = 20, with_text: bool = True) -> dict:
    """keywords: 현재 설정된 관심 키워드(설정에서 빠진 키워드의 의안은 숨김)."""
    where = ["b.bill_no IN (SELECT bill_no FROM bill_keywords WHERE keyword IN (%s))"
             % ",".join("?" * len(keywords) or ["''"])]
    args: list[Any] = list(keywords)
    if keyword:
        where.append("b.bill_no IN (SELECT bill_no FROM bill_keywords WHERE keyword = ?)")
        args.append(keyword)
    if status == "pending":
        where.append("COALESCE(b.proc_result, '') = ''")
    elif status == "processed":
        where.append("COALESCE(b.proc_result, '') <> ''")
    if q:
        where.append("b.bill_name LIKE ?")
        args.append(f"%{q}%")
    if date_from:
        where.append("b.propose_date >= ?")
        args.append(date_from)
    if date_to:
        where.append("b.propose_date <= ?")
        args.append(date_to)
    if new_only:
        where.append("b.created_at >= ?")
        args.append((datetime.now() - timedelta(days=new_days)).isoformat())
    sql_where = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM bills b WHERE {sql_where}", args).fetchone()[0]
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    rows = conn.execute(
        f"SELECT b.* FROM bills b WHERE {sql_where} ORDER BY b.propose_date DESC, b.bill_no DESC LIMIT ? OFFSET ?",
        [*args, page_size, (page - 1) * page_size]).fetchall()
    return {"items": [_bill_dict(conn, r, new_days, with_text) for r in rows],
            "page": page, "page_size": page_size, "total": total}


def get_bill(conn: sqlite3.Connection, bill_no: str, new_days: int = 7) -> dict | None:
    row = get_bill_row(conn, bill_no)
    return _bill_dict(conn, row, new_days) if row else None


# ---------------------------------------------------------------- sync_logs
def try_start_sync(conn: sqlite3.Connection) -> int | None:
    """실행 중인 조사가 없으면 sync_logs에 running 행을 만들고 id 반환. 있으면 None.
    웹과 명령줄이 동시에 조사하지 않도록 DB로 잠근다."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        stale = (datetime.now() - timedelta(minutes=STALE_SYNC_MINUTES)).isoformat()
        conn.execute("UPDATE sync_logs SET status = 'aborted', finished_at = ?, error_message = '응답 없이 중단됨'"
                     " WHERE status = 'running' AND started_at < ?", (now_iso(), stale))
        if conn.execute("SELECT 1 FROM sync_logs WHERE status = 'running'").fetchone():
            conn.execute("COMMIT")
            return None
        cur = conn.execute("INSERT INTO sync_logs (started_at, status, phase) VALUES (?, 'running', 'starting')",
                           (now_iso(),))
        conn.execute("COMMIT")
        return cur.lastrowid
    except Exception:
        conn.execute("ROLLBACK")
        raise


def update_sync(conn: sqlite3.Connection, sync_id: int, **fields: Any) -> None:
    if not fields:
        return
    conn.execute(f"UPDATE sync_logs SET {', '.join(k + ' = ?' for k in fields)} WHERE id = ?",
                 [*fields.values(), sync_id])
    conn.commit()


def last_sync(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM sync_logs ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def last_completed_sync(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM sync_logs WHERE status = 'completed' ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)
