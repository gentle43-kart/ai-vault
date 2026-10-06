# -*- coding: utf-8 -*-
"""
AI 자료창고 MCP 서버 v1.7 (2026-10-06) - search.db 읽기 전용 검색 서버
  v1.7: search_case가 '기관:번호'(예: 방통위:2012-03-0021)를 받아 그 기관 조각만 조회한다. 허용 기관은
        SOURCE_REGISTRY.yaml의 case_namespace 값이며, 미지원 접두어는 허용 값을 안내하는 오류로 답한다.
        접두어 없는 번호가 여러 기관에 걸리면 결과 title 앞에 (기관)을, 각 항목에 metadata.institution을 붙인다.
        한 기관에만 걸리면 v1.6과 같은 응답이다. 배경: '방통위:2012-03-0021'이 방심위 조각을 돌려준 결함(보고서 1번).
  v1.6: search·search_case 응답에 total(일치하는 전체 조각 수)·returned·offset·limit·truncated 추가,
        offset 인자 추가(이어서 조회), 도구 설명에 limit 상한(MAX_LIMIT 20)과 잘림 확인 안내 추가.
        results 항목은 v1.5와 같다. offset 기본값 0이면 v1.5와 같은 결과가 나온다.
        배경: 20건 상한에서 잘린 결과를 "일치 항목 전체"로 오판한 사례(2026-10-06).
  v1.5: search에 선택 인자 kind(자료 묶음), registry_id(정확한 id 목록) 추가. 둘 다 기본값은 빈 값이며,
        생략하면 v1.4와 결과가 같다. 값은 SQL에 직접 넣지 않고 매개변수로 넘긴다. search_case는 바꾸지 않았다.
  v1.4: 명령행 --remote-extra-ids 추가(환경변수 AIVAULT_REMOTE_EXTRA_IDS와 같고, 명령행이 우선).
        OpenAI tunnel-client 공식 문서에 stdio 명령으로 환경변수를 넘기는 방법이 확인되지 않아,
        --mcp-command 문자열 안에 값을 적을 수 있게 했다. 형식이 틀린 id는 표준오류로 알리고 무시한다.
  v1.3: AIVAULT_REMOTE_EXTRA_IDS 추가. remote 범위에서도 쉼표로 구분한 registry_id 목록을
        지정하면 해당 항목을 원격 경로로 제공한다(AGENTS.md 0절 3 예외, 개별 승인 대상).
        기본값은 빈 문자열(종전 동작과 같음). 결과 제목의 [internal] 표시는 유지한다.
  v1.2: 조회 범위 선택 추가. 환경변수 AIVAULT_SCOPE=all 또는 --scope all 이면 remote_allowed 조건 없이
        색인된 전체 자료(internal·unknown 포함)를 돌려준다. 기본값(remote)은 v1.1과 같다.
        Claude 데스크톱(로컬 stdio) 설정에서만 all을 쓰고, ChatGPT 터널은 기본값(remote)을 유지한다.
  v1.1: 서버 안내문에 위키(registry_id wiki) 자료의 성격 추가

- 기본(remote): 원격 허용(remote_allowed = 1) 자료만 돌려준다
  (SOURCE_REGISTRY.yaml 규칙 1: public + classification_confirmed + remote_allowed).
- all: 색인된 전체 자료를 돌려준다. 결과 제목에 [internal] 등 보안등급을 붙여 구분한다.
- DB는 읽기 전용(mode=ro)으로 연다. 쓰기 도구는 없다(AGENTS.md 2절: MCP는 검색·조회 전용).
- 도구: search(검색어) / fetch(조각 id) / search_case(의결번호). ChatGPT 검색·조회형 연결의 형식을 따른다.

실행 (PowerShell):
    pip install "mcp>=1.9,<2" pyyaml
    python mcp_server.py                       # stdio, 원격 허용 자료만 (OpenAI tunnel-client --mcp-command 용)
    python mcp_server.py --scope all           # stdio, 전체 자료 (Claude 데스크톱 로컬 연결용; AIVAULT_SCOPE=all과 같음)
    python mcp_server.py --http --port 8765    # streamable HTTP, http://127.0.0.1:8765/mcp (로컬 시험용)
    python mcp_server.py --remote-extra-ids notion_notes,law_budget   # remote 범위 + 승인된 internal 항목(v1.4)
"""
import argparse
import os
import re
import sqlite3
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("AIVAULT_DB", os.path.join(HERE, "data", "search.db"))
VAULT = os.environ.get("AIVAULT_VAULT", r"J:\AI 자료")
MAX_LIMIT = 20

