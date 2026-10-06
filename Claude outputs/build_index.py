# -*- coding: utf-8 -*-
"""
AI 자료창고 검색 DB(search.db) 색인기  v1.11 (2026-10-06)

v1.11: 색인 요청·실패 처리(보고서 3번, 설계안 작업 3).
      종료 코드: 0=성공, 1=실패 파일 1건 이상 또는 치명적 오류, 2=다른 색인이 실행 중이라 건너뜀(DB를 건드리지 않음).
      data/index_failed.txt에 실패 파일과 오류를 적고(실패 0건이면 지움), index_report.md 머리에 시작·완료 시각과
      성공(추가·갱신)·실패 건수를 적는다. 실패한 파일은 추가·갱신 건수에서 뺀다.
      단일 실행 잠금: DB 폴더의 index.lock에 Windows 파일 잠금(msvcrt.locking)을 건다. 프로세스가 죽으면 운영체제가
      잠금을 풀므로 남은 잠금 파일 때문에 막히지 않는다(잠금 파일은 지우지 않는다).
      실패한 파일은 DB에 이전 판이 남고 mtime이 달라 다음 실행에서 자동으로 다시 시도된다.

v1.10: 보안 머리말 판정(보고서 11번). effective()가 위키·수신함 머리말을 정규식이 아닌 YAML로 읽고(read_frontmatter),
      classification·보안등급 값을 public|internal|unknown으로 검증한다. 머리말 YAML이 깨졌거나 닫히지 않았거나
      허용 값이 아니면 원격에서 제외하고(fail-closed) classification을 unknown으로 기록한다. 머리말이 아예 없는 위키 페이지와
      classification 필드가 없는 위키 페이지는 종전처럼 레지스트리 값을 따른다. 정상 머리말의 판정 결과는 v1.9와 같다.
      조각 내용은 바뀌지 않으므로 PARSER_VERSION은 올리지 않는다(분류 변경은 증분 판정이 메타데이터 갱신으로 반영).

v1.9: 증분 판정 보완(보고서 6번). documents에 parser_version·policy_hash·struct_hash를 저장한다.
      파일(mtime·size)이 같아도 파서 버전(PARSER_VERSION), period_use·case_namespace·type이 바뀌면 다시 색인하고,
      보안등급·layer·원격 허용·registry_id만 바뀌면 조각은 두고 documents 행만 고친다(메타데이터 갱신).
      기존 DB는 컬럼을 자동으로 추가하며, 값이 없는 옛 행은 DB에 저장된 값으로 이전 해시를 복원해 비교한다(재색인 없음).
      파서 동작(조각 나누기·의결번호·CSV 해석)을 바꾸면 PARSER_VERSION을 올려야 전체가 다시 색인된다.

v1.8: 색인 성공 후 PRAGMA wal_checkpoint(TRUNCATE)로 search.db-wal을 비우고 결과를 보고서에 적는다
      (다른 연결이 DB를 열고 있으면 보류될 수 있으며, 보류되어도 오류로 보지 않는다).
      --full은 search.db와 함께 남은 -wal·-shm 파일도 지운다(이전 DB의 WAL이 새 DB에 적용되는 것을 막음).
v1.7: 수신함 머리말 '보안등급:'이 비어 있을 때 다음 줄(예: status: 대기)을 등급으로 읽던 오류 수정.
      보안등급이 비어 있거나 없으면 classification을 unknown으로 기록한다(원격 제외 판정은 v1.6과 같음).
v1.6: type: inbox 파일은 머리말 '보안등급'이 public일 때만 원격 허용(internal·unknown·공란은 제외).

v1.5: 위키(0 wiki) 페이지 색인. SOURCE_REGISTRY의 type: wiki 항목에 해당하는 파일은
      관리용 노드(index.md, log.md, _index.md)를 빼고 색인하며, 페이지 머리말에
      classification: internal 이 있으면 그 페이지만 원격 제공에서 뺀다(AGENTS.md 8절).

- J:\\AI 자료\\SOURCE_REGISTRY.yaml 을 읽어 searchable: true 인 자료만 색인한다.
- Markdown/TXT: 제목(#)·안건(■ 제...호) 단위로 조각을 나누어 FTS5(trigram)에 넣는다.
- CSV: 행 1개 = 조각 1개. type: statistics 자료만 의결번호·의결일·방송사 등을 decisions 테이블에 따로 저장한다.
- 그 밖의 CSV(예: 규정 연혁 취합본)는 판 이름 행을 머리글로 쓰고, 조 제목을 조각 제목으로 붙인다(v1.3).
- 원본 파일은 읽기만 한다. DB는 이 스크립트가 있는 폴더의 data\\search.db 에 만든다.
- 두 번째 실행부터는 바뀐 파일만 다시 색인한다(--full 로 전체 재색인).

사용법 (PowerShell):
    pip install pyyaml          # 최초 1회
    python build_index.py
    python build_index.py --full
    python build_index.py --vault "J:\\AI 자료"
"""
import argparse
import csv
import hashlib
import io
import os
import re
import sqlite3
import sys
import time
try:
    import msvcrt   # Windows 전용(단일 실행 잠금). 없으면 잠금 없이 실행한다
