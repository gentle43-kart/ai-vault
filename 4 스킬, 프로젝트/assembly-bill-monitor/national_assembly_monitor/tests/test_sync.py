"""조사 흐름: 국회 서버 대신 가짜 응답을 넣어 저장·변경 감지·실패 처리를 확인."""
import pytest

from app import db
from app.services import national_assembly as na
from app.services import sync_service
from tests.conftest import list_row


class FakeApi:
    def __init__(self):
        self.rows = {
            "방송": [list_row("2223020", "방송법 일부개정법률안"),
                   list_row("2223098", "방송통신발전 기본법 일부개정법률안")],
            "통신": [list_row("2223098", "방송통신발전 기본법 일부개정법률안"),
                   list_row("2223122", "전기통신사업법 일부개정법률안"),
                   list_row("2229999", "소득세법 일부개정법률안")],  # API가 엉뚱한 결과를 줘도 걸러야 함
            "시청각": [],
        }
        self.summaries = {"PRC_2223020": "제안이유\n  방송 원문", "PRC_2223098": "제안이유 및 주요내용\n  발전법 원문",
                          "PRC_2223122": None}
        self.fail_summary = set()
        self.summary_calls = []
        self.auth_error = False


@pytest.fixture
def fake(monkeypatch):
    f = FakeApi()

    def search_bills(self, keyword, page_size=100, max_pages=50):
        if f.auth_error:
            raise na.AssemblyAuthError("국회 Open API 인증키 오류(ERROR-290): 인증키가 유효하지 않습니다.", "ERROR-290")
        return [dict(r) for r in f.rows.get(keyword, [])]

    def get_official_summary(self, bill_id):
        f.summary_calls.append(bill_id)
        if bill_id in f.fail_summary:
            raise na.AssemblyApiError("timeout")
        return f.summaries.get(bill_id)

    monkeypatch.setattr(na.NationalAssemblyClient, "search_bills", search_bills)
    monkeypatch.setattr(na.NationalAssemblyClient, "get_official_summary", get_official_summary)
    return f


def _conn(settings):
    return db.connect(settings.database_path)


def test_first_sync_inserts_and_dedupes(settings, fake):
    r = sync_service.run_sync(settings)
    assert r["status"] == "completed"
    assert r["total_found"] == 5
    assert r["related_found"] == 3            # 중복(2223098) 제거, 무관 의안 제외
    assert r["inserted"] == 3 and r["failed"] == 0
    conn = _conn(settings)
    b = db.get_bill(conn, "2223098")
    assert b["keywords"] == ["방송", "통신"]
    assert b["summary_text"] == "제안이유 및 주요내용\n  발전법 원문"   # 원문 그대로
    assert db.get_bill(conn, "2223122")["summary_status"] == "none"   # 국회 제공 내용 없음 → NULL
    assert db.get_bill(conn, "2223122")["summary_text"] is None
    assert db.get_bill(conn, "2229999") is None


def test_second_sync_unchanged_without_refetch(settings, fake):
    sync_service.run_sync(settings)
    fake.summary_calls.clear()
    r = sync_service.run_sync(settings)
    assert (r["inserted"], r["updated"], r["unchanged"]) == (0, 0, 3)
    assert fake.summary_calls == []   # 이미 받은 원문은 다시 요청하지 않음


def test_status_change_updates(settings, fake):
    sync_service.run_sync(settings)
    fake.rows["방송"][0] = list_row("2223020", "방송법 일부개정법률안", result="원안가결")
    r = sync_service.run_sync(settings)
    assert r["updated"] == 1 and r["updated_bills"][0]["bill_number"] == "2223020"
    assert db.get_bill(_conn(settings), "2223020")["proc_result"] == "원안가결"


def test_summary_failure_does_not_stop_sync_and_retries(settings, fake):
    fake.fail_summary.add("PRC_2223020")
    r = sync_service.run_sync(settings)
    assert r["status"] == "completed"
    assert r["inserted"] == 3 and r["failed"] == 1
    conn = _conn(settings)
    assert db.get_bill(conn, "2223020")["summary_status"] == "failed"
    assert db.get_bill(conn, "2223122")["summary_status"] == "none"
    # 다음 조사에서 실패한 것만 다시 시도
    fake.fail_summary.clear()
    fake.summary_calls.clear()
    r2 = sync_service.run_sync(settings)
    assert fake.summary_calls == ["PRC_2223020"]
    assert r2["failed"] == 0 and r2["updated"] == 1
    assert db.get_bill(_conn(settings), "2223020")["summary_text"] == "제안이유\n  방송 원문"


def test_auth_error_fails_sync(settings, fake):
    fake.auth_error = True
    r = sync_service.run_sync(settings)
    assert r["status"] == "failed"
    assert "ERROR-290" in r["error_message"] and "ASSEMBLY_API_KEY" in r["error_message"]
    assert db.last_sync(_conn(settings))["status"] == "failed"


def test_already_running(settings, fake):
    conn = _conn(settings)
    db.init_db(conn)
    assert db.try_start_sync(conn) is not None
    assert sync_service.run_sync(settings) == {"status": "already_running"}