# 조회 범위(v1.2). 명령행 --scope가 환경변수보다 우선한다. 모듈 로드 시점에 정해야 안내문에 반영된다.
def _argv_value(flag):
    """명령행 값(모듈 로드 시점에 필요한 옵션용). '--flag 값'과 '--flag=값'을 모두 받는다."""
    for i, a in enumerate(sys.argv):
        if a == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


_argv_scope = _argv_value("--scope")
SCOPE = (_argv_scope or os.environ.get("AIVAULT_SCOPE", "remote")).strip().lower()
if SCOPE not in ("remote", "all"):
    sys.exit(f"AIVAULT_SCOPE/--scope 값은 remote 또는 all이어야 합니다: {SCOPE}")

# 원격 추가 허용 registry_id (v1.3, AGENTS.md 0절 3 예외, 개별 승인 대상)
# 환경변수 AIVAULT_REMOTE_EXTRA_IDS에 쉼표로 구분한 registry_id 목록. 기본값은 빈 문자열(종전 동작).
_VALID_ID = re.compile(r"^[a-zA-Z0-9_]+$")
# v1.4: 명령행 --remote-extra-ids가 환경변수보다 우선한다.
_extra_argv = _argv_value("--remote-extra-ids")
_extra_raw = _extra_argv if _extra_argv is not None else os.environ.get("AIVAULT_REMOTE_EXTRA_IDS", "")
_extra_all = [x.strip() for x in _extra_raw.split(",") if x.strip()]
EXTRA_IDS = [x for x in _extra_all if _VALID_ID.match(x)]
for _bad in sorted(set(_extra_all) - set(EXTRA_IDS)):
    print(f"[ai-vault] 형식이 틀린 registry_id를 무시합니다: {_bad!r}", file=sys.stderr)  # stdout은 MCP 통신용

if SCOPE == "all":
    SCOPE_SQL = "1 = 1"
elif EXTRA_IDS:
    _ids_sql = ",".join(f"'{rid}'" for rid in EXTRA_IDS)
    SCOPE_SQL = f"(d.remote_allowed = 1 OR d.registry_id IN ({_ids_sql}))"
else:
    SCOPE_SQL = "d.remote_allowed = 1"

_extra_note = (
    f" 추가 허용 항목: {', '.join(EXTRA_IDS)}. " if EXTRA_IDS and SCOPE == "remote" else ""
)
SCOPE_NOTE = (
    ("원격 허용(public) 자료만 검색한다." + _extra_note + " ") if SCOPE == "remote" else
    "색인된 전체 자료(internal·unknown 포함)를 검색한다. 결과 제목의 [internal]·[unknown] 표시는 보안등급이며, "
    "이런 자료를 외부 공유 문서에 옮길 때는 보안등급을 확인한다. "
)

# 검색 범위 필터(v1.5). kind 묶음은 SOURCE_REGISTRY.yaml의 type(= documents.type)을 기준으로 한다.
# 보안등급(public 여부)이나 자료의 성격(법령 여부)으로 나누지 않는다. 예: law_budget은 type이 guide라
# guide 묶음이고, 내부 자료라도 type이 law·regulation이면 law 묶음이다(공개 범위는 SCOPE_SQL이 따로 정한다).
KINDS = {
    "wiki": ("wiki",),
    "law": ("law", "regulation"),
    "minutes": ("meeting_minutes",),
    "stats": ("statistics",),
    "papers": ("research",),
    "cases": ("casebook", "precedent", "interpretation"),
    "guide": ("guide", "commentary"),
    "news": ("news",),
    "internal": ("internal_doc", "notes", "inbox"),
}


def _page(results, total, offset, limit):
    """응답에 붙일 쪽 정보. truncated가 true면 일치 항목이 더 남아 있으니 offset을 올려 이어서 조회해야 한다."""
    return {"results": results, "total": total, "returned": len(results), "offset": offset, "limit": limit,
            "truncated": offset + len(results) < total}


def _scope_filter(kind, registry_id):
    """kind·registry_id를 (SQL 조각 목록, 매개변수 목록)으로 바꾼다. 값은 모두 ? 매개변수로 넘긴다."""
    where, params = [], []
    names = [k.strip().lower() for k in re.split(r"[|,]", kind or "") if k.strip()]
    if names:
        bad = [k for k in names if k not in KINDS]
        if bad:
            raise ValueError(f"알 수 없는 kind: {', '.join(bad)}. 사용 가능한 값: {', '.join(KINDS)}")
        types = sorted({t for k in names for t in KINDS[k]})
        where.append(f"d.type IN ({','.join('?' * len(types))})")
        params += types
    ids = [x.strip() for x in (registry_id or "").split(",") if x.strip()]
    if ids:
        bad = [x for x in ids if not _VALID_ID.match(x)]
        if bad:
            raise ValueError(f"registry_id 형식이 틀렸습니다(영문·숫자·밑줄만, 쉼표로 구분): {', '.join(bad)}")
        where.append(f"d.registry_id IN ({','.join('?' * len(ids))})")
        params += ids
    return where, params