except ImportError:
    msvcrt = None
from datetime import date, datetime

try:
    import yaml
except ImportError:
    sys.exit("PyYAML이 필요합니다. PowerShell에서 'pip install pyyaml'을 실행한 뒤 다시 시도하세요.")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VAULT = r"J:\AI 자료"
DEFAULT_DB = os.path.join(HERE, "data", "search.db")
# 색인 대상 최상위 폴더. 0 wiki/@clippings(2026-09-30 이전 Clippings·_clippings)는 위키가 아닌 원자료 수신함(AGENTS.md 2절, v1.4 추가)
SCAN_DIRS = ("1 documents_md", "2 data_csv", "0 wiki")   # v1.5: 0 wiki 전체(@clippings 포함). 대상 여부는 레지스트리가 정한다
WIKI_ADMIN = {"index.md", "log.md", "_index.md"}          # 위키 관리용 노드(AGENTS.md 3.3)는 색인하지 않는다
SECURITY_VALUES = ("public", "internal", "unknown")   # v1.10: 머리말 보안등급 허용 값
TEXT_EXT = {".md", ".txt"}
CSV_EXT = {".csv"}
PARSER_VERSION = "1.9"    # 조각 나누기·의결번호·CSV 해석을 바꿀 때 올린다(올리면 다음 증분 색인에서 전체 재색인)
MAX_CHUNK = 1800          # 조각 최대 글자 수
MIN_CHUNK = 200           # 이보다 짧은 조각은 다음 조각과 합친다

# 의결번호: 2026-방송-02-0003 / 제2020-08-0064호 / 2012-방송-02-003 / 2024-24-0116∼ 0118
CASE_RE = re.compile(
    r"(?<!\d)(\d{4})\s?-\s?(?:([가-힣]+)\s?-\s?)?(\d{1,2})\s?-\s?(\d{3,4})(?!\d)\s*호?"
    r"(?:\s*[~∼～]\s*(?:제\s*)?(?:\d{4}-(?:[가-힣]+-)?\d{1,2}-)?(\d{3,4})\s*호?)?")
STRUCT_HEAD_RE = re.compile(r"^(?:\d{1,2}\s*\.|[가-하]\s*\.|제\s*\d+\s*차)")
MEETING_RE = re.compile(r"^#\s+(.*(?:회의록|회의발언내용).*)$")
CASE_HEAD_RE = re.compile(r"^#{1,6}\s*■\s*(.+)$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")


# ─────────────────────────── 레지스트리 ───────────────────────────
def norm(p):
    return p.replace("\\", "/").strip("/")


class Registry:
    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.defaults = data.get("defaults", {}) or {}
        self.entries = []
        for s in data.get("sources", []):
            e = dict(self.defaults)
            e.update(s)
            raw = s["path"]
            e["_is_dir"] = raw.endswith("/")
            e["_path"] = norm(raw)
            # 규칙 1: 원격 허용은 public + 사용자 확인일 때만
            e["remote_allowed"] = bool(
                e.get("remote_allowed")
                and e.get("classification") == "public"
                and e.get("classification_confirmed") is True
            )
            self.entries.append(e)

    def match(self, rel):
        """파일 단위 항목 우선, 그다음 가장 긴 폴더 경로."""
        rel = norm(rel)
        best, best_len = None, -1
        for e in self.entries:
            if not e["_is_dir"]:
                if rel == e["_path"]:
                    return e
                continue
            p = e["_path"]
            if rel.startswith(p + "/") and len(p) > best_len:
                best, best_len = e, len(p)
        return best


def parse_period(s):
    """'2026.07~2026.08' -> (date(2026,7,1), date(2026,8,31))"""
    if not s:
        return None
    m = re.match(r"\s*(\d{4})\.(\d{1,2})\s*~\s*(\d{4})\.(\d{1,2})", str(s))
    if not m:
        return None
    y1, m1, y2, m2 = map(int, m.groups())
    start = date(y1, m1, 1)
    end = date(y2 + (m2 == 12), (m2 % 12) + 1, 1)
    end = date.fromordinal(end.toordinal() - 1)
    return start, end


