"""국회 API 응답 → 내부 의안 모델 변환, 중복 제거, 변경 감지 해시."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _clean(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def normalize_list_row(row: dict) -> dict:
    """TVBPMBILL11 행 → 내부 모델. 필드명은 실제 응답 기준."""
    return {
        "bill_no": _clean(row.get("BILL_NO")),
        "bill_id": _clean(row.get("BILL_ID")),
        "bill_name": _clean(row.get("BILL_NAME")),
        "proposer": _clean(row.get("PROPOSER")),
        "proposer_kind": _clean(row.get("PROPOSER_KIND")),
        "propose_date": _clean(row.get("PROPOSE_DT")),
        "committee": _clean(row.get("CURR_COMMITTEE")),
        "proc_result": _clean(row.get("PROC_RESULT_CD")),
        "source_url": _clean(row.get("LINK_URL")),
        "list_data": json.dumps(row, ensure_ascii=False, sort_keys=True),
    }


def merge_bills(items: list[tuple[str, dict]]) -> dict[str, dict]:
    """(검색 키워드, 정규화된 의안) 목록을 의안번호 기준으로 합친다.
    같은 의안이 여러 키워드로 나오면 키워드만 누적한다."""
    result: dict[str, dict] = {}
    for keyword, bill in items:
        no = bill.get("bill_no")
        if not no:
            continue
        if no not in result:
            result[no] = {**bill, "keywords": []}
        else:  # 비어 있는 값만 보완
            for k, v in bill.items():
                if result[no].get(k) is None and v is not None:
                    result[no][k] = v
        if keyword not in result[no]["keywords"]:
            result[no]["keywords"].append(keyword)
    return result


HASH_FIELDS = ("bill_name", "proposer", "propose_date", "committee", "proc_result", "source_url")


def make_source_hash(bill: dict, summary_text: str | None) -> str:
    text = "\n".join([*(bill.get(f) or "" for f in HASH_FIELDS), summary_text or ""])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_content_hash(summary_text: str | None) -> str | None:
    return hashlib.sha256(summary_text.encode("utf-8")).hexdigest() if summary_text else None