sys.path.insert(0, HERE)
from build_index import parse_case  # noqa: E402  의결번호 해석은 색인기와 같은 규칙을 쓴다
from search import fts_query  # noqa: E402

mcp = FastMCP(
    "ai-vault",
    instructions=(
        "방송심의 업무 자료창고(법령·규정·해설집·판례·통계·기사 등)를 검색한다. " + SCOPE_NOTE +
        "결과는 변환본 조각이며, 결론을 좌우하는 내용은 원문 확인이 필요하다. "
        "기사(registry_id news_clippings)와 논문은 공식 자료가 아니다. "
        "위키(registry_id wiki)는 AI가 작성한 요약·분석이며 대부분 status: draft이다. "
        "위키 내용을 근거로 쓸 때는 그 페이지의 sources에 적힌 변환본·원본을 함께 확인한다."
    ),
)


def _con():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


_url_cache = {}


def _source_url(path):
    """기사 클립은 머리말의 source URL을 돌려준다."""
    if path in _url_cache:
        return _url_cache[path]
    url = ""
    try:
        with open(os.path.join(VAULT, path), encoding="utf-8-sig") as f:
            head = f.read(3000)
        m = re.search(r'^source:\s*"?([^"\n]+)"?\s*$', head, re.M)
        if m:
            url = m.group(1).strip()
    except OSError:
        pass
    _url_cache[path] = url
    return url


def _url(r):
    if r["registry_id"] == "news_clippings":
        u = _source_url(r["path"])
        if u:
            return u
    return f"vault://{r['path']}#L{r['line_start']}"


def _title(r):
    parts = [r["registry_id"], os.path.basename(r["path"])]
    cls = r["classification"] if "classification" in r.keys() else None
    if cls and cls != "public":
        parts[0] = f"[{cls}] " + parts[0]
    for k in ("meeting", "case_no", "heading"):
        if r[k]:
            parts.append(str(r[k])[:80])
    return " | ".join(parts)