def parse_date(s):
    if not s:
        return None
    s = str(s)
    m = re.search(r"(?<!\d)(\d{4})\s*[-./]\s*(\d{1,2})\s*[-./]\s*(\d{1,2})", s)
    if not m:  # '12. 2. 1.' 처럼 연도가 두 자리인 경우
        m2 = re.search(r"(?<![\d-])(\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})(?!\d)", s)
        if not m2:
            return None
        g = (2000 + int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    else:
        g = tuple(map(int, m.groups()))
    try:
        return date(*g)
    except ValueError:
        return None


# ─────────────────────────── 파일 읽기 ───────────────────────────
def read_text(path):
    b = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", errors="replace"), "utf-8(replace)"


def parse_case(s):
    """문자열에서 첫 의결번호(범위 포함)를 찾아 (표시용 번호, 접두부, 시작번호, 끝번호)를 돌려준다."""
    m = CASE_RE.search(s or "")
    if not m:
        return None
    y, sec, nn, a, b = m.groups()
    prefix = f"{y}-{sec + '-' if sec else ''}{int(nn):02d}"
    na = int(a)
    nb = int(b) if b and int(b) >= na else na
    label = f"{prefix}-{na:04d}" + (f"~{nb:04d}" if nb != na else "")
    return label, prefix, na, nb


def norm_case(s):
    c = parse_case(s)
    return c[0] if c else None


# ─────────────────────────── Markdown 조각내기 ───────────────────────────
def chunk_markdown(text):
    """(meeting, case, heading, line_start, text) 목록. case = parse_case() 결과 또는 None"""
    lines = text.splitlines()
    chunks = []
    meeting, case, heading = "", None, ""
    buf, buf_start = [], 1

    def flush():
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            # 너무 긴 조각은 문단 경계에서 자른다
            while len(body) > MAX_CHUNK:
                cut = body.rfind("\n", 0, MAX_CHUNK)
                if cut < MAX_CHUNK // 2:
                    cut = MAX_CHUNK
                chunks.append([meeting, case, heading, buf_start, body[:cut].strip()])
                body = body[cut:].strip()
            if body:
                chunks.append([meeting, case, heading, buf_start, body])
        buf = []

    def chasu(t):
        m = re.search(r"제\s*(\d+)\s*차", t or "")
        return m.group(1) if m else None

    for i, line in enumerate(lines, 1):
        h = HEAD_RE.match(line)
        title = h.group(2).strip() if h else ""
        if not h:
            # '- 가. 방송심의에관한건 ... (2024-24-0116∼0118)' 처럼 목록으로 변환된 안건 제목도 경계로 본다
            t = line.lstrip("-*• \t")
            if STRUCT_HEAD_RE.match(t) and parse_case(t) and len(t) < 200:
                title = t
        if title:
            flush()
            buf_start = i
            is_h1_minutes = h is not None and h.group(1) == "#" and title.endswith("회의록")
            is_speech = re.search(r"회의\s*발언\s*내용", title) is not None
            if is_h1_minutes or is_speech:
                # '# 2026년 제1차 …회의록' 다음의 '# 제 1 차 …회의발언내용'은 같은 회의로 본다
                if not (is_speech and meeting and chasu(meeting) == chasu(title)):
                    meeting = title
                case = None
            ch = CASE_HEAD_RE.match(line)
            if ch:                              # ■ 제2019-방송-02-0019호<...>
                case = parse_case(ch.group(1)) or case
            elif STRUCT_HEAD_RE.match(title):   # 가. / 5. 같은 구조 제목: 범위 번호가 있으면 적용, 없으면 연결 끊기
                case = parse_case(title)
            # 그 밖의 제목(○ 위원명, ( 의견진술자 입장 ), 변환 과정에서 생긴 가짜 제목)은 직전 안건 유지
            heading = title
            buf.append(line)
            continue
        buf.append(line)
    flush()

    # 짧은 조각은 같은 안건·같은 회의 안에서 다음 조각과 합친다
    merged = []
    for c in chunks:
        if merged and len(merged[-1][4]) < MIN_CHUNK and merged[-1][0] == c[0] and merged[-1][1] == c[1]:
            merged[-1][4] = merged[-1][4] + "\n" + c[4]
        else:
            merged.append(c)
    return merged


# ─────────────────────────── CSV ───────────────────────────
HEADER_KEYS = ("의결번호", "의결일", "방송사", "구분")
COLMAP = {
    "case_no": ("의결번호", "구분", "의결일/ 의결번호"),
    "decision_date": ("의결일", "회차/의결일자"),
    "broadcaster": ("방송사",),
    "channel": ("채널명",),
    "program": ("프로그램명",),
    "articles": ("관련조항",),
    "result": ("심의결과", "심의의결 내용"),
}


def find_col(header, keys):
    for k in keys:
        for i, h in enumerate(header):
            if h and h.replace("\n", "").strip().startswith(k):
                return i
    return None


_last_header = {}


def read_csv_rows(path, text):
    rows = list(csv.reader(io.StringIO(text)))
    hidx = None
    for i, r in enumerate(rows[:15]):
        hits = sum(1 for c in r if any(c.strip().startswith(k) for k in HEADER_KEYS))
        if hits >= 2:
            hidx = i
            break
    group = re.sub(r"_part\d+", "", os.path.basename(path))
    key = (os.path.dirname(path), group)
    if hidx is None:
        header = _last_header.get(key) or [f"col{i+1}" for i in range(max(len(r) for r in rows) if rows else 0)]
        data = rows
        header_note = "이전 part의 머리글 사용" if key in _last_header else "머리글 없음"
    else:
        header = [h.replace("\n", " ").strip() for h in rows[hidx]]
        _last_header[key] = header
        data = rows[hidx + 1:]
        header_note = ""
    return header, data, header_note


ARTICLE_RE = re.compile(r"제\s*\d+\s*조(?:\s*의\s*\d+)?\s*\([^)]{1,40}\)")
EDITION_RE = re.compile(r"제\s*(\d+)\s*호")
EFFECTIVE_RE = re.compile(r"시행\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.")


def index_generic_csv(con, doc_id, text):
    """통계가 아닌 CSV. 앞 10행 중 '제n호'가 두 칸 이상 있는 행을 판 이름 머리글로 쓴다.
    조 제목(제n조(...))이 나오면 조각 제목으로 삼고, 다음 조 제목까지 이어 붙인다."""
    rows = list(csv.reader(io.StringIO(text)))
    hidx, header = None, None
    for i, r in enumerate(rows[:10]):
        if sum(1 for c in r if EDITION_RE.search(c)) >= 2:
            hidx = i
            header = []
            for j, c in enumerate(r):
                e, t = EDITION_RE.search(c), EFFECTIVE_RE.search(c)
                header.append((f"제{e.group(1)}호" if e else f"col{j+1}")
                              + (f"(시행 {t.group(1)}.{int(t.group(2))}.{int(t.group(3))}.)" if t else ""))
            break
    if header is None:
        header = rows[0] if rows else []
        hidx = 0
    note = "" if EDITION_RE.search(" ".join(header)) else "판 이름 머리글을 찾지 못해 첫 행을 머리글로 사용"
    article, n = "", 0
    for seq, row in enumerate(rows[hidx + 1:], hidx + 2):
        cells = [c.replace("\xa0", " ").strip() for c in row]
        if not any(cells):
            continue
        first = next((c for c in cells if c), "")
        m = ARTICLE_RE.match(first)
        if m:
            article = re.sub(r"\s+", "", m.group(0))
        elif re.match(r"제\s*\d+\s*(장|절)", first):
            article = re.sub(r"\s+", " ", first)[:40]
        body = "\n".join(f"{header[i] if i < len(header) else f'col{i+1}'}: {c}" for i, c in enumerate(cells) if c)
        insert_chunk(con, doc_id, n, "csv_row", "", None, article, seq, body)
        n += 1
    return n, note


# ─────────────────────────── DB ───────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS documents(
  doc_id INTEGER PRIMARY KEY,
  path TEXT UNIQUE, registry_id TEXT, type TEXT, layer TEXT,
  classification TEXT, remote_allowed INTEGER,
  mtime REAL, size INTEGER, sha1 TEXT, encoding TEXT,
  n_chunks INTEGER, note TEXT, indexed_at TEXT,
  parser_version TEXT, policy_hash TEXT, struct_hash TEXT);
