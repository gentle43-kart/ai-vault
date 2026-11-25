"""국회 공식 데이터 수집 전담 모듈.

- 국회사무처 Open API(open.assembly.go.kr): 의안 목록·기본정보
- 국회 의안정보시스템(likms.assembly.go.kr): '제안이유 및 주요내용' 원문
  (Open API 응답에는 이 텍스트가 없어서, 의안 상세 화면이 사용하는 요청을 그대로 재현한다)

받은 텍스트는 고치거나 요약하지 않는다. HTML 엔티티 복원과 앞뒤 공백 제거만 한다.
"""
from __future__ import annotations

import html
import http.cookiejar
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from app.config import Settings

# 국회 API 서버는 User-Agent가 없으면 400을 돌려준다.
USER_AGENT = "Mozilla/5.0 (compatible; bill-monitor/1.0)"

# 의원·위원회·정부 제출 법률안 전체 목록(의안명 부분일치 검색 지원)
BILL_LIST_API = "TVBPMBILL11"


class AssemblyApiError(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class AssemblyAuthError(AssemblyApiError):
    """인증키 오류(ERROR-290 등)."""


def _with_retry(func: Callable[[], Any], waits: tuple[float, ...]) -> Any:
    """1차 실패 → 2초 대기 → 2차 실패 → 5초 대기 → 3차. 인증 오류는 재시도하지 않는다."""
    last: Exception | None = None
    for attempt in range(len(waits) + 1):
        try:
            return func()
        except AssemblyAuthError:
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, AssemblyApiError, ValueError) as e:
            last = e
            if attempt < len(waits):
                time.sleep(waits[attempt])
    raise AssemblyApiError(f"요청 실패(3회 시도): {last}") from last


