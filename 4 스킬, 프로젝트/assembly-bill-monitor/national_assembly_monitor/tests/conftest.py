import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    s = Settings()
    s.database_path = tmp_path / "test.db"
    s.keywords = ["방송", "통신", "시청각"]
    s.detail_delay_seconds = 0
    s.api_retry_waits = (0, 0)
    s.assembly_api_key = "test-key"
    return s


def list_row(no, name, result="", committee="과학기술정보방송통신위원회"):
    return {"BILL_NO": no, "BILL_ID": f"PRC_{no}", "BILL_NAME": name, "PROPOSER": "홍길동의원 등 10인",
            "PROPOSER_KIND": "의원", "PROPOSE_DT": "2026-11-20", "CURR_COMMITTEE": committee,
            "PROC_RESULT_CD": result, "LINK_URL": f"https://likms.assembly.go.kr/bill/billDetail.do?billId=PRC_{no}"}