CREATE TABLE IF NOT EXISTS chunks(
  chunk_id INTEGER PRIMARY KEY,
  doc_id INTEGER, seq INTEGER, kind TEXT,
  meeting TEXT, case_no TEXT, case_prefix TEXT, num_from INTEGER, num_to INTEGER,
  heading TEXT, line_start INTEGER);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS ix_chunks_case ON chunks(case_prefix, num_from, num_to);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  text, heading, tokenize='trigram');
CREATE TABLE IF NOT EXISTS decisions(
  chunk_id INTEGER PRIMARY KEY, doc_id INTEGER,
  case_no TEXT, case_prefix TEXT, case_num INTEGER, decision_date TEXT, broadcaster TEXT, channel TEXT,
  program TEXT, articles TEXT, result TEXT);
CREATE INDEX IF NOT EXISTS ix_dec_case ON decisions(case_prefix, case_num);
CREATE INDEX IF NOT EXISTS ix_dec_date ON decisions(decision_date);
"""


def check_sqlite():
    v = tuple(map(int, sqlite3.sqlite_version.split(".")))
    if v < (3, 34, 0):
        sys.exit(f"SQLite {sqlite3.sqlite_version}은 trigram 검색을 지원하지 않습니다(3.34 이상 필요). Python을 업데이트하세요.")


def policy_hash(cls, typ, layer, period_use, ns, ra):
    """공개 조건·분류 값의 지문. 바뀌면 documents 행을 갱신해야 한다."""
    s = "\x1f".join("" if v is None else str(v) for v in (cls, typ, layer, period_use, ns, int(ra)))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def struct_hash(typ, period_use, ns):
    """조각 내용을 바꾸는 설정의 지문. 바뀌면 파일을 다시 색인해야 한다(type은 CSV 해석 방식을 정한다)."""
    s = "\x1f".join("" if v is None else str(v) for v in (typ, period_use, ns))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def migrate_documents(con):
    """v1.9: 기존 DB의 documents에 증분 판정용 컬럼을 추가한다(이미 있으면 아무것도 하지 않음)."""
    have = {r[1] for r in con.execute("PRAGMA table_info(documents)")}
    for c in ("parser_version", "policy_hash", "struct_hash"):
        if c not in have:
            con.execute(f"ALTER TABLE documents ADD COLUMN {c} TEXT")
    con.commit()


def delete_doc(con, doc_id):
    ids = [r[0] for r in con.execute("SELECT chunk_id FROM chunks WHERE doc_id=?", (doc_id,))]
    con.executemany("DELETE FROM chunks_fts WHERE rowid=?", [(i,) for i in ids])
    con.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    con.execute("DELETE FROM decisions WHERE doc_id=?", (doc_id,))
    con.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))


def insert_chunk(con, doc_id, seq, kind, meeting, case, heading, line_start, text, ns=None):
    label, prefix, na, nb = case if case else (None, None, None, None)
    if ns and prefix:  # 다른 기관(방통위 등)의 같은 형식 번호와 섞이지 않도록 접두부에 이름공간을 붙인다
        prefix, label = f"{ns}:{prefix}", f"{ns}:{label}"
    cur = con.execute(
        "INSERT INTO chunks(doc_id,seq,kind,meeting,case_no,case_prefix,num_from,num_to,heading,line_start)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (doc_id, seq, kind, meeting, label, prefix, na, nb, heading, line_start))
    cid = cur.lastrowid
    con.execute("INSERT INTO chunks_fts(rowid,text,heading) VALUES(?,?,?)", (cid, text, heading or ""))
    return cid


def read_frontmatter(path):
    """머리말(--- 사이)을 YAML로 읽는다. (dict, 오류문자열|None). 머리말이 없으면 ({}, None).
    머리말이 시작됐는데 닫히지 않았거나 YAML이 깨졌거나 매핑이 아니면 오류 문자열을 돌려준다."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            head = f.read(65536)
    except OSError as e:
        return {}, f"읽기 실패: {e}"
    head = head.replace("\r\n", "\n")
    if not head.startswith("---"):
        return {}, None
    m = re.match(r"---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", head, re.S)
    if not m:
        return {}, "머리말이 닫히지 않음"
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return {}, f"YAML 오류: {str(e).splitlines()[0] if str(e) else e}"
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return {}, "머리말이 매핑이 아님"
    return data, None


