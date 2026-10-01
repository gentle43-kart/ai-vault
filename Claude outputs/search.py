# -*- coding: utf-8 -*-
"""
AI 자료창고 검색기 v1.2 (2026-09-22) - search.db를 조회한다(읽기 전용).

사용법 (PowerShell):
    python search.py "방송사고"
    python search.py "제55조의2" --id minutes_broadcast --limit 20
    python search.py "공정" --remote-only           # 원격 허용 자료만
    python search.py --case 2026-방송-02-0002        # 의결번호로 회의록·통계 모두 찾기
    python search.py --show 12345                    # 조각 번호로 전문 보기
"""
import argparse
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "data", "search.db")


def connect(db):
    if not os.path.exists(db):
        sys.exit(f"DB가 없습니다: {db}  (먼저 python build_index.py 실행)")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def fts_query(q):
    # 공백으로 나뉜 각 단어를 따옴표로 감싸 AND 검색 (trigram은 3글자 이상 단어만 색인 사용)
    terms = [t for t in q.split() if t]
    long_terms = [t for t in terms if len(t) >= 3]
    short_terms = [t for t in terms if len(t) < 3]
    match = " AND ".join('"' + t.replace('"', '""') + '"' for t in long_terms)
    return match, short_terms


def search(con, q, reg_id=None, remote_only=False, limit=10):
    match, shorts = fts_query(q)
    where, params = [], []
    if match:
        where.append("chunks_fts MATCH ?")
        params.append(match)
    for s in shorts:  # 2글자 이하는 trigram 색인을 쓸 수 없으므로 instr()로 전체를 훑는다(느릴 수 있음)
        # v1.2: 종전의 "chunks_fts.text LIKE ?"는 trigram 표에서 2글자 이하 패턴에 결과를 돌려주지 않았다
        where.append("instr(chunks_fts.text, ?) > 0")
        params.append(s)
    if reg_id:
        where.append("d.registry_id = ?")
        params.append(reg_id)
    if remote_only:
        where.append("d.remote_allowed = 1")
    order = "bm25(chunks_fts)" if match else "c.chunk_id"
    snip = "snippet(chunks_fts, 0, '[', ']', ' … ', 24)" if match else "substr(chunks_fts.text, 1, 160)"
    sql = f"""
      SELECT c.chunk_id, d.path, d.registry_id, c.meeting, c.case_no, c.heading, c.line_start, {snip} AS snip
      FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.rowid
      JOIN documents d ON d.doc_id = c.doc_id
      WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?"""
    params.append(limit)
    return con.execute(sql, params).fetchall()


def by_case(con, case_no):
    """의결번호로 찾기. 회의록의 범위 제목(예: 0017~0018호)에 포함된 경우도 찾는다."""
    from build_index import parse_case
    c = parse_case(case_no)
    if not c:
        sys.exit("의결번호 형식을 인식하지 못했습니다. 예: 2026-방송-02-0003, 제2020-08-0064호")
    _, prefix, na, nb = c
    return con.execute("""
      SELECT c.chunk_id, d.path, d.registry_id, c.meeting, c.case_no, c.heading, c.line_start,
             substr(f.text, 1, 160) AS snip
      FROM chunks c JOIN documents d ON d.doc_id=c.doc_id JOIN chunks_fts f ON f.rowid=c.chunk_id
      WHERE c.case_prefix = ? AND c.num_from <= ? AND c.num_to >= ?
      ORDER BY c.kind DESC, d.path, c.seq""", (prefix, nb, na)).fetchall()


def show(con, cid):
    r = con.execute("""SELECT c.*, d.path, d.registry_id, f.text FROM chunks c
                       JOIN documents d ON d.doc_id=c.doc_id JOIN chunks_fts f ON f.rowid=c.chunk_id
                       WHERE c.chunk_id=?""", (cid,)).fetchone()
    if not r:
        sys.exit("해당 조각이 없습니다.")
    print(f"# 조각 {cid}\n- 파일: {r['path']} (줄 {r['line_start']})\n- 자료: {r['registry_id']}"
          f"\n- 회의: {r['meeting'] or '-'}\n- 의결번호: {r['case_no'] or '-'}\n- 제목: {r['heading'] or '-'}\n")
    print(r["text"])


def main():
    ap = argparse.ArgumentParser(description="AI 자료창고 검색기")
    ap.add_argument("query", nargs="?")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--id", help="SOURCE_REGISTRY id로 범위 제한 (예: minutes_broadcast)")
    ap.add_argument("--remote-only", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--case", help="의결번호로 찾기")
    ap.add_argument("--show", type=int, help="조각 번호로 전문 보기")
    a = ap.parse_args()
    con = connect(a.db)
    if a.show:
        return show(con, a.show)
    if a.case:
        rows = by_case(con, a.case)
    elif a.query:
        rows = search(con, a.query, a.id, a.remote_only, a.limit)
    else:
        ap.print_help()
        return
    if not rows:
        print("검색 결과가 없습니다.")
    for r in rows:
        loc = " / ".join(x for x in (r["meeting"], r["case_no"], r["heading"]) if x)
        print(f"[{r['chunk_id']}] {r['registry_id']} | {r['path']} (줄 {r['line_start']})")
        if loc:
            print(f"    {loc[:150]}")
        print(f"    {(r['snip'] or '').replace(chr(10), ' ')[:300]}\n")


if __name__ == "__main__":
    main()