@mcp.tool(annotations=RO, structured_output=True)
def search(query: str, limit: int = 10, kind: str = "", registry_id: str = "", offset: int = 0) -> dict[str, Any]:
    """자료창고 검색. 공백으로 나눈 단어를 모두 포함하는 조각을 찾는다(3글자 이상은 색인, 2글자 이하는 전체 훑기).
    결과의 id를 fetch에 넘기면 조각 전문을 볼 수 있다.
    범위 좁히기(선택, 생략하면 전체): 회의록·논문이 많아 결과가 묻힐 때 쓴다.
    - kind: 자료 묶음. wiki(위키) / law(법령·규정·규칙) / minutes(회의록) / stats(통계) / papers(논문) /
      cases(사례집·판례·해석례) / guide(지침·해설집) / news(기사) / internal(내부·메모류).
      '|' 또는 쉼표로 여러 개 가능(예: "wiki|law").
    - registry_id: 정확한 자료 id를 쉼표로 구분(예: "law_broadcast,law_general"). kind와 같이 주면 둘 다 만족하는 것만 찾는다.
    조회 범위(서버 설정)를 넘는 자료는 지정해도 나오지 않는다. 값이 틀리면 오류로 사용 가능한 값을 알려 준다.
    한 번에 돌려주는 건수: limit 기본 10, 최대 20(더 크게 줘도 20건에서 잘린다). 결과가 상위 일부일 수 있으므로
    응답의 total(일치하는 전체 조각 수)·returned·truncated를 반드시 확인한다. truncated가 true이면
    일치 항목이 더 있으니, "전체"를 말하려면 offset을 returned만큼 올려 가며 이어서 조회한다(예: offset=20, 40...).
    결과가 limit보다 적게 나왔다고 해서 전체라는 뜻은 아니다. total과 비교해 판단한다."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    match, shorts = fts_query(query or "")
    where, params = [SCOPE_SQL], []
    f_where, f_params = _scope_filter(kind, registry_id)
    where += f_where
    params += f_params
    if match:
        where.append("chunks_fts MATCH ?")
        params.append(match)
    for s in shorts:
        where.append("instr(chunks_fts.text, ?) > 0")
        params.append(s)
    if not match and not shorts:
        return _page([], 0, offset, limit)
    # offset으로 이어 조회해도 순서가 흔들리지 않도록 chunk_id를 보조 정렬 키로 둔다.
    order = "bm25(chunks_fts), c.chunk_id" if match else "c.chunk_id"
    base = f"""FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.rowid
              JOIN documents d ON d.doc_id = c.doc_id
              WHERE {' AND '.join(where)}"""
    with _con() as con:
        total = con.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        rows = con.execute(f"""SELECT c.chunk_id, d.path, d.registry_id, d.classification, c.meeting, c.case_no, c.heading, c.line_start
                              {base} ORDER BY {order} LIMIT ? OFFSET ?""", params + [limit, offset]).fetchall()
    return _page([{"id": str(r["chunk_id"]), "title": _title(r), "url": _url(r)} for r in rows], total, offset, limit)


@mcp.tool(annotations=RO, structured_output=True)
def fetch(id: str) -> dict[str, Any]:
    """search 결과의 id로 조각 전문과 출처(파일 경로·줄 번호·자료 종류)를 가져온다."""
    try:
        cid = int(id)
    except (TypeError, ValueError):
        raise ValueError("id는 search 결과의 숫자 id여야 합니다.")
    with _con() as con:
        r = con.execute(f"""SELECT c.chunk_id, c.meeting, c.case_no, c.heading, c.line_start,
                                  d.path, d.registry_id, d.type, d.layer, d.classification, d.remote_allowed, f.text
                           FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                           JOIN chunks_fts f ON f.rowid = c.chunk_id
                           WHERE c.chunk_id = ? AND {SCOPE_SQL}""", (cid,)).fetchone()
    if not r:
        raise ValueError("해당 조각이 없거나, 현재 조회 범위(" + SCOPE + ")에서 제공하지 않는 자료입니다.")
    return {
        "id": str(r["chunk_id"]),
        "title": _title(r),
        "text": r["text"],
        "url": _url(r),
        "metadata": {
            "path": r["path"], "line": r["line_start"], "registry_id": r["registry_id"],
            "type": r["type"], "layer": r["layer"], "classification": r["classification"],
            "remote_allowed": bool(r["remote_allowed"]), "scope": SCOPE,
            "meeting": r["meeting"] or "", "case_no": r["case_no"] or "",
            "note": "변환본 조각이다. 결론을 좌우하는 내용은 원본·공식 원문으로 확인해야 한다.",
        },
    }


_NS_INPUT_RE = re.compile(r"^\s*([^\s:：\d][^\s:：]*)\s*[:：]\s*(.+)$", re.S)
BASE_ORG = "방심위"  # 이름공간이 없는 번호(색인기 case_namespace 미지정 항목)의 표시 이름
# 기관 약칭 별칭(v1.8, 사용자 결정 2026-10-06). 기관 이름이 바뀌었으므로 옛 이름·현 이름을 모두 받는다.
# 값은 DB에 저장된 이름공간이며 ""은 이름공간 없음(방심위 자료)이다. SOURCE_REGISTRY에는 별칭 필드를 두지 않는다.
CASE_ALIASES = {"방심위": "", "방미심위": "", "방통위": "방통위", "방미통위": "방통위"}
_ns_cache = None


def _case_namespaces():
    """색인된 이름공간 = SOURCE_REGISTRY.yaml의 case_namespace 값(색인기 insert_chunk가 접두부에 붙이는 값).
    레지스트리를 읽지 못하면 DB에 실제 저장된 이름공간으로 대신한다."""
    global _ns_cache
    if _ns_cache is not None:
        return _ns_cache
    found = set()
    try:
        import yaml
        with open(os.path.join(VAULT, "SOURCE_REGISTRY.yaml"), encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        defaults = data.get("defaults") or {}
        if defaults.get("case_namespace"):
            found.add(str(defaults["case_namespace"]))
        found |= {str(s["case_namespace"]) for s in data.get("sources", []) if s.get("case_namespace")}
    except Exception as e:  # 레지스트리를 못 읽는 것이 검색 중단 사유는 아니다
        print(f"[ai-vault] 레지스트리의 case_namespace를 읽지 못했습니다: {e}", file=sys.stderr)
    if not found:
        with _con() as con:
            found = {r[0] for r in con.execute(
                "SELECT DISTINCT substr(case_prefix, 1, instr(case_prefix, ':') - 1) FROM chunks WHERE case_prefix LIKE '%:%'")}
    _ns_cache = sorted(found)
    for target in {v for v in CASE_ALIASES.values() if v}:   # 서버 시작 때 점검: 별칭이 가리키는 값이 레지스트리에 있어야 한다
        if target not in _ns_cache:
            print(f"[ai-vault] 별칭이 가리키는 이름공간 '{target}'이(가) 레지스트리 case_namespace에 없습니다.", file=sys.stderr)
    return _ns_cache


def _accepted_prefixes():
    """입력으로 받는 접두어 -> 이름공간. 별칭 표 + 레지스트리에만 있는 이름공간(그 값 자체)."""
    acc = dict(CASE_ALIASES)
    for n in _case_namespaces():
        acc.setdefault(n, n)
    return acc


def _org(prefix):
    """case_prefix(저장값)의 기관 표시: 이름공간 없음 -> 방심위, 그 밖에는 이름공간 그대로."""
    return prefix.split(":", 1)[0] if prefix and ":" in prefix else BASE_ORG


@mcp.tool(annotations=RO, structured_output=True)
def search_case(case_no: str, limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """의결번호(예: 2016-방송-08-0066, 제2020-08-0064호)로 자료 조각을 찾는다(조회 범위는 서버 설정을 따른다).
    기관 구분: 형식이 같은 다른 기관 번호가 있어 '방통위:2012-03-0021'처럼 앞에 '기관:'을 붙이면 그 기관 조각만 돌려준다.
    기관 약칭은 옛 이름과 현 이름을 모두 받는다(방심위=방미심위, 방통위=방미통위). 붙이지 않으면 방심위 번호를 먼저,
    다른 기관 번호를 이어서 찾는다. 결과 항목의 namespace가 기관 표시(방심위·방통위)이다.
    limit 최대 20(초과분은 잘림). 응답의 total·returned·truncated를 확인하고, truncated가 true이면 offset을 올려 이어서 조회한다."""
    raw = case_no or ""
    ns = None   # None=접두어 없음, ""=이름공간 없는 자료(방심위), 그 밖=이름공간
    m = _NS_INPUT_RE.match(raw)
    if m:
        label, raw = m.group(1), m.group(2)
        acc = _accepted_prefixes()
        if label not in acc:
            raise ValueError(f"지원하지 않는 기관 접두어: {label}. 사용 가능한 접두어: {', '.join(acc)}. 접두어 없이 번호만 입력해도 된다.")
        ns = acc[label]
    c = parse_case(raw)
    if not c:
        raise ValueError("의결번호 형식을 인식하지 못했습니다. 예: 2026-방송-02-0003, 방통위:2012-03-0021")
    _, prefix, na, nb = c
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    if ns is None:
        prefixes = [prefix] + [f"{n}:{prefix}" for n in _case_namespaces()]
    elif ns == "":
        prefixes = [prefix]
    else:
        prefixes = [f"{ns}:{prefix}"]
    where = f"{SCOPE_SQL} AND c.case_prefix IN ({','.join('?' * len(prefixes))}) AND c.num_from <= ? AND c.num_to >= ?"
    params = prefixes + [nb, na]
    with _con() as con:
        total = con.execute(f"""SELECT COUNT(*) FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                               WHERE {where}""", params).fetchone()[0]
        # 이름공간 없는 조각(방심위)을 먼저 둔다: 접두어 없는 입력에서도 기존 번호의 v1.6 순서가 유지된다
        rows = con.execute(f"""SELECT c.chunk_id, d.path, d.registry_id, d.classification, c.meeting, c.case_no, c.case_prefix, c.heading, c.line_start
                              FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                              WHERE {where}
                              ORDER BY (instr(c.case_prefix, ':') > 0), c.kind DESC, d.path, c.seq LIMIT ? OFFSET ?""",
                            params + [limit, offset]).fetchall()
    results = [{"id": str(r["chunk_id"]), "title": _title(r), "url": _url(r), "namespace": _org(r["case_prefix"])} for r in rows]
    return _page(results, total, offset, limit)


def main():
    ap = argparse.ArgumentParser(description="AI 자료창고 MCP 서버(읽기 전용)")
    ap.add_argument("--http", action="store_true", help="streamable HTTP로 실행(기본은 stdio)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--scope", choices=["remote", "all"], help="조회 범위(기본 remote). 환경변수 AIVAULT_SCOPE와 같음")
    ap.add_argument("--remote-extra-ids", help="remote 범위에서 추가 허용할 registry_id(쉼표 구분). 환경변수 AIVAULT_REMOTE_EXTRA_IDS와 같음")
    a = ap.parse_args()
    if not os.path.exists(DB):
        sys.exit(f"DB가 없습니다: {DB}")
    if a.http:
        mcp.settings.host, mcp.settings.port = a.host, a.port
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