def effective(vault, rel, entry):
    """페이지 단위 보정(v1.5/v1.6/v1.7/v1.10).
    위키(type: wiki): 머리말 classification: internal 이 레지스트리보다 우선한다.
    수신함(type: inbox): 머리말 '보안등급'이 internal·unknown이거나 비어 있으면 원격 제외(AGENTS.md 6.3).
    v1.10: 머리말을 정규식이 아닌 YAML로 읽고 값은 public|internal|unknown만 허용한다.
      머리말을 읽지 못하거나(YAML 오류·닫히지 않음) 허용 값이 아니면 원격에서 제외하고(fail-closed) classification은 unknown으로 기록한다.
    돌려주는 값: (classification, remote_allowed)"""
    cls, ra = entry.get("classification"), bool(entry["remote_allowed"])
    entry_type = entry.get("type")
    if entry_type in ("wiki", "inbox"):
        fm, err = read_frontmatter(os.path.join(vault, rel))
        if err:
            return "unknown", False
        if entry_type == "wiki":
            if "classification" in fm:
                v = fm["classification"]
                v = "" if v is None else str(v).strip()
                if v not in SECURITY_VALUES:
                    return "unknown", False
                if v != "public":
                    return v, False      # internal·unknown은 원격 제외
            # 필드가 없으면 레지스트리 값 유지
        else:  # inbox: 머리말 '보안등급' 필드 기준
            v = fm.get("보안등급")
            v = "" if v is None else str(v).strip()
            if v == "public":
                pass    # public이면 레지스트리 값(ra) 유지
            elif v in ("", "unknown"):
                cls, ra = "unknown", False   # 공란·필드 없음은 unknown으로 표시(v1.7)
            elif v == "internal":
                cls, ra = "internal", False
            else:
                cls, ra = "unknown", False   # 허용 값이 아님: fail-closed
    return cls, ra


