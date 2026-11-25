"""관심 키워드 매칭."""
from __future__ import annotations


def contains_keyword(text: str | None, keyword: str) -> bool:
    """단순 포함 검색. 영문은 대소문자 무시(한글은 영향 없음)."""
    if not text or not keyword:
        return False
    return keyword.casefold() in text.casefold()


def matched_keywords(bill_name: str | None, keywords: list[str]) -> list[str]:
    """의안명에 들어 있는 관심 키워드 목록."""
    return [k for k in keywords if contains_keyword(bill_name, k)]