class NationalAssemblyClient:
    def __init__(self, settings: Settings, raw_logger: Callable[[str, str | None, str], None] | None = None):
        self.s = settings
        self.raw_logger = raw_logger  # (api_name, bill_no, response_text) 원본 응답 저장 콜백

    # ------------------------------------------------------------------ Open API
    def _get_json(self, api: str, params: dict[str, Any]) -> dict:
        q = {"Type": "json", **params}
        if self.s.assembly_api_key:
            q["KEY"] = self.s.assembly_api_key
        url = self.s.assembly_api_base_url + api + "?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.s.api_timeout) as r:
            if r.status != 200:
                raise AssemblyApiError(f"HTTP {r.status}")
            text = r.read().decode("utf-8")
        if self.raw_logger:
            self.raw_logger(api, params.get("BILL_NO"), text)
        return json.loads(text)

    def _rows(self, api: str, params: dict[str, Any]) -> tuple[int, list[dict]]:
        data = _with_retry(lambda: self._get_json(api, params), self.s.api_retry_waits)
        if api not in data:  # 오류 응답: {"RESULT": {"CODE": ..., "MESSAGE": ...}}
            result = data.get("RESULT", {})
            code, msg = result.get("CODE", ""), result.get("MESSAGE", "")
            if code == "INFO-200":  # 해당하는 데이터가 없습니다
                return 0, []
            if code == "ERROR-290":
                raise AssemblyAuthError(f"국회 Open API 인증키 오류({code}): {msg}", code)
            raise AssemblyApiError(f"국회 Open API 오류({code}): {msg}", code)
        blocks = data[api]
        head = blocks[0].get("head", [])
        total = 0
        for h in head:
            if "list_total_count" in h:
                total = int(h["list_total_count"])
            if "RESULT" in h and h["RESULT"].get("CODE") not in ("INFO-000", None):
                raise AssemblyApiError(f"국회 Open API 오류: {h['RESULT']}", h["RESULT"].get("CODE"))
        rows = blocks[1].get("row", []) if len(blocks) > 1 else []
        return total, rows

    def search_bills(self, keyword: str, since: str | None = None,
                     page_size: int = 100, max_pages: int = 50) -> list[dict]:
        """의안명에 keyword가 들어간 법률안 목록.

        since(YYYY-MM-DD)를 주면 제안일이 그 날짜 이후인 의안만 돌려준다.
        API는 날짜 조건을 받지 않지만 결과가 제안일 최신순이므로
        (2026-11-25 확인) 기준일보다 오래된 의안이 나오면 더 받지 않는다.
        """
        rows: list[dict] = []
        fetched = 0
        if since:
            page_size = min(page_size, 20)  # 최근 것만 볼 때는 작게 받아 빨리 멈춘다
        for page in range(1, max_pages + 1):
            total, chunk = self._rows(BILL_LIST_API, {
                "AGE": self.s.age, "BILL_NAME": keyword, "pIndex": page, "pSize": page_size})
            fetched += len(chunk)
            if since:
                recent = [r for r in chunk if (r.get("PROPOSE_DT") or "") >= since]
                rows.extend(recent)
                if len(recent) < len(chunk):  # 기준일 이전 의안이 나옴 → 중단
                    break
            else:
                rows.extend(chunk)
            # 인증키가 없으면 샘플 모드(최대 5건)라 페이지가 늘지 않는다.
            if not chunk or fetched >= total or len(chunk) < page_size:
                break
        return rows

    def get_bill_basic(self, bill_no: str) -> dict | None:
        """의안번호로 기본정보 1건(ALLBILL). 목록 API에 없는 공포 정보 등이 필요할 때 사용."""
        _, rows = self._rows("ALLBILL", {"BILL_NO": bill_no, "pIndex": 1, "pSize": 1})
        return rows[0] if rows else None

    def get_bill_proposers(self, bill_id: str) -> list[dict]:
        """의안 제안자 명단(BILLINFOPPSR)."""
        _, rows = self._rows("BILLINFOPPSR", {"BILL_ID": bill_id, "pIndex": 1, "pSize": 300})
        return rows

    # ------------------------------------------------------- 의안정보시스템 원문
    def get_official_summary(self, bill_id: str) -> str | None:
        """'제안이유 및 주요내용' 원문. 해당 내용이 없는 의안이면 None.

        의안 상세 화면(billDetailPage.do)의 hidden 폼 값을 그대로 담아
        화면이 쓰는 요청(bill/detail/billInfo.do)을 보낸다.
        """
        return _with_retry(lambda: self._fetch_summary(bill_id), self.s.api_retry_waits)

    def _fetch_summary(self, bill_id: str) -> str | None:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.addheaders = [("User-Agent", USER_AGENT)]
        base = self.s.likms_base_url
        detail_url = f"{base}/billDetailPage.do?billId={urllib.parse.quote(bill_id)}"
        with opener.open(detail_url, timeout=self.s.api_timeout) as r:
            detail = r.read().decode("utf-8", "replace")
        params = parse_bill_form(detail)
        if not params.get("billId"):
            raise AssemblyApiError("의안정보시스템 상세 화면 구조가 바뀌었습니다(의안 정보 폼 없음)")
        req = urllib.request.Request(
            f"{base}/bill/detail/billInfo.do",
            data=urllib.parse.urlencode(params).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                     "X-Requested-With": "XMLHttpRequest", "Referer": detail_url})
        with opener.open(req, timeout=self.s.api_timeout) as r:
            fragment = r.read().decode("utf-8", "replace")
        if self.raw_logger:
            self.raw_logger("likms.billInfo", params.get("billNo"), fragment)
        if 'id="tab_billInfo_sect"' not in fragment:
            raise AssemblyApiError("의안정보시스템 응답이 예상과 다릅니다(심사정보 영역 없음)")
        return parse_summary(fragment)


# 상세 화면의 의안 정보 폼: <form id="form" name="form"> 안의 hidden input(billId, billNo, billKindCd ...)
_FORM_RE = re.compile(r'<form\b[^>]*\bid="form"[^>]*>(.*?)</form>', re.S)
_INPUT_RE = re.compile(r"<input\b[^>]*>", re.S)
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
_SUMMARY_RE = re.compile(r'<pre\b[^>]*id="prntSummary"[^>]*>(.*?)</pre>', re.S)


def parse_bill_form(detail_html: str) -> dict[str, str]:
    m = _FORM_RE.search(detail_html)
    if not m:
        return {}
    params: dict[str, str] = {}
    for tag in _INPUT_RE.findall(m.group(1)):
        attrs = dict(_ATTR_RE.findall(tag))
        if "name" in attrs:
            params[attrs["name"]] = html.unescape(attrs.get("value", ""))
    return params


def parse_summary(fragment: str) -> str | None:
    """<pre id="prntSummary"> 안의 텍스트. 문장은 손대지 않는다."""
    m = _SUMMARY_RE.search(fragment)
    if not m:
        return None
    text = html.unescape(re.sub(r"<br\s*/?>", "\n", m.group(1)))
    text = text.replace("\r\n", "\n").strip("\n").rstrip()
    # 앞쪽 빈 줄만 정리. 들여쓰기·줄바꿈 등 원문 형식은 유지
    return text if text.strip() else None