def index_file(con, vault, rel, entry, stat):
    full = os.path.join(vault, rel)
    text, enc = read_text(full)
    sha1 = hashlib.sha1(text.encode("utf-8")).hexdigest()
    cls, ra = effective(vault, rel, entry)
    cur = con.execute(
        "INSERT INTO documents(path,registry_id,type,layer,classification,remote_allowed,mtime,size,sha1,encoding,indexed_at,"
        "parser_version,policy_hash,struct_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rel, entry["id"], entry.get("type"), entry.get("layer"), cls,
         int(ra), stat.st_mtime, stat.st_size, sha1, enc,
         datetime.now().isoformat(timespec="seconds"),
         PARSER_VERSION,
         policy_hash(cls, entry.get("type"), entry.get("layer"), entry.get("period_use"), entry.get("case_namespace"), ra),
         struct_hash(entry.get("type"), entry.get("period_use"), entry.get("case_namespace"))))
    doc_id = cur.lastrowid
    ext = os.path.splitext(rel)[1].lower()
    n, note = 0, ""

    if ext in TEXT_EXT:
        for seq, (meeting, case, heading, ls, body) in enumerate(chunk_markdown(text)):
            insert_chunk(con, doc_id, seq, "text", meeting, case, heading, ls, body, entry.get("case_namespace"))
            n += 1
    elif entry.get("type") != "statistics":
        n, note = index_generic_csv(con, doc_id, text)
    else:
        header, data, note = read_csv_rows(full, text)
        cols = {k: find_col(header, v) for k, v in COLMAP.items()}
        period = parse_period(entry.get("period_use"))
        skipped = 0
        for seq, row in enumerate(data):
            if not any(c.strip() for c in row):
                continue
            get = lambda k: (row[cols[k]].strip() if cols[k] is not None and cols[k] < len(row) else "")
            d = parse_date(get("decision_date"))
            if period and (d is None or not (period[0] <= d <= period[1])):
                skipped += 1
                continue
            pairs = [f"{(header[i] if i < len(header) else f'col{i+1}')}: {c.strip()}"
                     for i, c in enumerate(row) if c.strip()]
            body = "\n".join(pairs)
            # 의결번호 열 → 의결일 열 → 앞쪽 세 열 순서로 의결번호 형식을 찾는다(선방위 '구분' 열의 선거명 등은 버림)
            case = parse_case(get("case_no")) or parse_case(get("decision_date"))
            if not case:
                for c in row[:3]:
                    case = parse_case(c)
                    if case:
                        break
            heading = " | ".join(x for x in (get("broadcaster"), get("program").split("\n")[0], get("result")) if x)
            cid = insert_chunk(con, doc_id, seq, "csv_row", "", case, heading, seq + 1, body)
            con.execute(
                "INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (cid, doc_id, case[0] if case else None, case[1] if case else None, case[2] if case else None,
                 d.isoformat() if d else None,  # v1.3: 날짜로 읽지 못한 값은 넣지 않는다(원문은 조각 본문에 있음)
                 get("broadcaster"), get("channel"), get("program"), get("articles"), get("result")))
            n += 1
        if period:
            note = (note + "; " if note else "") + f"period_use {entry.get('period_use')} 적용, {skipped}행 제외"
    con.execute("UPDATE documents SET n_chunks=?, note=? WHERE doc_id=?", (n, note, doc_id))
    return n, note


def acquire_lock(db_dir):
    """다른 색인기가 실행 중이면 exit 2로 끝낸다. 잠금은 프로세스가 끝날 때까지(반환된 파일 객체가 살아 있는 동안) 유지된다."""
    if msvcrt is None:
        return None
    os.makedirs(db_dir, exist_ok=True)
    f = open(os.path.join(db_dir, "index.lock"), "a+b")
    try:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        f.close()
        print("다른 색인이 실행 중이라 이번 실행은 건너뜁니다(exit 2).", flush=True)
        sys.exit(2)
    return f


