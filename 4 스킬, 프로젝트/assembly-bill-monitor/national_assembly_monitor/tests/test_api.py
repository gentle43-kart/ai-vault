"""웹 API와 국회 Open API 응답 처리(네트워크 없이)."""
import io
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app import config as config_mod
from app import db
from app.services import national_assembly as na
from tests.conftest import list_row


# ------------------------------------------------------ Open API 응답 처리
class _Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_urlopen(monkeypatch, payloads):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        p = payloads.pop(0)
        if isinstance(p, Exception):
            raise p
        return _Resp(json.dumps(p, ensure_ascii=False).encode("utf-8"))

    monkeypatch.setattr(na.urllib.request, "urlopen", fake_urlopen)
    return calls


def test_search_bills_paginates_and_sends_user_agent(settings, monkeypatch):
    page1 = {"TVBPMBILL11": [{"head": [{"list_total_count": 3}, {"RESULT": {"CODE": "INFO-000"}}]},
                             {"row": [list_row("1", "방송법"), list_row("2", "방송법2")]}]}
    page2 = {"TVBPMBILL11": [{"head": [{"list_total_count": 3}, {"RESULT": {"CODE": "INFO-000"}}]},
                             {"row": [list_row("3", "방송법3")]}]}
    calls = _patch_urlopen(monkeypatch, [page1, page2])
    rows = na.NationalAssemblyClient(settings).search_bills("방송", page_size=2)
    assert [r["BILL_NO"] for r in rows] == ["1", "2", "3"]
    assert calls[0].get_header("User-agent")
    assert "KEY=test-key" in calls[0].full_url and "BILL_NAME=" in calls[0].full_url


def test_since_stops_at_older_bill(settings, monkeypatch):
    def page(rows):
        return {"TVBPMBILL11": [{"head": [{"list_total_count": 500}, {"RESULT": {"CODE": "INFO-000"}}]},
                                {"row": rows}]}
    p1 = page([list_row("5", "방송법", date="2026-11-24"), list_row("4", "방송법", date="2026-11-20")])
    p2 = page([list_row("3", "방송법", date="2026-11-18"), list_row("2", "방송법", date="2026-11-10")])
    calls = _patch_urlopen(monkeypatch, [p1, p2, page([list_row("1", "방송법", date="2026-11-01")])])
    rows = na.NationalAssemblyClient(settings).search_bills("방송", since="2026-11-18", page_size=2)
    assert [r["BILL_NO"] for r in rows] == ["5", "4", "3"]   # 기준일 당일 포함, 이전은 제외
    assert len(calls) == 2                                     # 오래된 의안이 나온 페이지에서 멈춤


def test_no_data_returns_empty(settings, monkeypatch):
    _patch_urlopen(monkeypatch, [{"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}])
    assert na.NationalAssemblyClient(settings).search_bills("없는말") == []


def test_auth_error_not_retried(settings, monkeypatch):
    calls = _patch_urlopen(monkeypatch, [{"RESULT": {"CODE": "ERROR-290", "MESSAGE": "인증키가 유효하지 않습니다."}}])
    with pytest.raises(na.AssemblyAuthError):
        na.NationalAssemblyClient(settings).search_bills("방송")
    assert len(calls) == 1


def test_network_error_retried_three_times(settings, monkeypatch):
    calls = _patch_urlopen(monkeypatch, [urllib.error.URLError("timeout")] * 3)
    with pytest.raises(na.AssemblyApiError):
        na.NationalAssemblyClient(settings).search_bills("방송")
    assert len(calls) == 3


# ------------------------------------------------------ FastAPI
@pytest.fixture
def client(settings, monkeypatch):
    monkeypatch.setattr(config_mod, "load_settings", lambda: settings)
    import app.main as main
    monkeypatch.setattr(main, "load_settings", lambda: settings)
    conn = db.connect(settings.database_path)
    db.init_db(conn)
    db.upsert_bill(conn, {"bill_no": "2223020", "bill_id": "PRC_1", "bill_name": "방송법 일부개정법률안",
                          "proposer": "홍길동의원 등 10인", "propose_date": "2026-11-19",
                          "source_url": "https://likms.assembly.go.kr/x"}, "h")
    db.save_content(conn, "2223020", "제안이유\n  <script>alert(1)</script> 원문", "ok", "c")
    db.save_keywords(conn, "2223020", ["방송"])
    conn.commit()
    conn.close()
    with TestClient(main.app) as c:
        yield c


def test_list_and_detail(client):
    r = client.get("/api/bills").json()
    assert r["total"] == 1 and r["items"][0]["is_new"] is True
    assert r["items"][0]["summary_text"] == "제안이유\n  <script>alert(1)</script> 원문"  # 원문 그대로(화면에서 textContent로 표시)
    assert client.get("/api/bills/2223020").json()["keywords"] == ["방송"]
    assert client.get("/api/bills/0000000").status_code == 404
    assert client.get("/api/bills", params={"keyword": "통신"}).json()["total"] == 0
    assert client.get("/api/bills", params={"status": "processed"}).json()["total"] == 0


def test_keywords_and_index(client):
    assert client.get("/api/keywords").json() == {"keywords": ["방송", "통신", "시청각"]}
    html = client.get("/").text
    assert "최신 조사" in html and "AI" not in html


def test_get_does_not_call_assembly(client, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("F5/GET에서 국회 API를 호출하면 안 됨")
    monkeypatch.setattr(na.urllib.request, "urlopen", boom)
    client.get("/")
    client.get("/api/bills")
    client.get("/api/sync/status")