def main():
    ap = argparse.ArgumentParser(description="AI 자료창고 검색 DB 색인기")
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--full", action="store_true", help="기존 DB를 지우고 전체 재색인")
    ap.add_argument("--registry", help="레지스트리 파일(기본: vault/SOURCE_REGISTRY.yaml). 시험용")
    args = ap.parse_args()
    lock = acquire_lock(os.path.dirname(os.path.abspath(args.db)))   # v1.11: 단일 실행 잠금(--full의 DB 삭제보다 먼저)
    started = datetime.now()

    check_sqlite()
    reg_path = args.registry or os.path.join(args.vault, "SOURCE_REGISTRY.yaml")
    if not os.path.exists(reg_path):
        sys.exit(f"레지스트리를 찾을 수 없습니다: {reg_path}")
    reg = Registry(reg_path)

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    if args.full:
        for p in (args.db, args.db + "-wal", args.db + "-shm"):   # v1.8: 남은 WAL·SHM도 함께 지움
            if os.path.exists(p):
                os.remove(p)
    con = sqlite3.connect(args.db)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    cols = [r[1] for r in con.execute("PRAGMA table_info(chunks)")]
    if cols and "case_prefix" not in cols:
        con.close()
        sys.exit("DB 구조가 바뀌었습니다(v1.1). 'python build_index.py --full'로 다시 만들어 주세요.")
    con.executescript(SCHEMA)
    migrate_documents(con)

    t0 = time.time()
    seen, unlisted, report, failed = set(), [], [], []
    added = updated = unchanged = removed = meta_only = 0

    targets = []
    for top in SCAN_DIRS:
        for dirpath, dirs, files in os.walk(os.path.join(args.vault, top)):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fn in sorted(files):
                ext = os.path.splitext(fn)[1].lower()
                if fn.startswith(".") or ext not in TEXT_EXT | CSV_EXT:
                    continue
                rel = norm(os.path.relpath(os.path.join(dirpath, fn), args.vault))
                entry = reg.match(rel)
                if entry is None:
                    unlisted.append(rel)
                    continue
                if not entry.get("searchable", True) or entry.get("canonical") is False:
                    continue
                if entry.get("type") == "wiki" and fn in WIKI_ADMIN:
                    continue
                targets.append((rel, entry))

    total = len(targets)
    for k, (rel, entry) in enumerate(targets, 1):
        seen.add(rel)
        st = os.stat(os.path.join(args.vault, rel))
        row = con.execute("SELECT doc_id, mtime, size, registry_id, classification, remote_allowed, type, layer,"
                          " parser_version, policy_hash, struct_hash FROM documents WHERE path=?", (rel,)).fetchone()
        if row and row[1] == st.st_mtime and row[2] == st.st_size:
            doc_id, o_rid, o_cls, o_ra, o_type, o_layer, o_pv, o_ph, o_sh = row[0], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]
            pu, ns, typ = entry.get("period_use"), entry.get("case_namespace"), entry.get("type")
            cls, ra = effective(args.vault, rel, entry)
            new_ph, new_sh = policy_hash(cls, typ, entry.get("layer"), pu, ns, ra), struct_hash(typ, pu, ns)
            # 옛 행(v1.8 이하 DB)은 해시가 없다: 저장된 값으로 이전 해시를 복원하고, 파서 버전은 현재와 같다고 본다
            if o_ph is None or o_sh is None:
                o_ph = policy_hash(o_cls, o_type, o_layer, pu, ns, o_ra)
                o_sh = struct_hash(o_type, pu, ns)
            if o_pv is None:
                o_pv = PARSER_VERSION
            if o_pv == PARSER_VERSION and o_sh == new_sh:
                if o_ph == new_ph and o_rid == entry["id"] and row[8] is not None and row[9] is not None:
                    unchanged += 1
                    continue
                # 본문·구조는 그대로이고 공개 조건 등만 바뀜: 조각은 두고 documents 행만 고친다
                con.execute("UPDATE documents SET registry_id=?, type=?, layer=?, classification=?, remote_allowed=?,"
                            " parser_version=?, policy_hash=?, struct_hash=? WHERE doc_id=?",
                            (entry["id"], typ, entry.get("layer"), cls, int(ra), PARSER_VERSION, new_ph, new_sh, doc_id))
                con.commit()
                meta_only += 1
                print(f"[{k}/{total}] (메타데이터만 갱신) {rel}", flush=True)
                continue
        is_update = bool(row)
        if row:
            delete_doc(con, row[0])
        print(f"[{k}/{total}] {rel}", flush=True)
        try:
            n, note = index_file(con, args.vault, rel, entry, st)
            report.append((entry["id"], rel, n, note))
        except Exception as ex:  # 한 파일 오류로 전체가 멈추지 않게 한다. 실패는 목록에 남기고 종료 코드 1로 알린다
            con.rollback()   # 지우기·넣기를 함께 되돌리므로 DB에는 이전 판이 남고, 다음 실행에서 다시 시도된다
            msg = " ".join(str(ex).split()) or type(ex).__name__
            report.append((entry["id"], rel, -1, f"오류: {msg}"))
            failed.append((rel, msg))
            print(f"   ! 오류: {msg}", flush=True)
            continue
        con.commit()
        if is_update:
            updated += 1
        else:
            added += 1

    for doc_id, path in con.execute("SELECT doc_id, path FROM documents").fetchall():
        if path not in seen:
            delete_doc(con, doc_id)
            removed += 1
    con.execute("INSERT OR REPLACE INTO meta VALUES('built_at', ?)", (datetime.now().isoformat(timespec="seconds"),))
    con.execute("INSERT OR REPLACE INTO meta VALUES('vault', ?)", (args.vault,))
    con.commit()
    con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('optimize')")
    con.commit()

    # v1.8: WAL 파일 정리(색인 성공 시에만 실행)
    try:
        busy, wal_pages, done = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        wal_note = "완료" if busy == 0 else f"보류(다른 연결이 사용 중, {done}/{wal_pages} 페이지 반영)"
    except sqlite3.Error as e:
        wal_note = f"오류: {e}"

    # 보고서
    stats = con.execute(
        "SELECT registry_id, COUNT(*), SUM(n_chunks), MAX(remote_allowed), SUM(remote_allowed) FROM documents GROUP BY registry_id ORDER BY registry_id"
    ).fetchall()
    elapsed = time.time() - t0
    finished = datetime.now()
    lines = [f"# 색인 보고서 ({finished:%Y-%m-%d %H:%M})", "",
             f"- 시작 {started:%Y-%m-%d %H:%M:%S} / 완료 {finished:%Y-%m-%d %H:%M:%S} (소요 {elapsed:,.0f}초)",
             f"- 결과: **{'실패 ' + str(len(failed)) + '건 있음 (exit 1)' if failed else '성공 (실패 0건)'}**",
             f"- 성공: 추가 {added} / 갱신 {updated} / 메타데이터만 갱신 {meta_only} / 변경 없음 {unchanged} / 삭제 {removed}; 실패 {len(failed)}",
             f"- DB: `{args.db}` ({os.path.getsize(args.db)/1e6:,.1f} MB), WAL 정리: {wal_note}", "",
             "## 레지스트리 항목별", "", "| registry_id | 파일 수 | 조각 수 | 원격 허용 |", "|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {('예' if r[4] == r[1] else f'일부({r[4]}/{r[1]})') if r[3] else '아니오'} |" for r in stats]
    held = con.execute("SELECT path, classification FROM documents WHERE type='wiki' AND remote_allowed=0").fetchall()
    if held:
        lines += ["", f"## 원격 제외 위키 페이지 ({len(held)}개, 머리말 classification)", ""] + [f"- `{p}` ({c})" for p, c in held]
    notes = [r for r in report if r[3]]
    if failed:
        lines += ["", f"## 실패 파일 ({len(failed)}건, 다음 실행에서 자동 재시도)", ""] + [f"- `{p}`: {m}" for p, m in failed]
    if notes:
        lines += ["", "## 참고·오류", ""] + [f"- `{r[1]}` ({r[0]}): {r[3]}" for r in notes]
    if unlisted:
        lines += ["", f"## 레지스트리에 없는 파일 ({len(unlisted)}개, 색인 제외)", ""] + [f"- `{u}`" for u in unlisted]
    rep_path = os.path.join(HERE, "data", "index_report.md")
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    con.close()
    # v1.11: 실패 목록 파일(있으면 실패가 있다는 뜻이 되도록 0건이면 지운다)
    fail_path = os.path.join(os.path.dirname(os.path.abspath(args.db)), "index_failed.txt")
    if failed:
        with open(fail_path, "w", encoding="utf-8") as f:
            f.write(f"# 색인 실패 {len(failed)}건 ({finished:%Y-%m-%d %H:%M:%S})\n")
            f.writelines(f"{p}\t{m}\n" for p, m in failed)
    elif os.path.exists(fail_path):
        os.remove(fail_path)
    print("\n".join(lines[:7]))
    print(f"\n보고서: {rep_path}")
    if failed:
        print(f"실패 {len(failed)}건: {fail_path}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
