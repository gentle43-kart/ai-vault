from app.services.search_service import contains_keyword, matched_keywords

KW = ["방송", "통신", "시청각"]


def test_broadcast_match():
    assert matched_keywords("방송법 일부개정법률안", KW) == ["방송"]


def test_telecom_match():
    assert matched_keywords("전기통신사업법 일부개정법률안", KW) == ["통신"]


def test_multiple_match():
    assert matched_keywords("방송통신발전 기본법 일부개정법률안", KW) == ["방송", "통신"]


def test_unrelated_excluded():
    assert matched_keywords("소득세법 일부개정법률안", KW) == []


def test_english_case_insensitive():
    assert contains_keyword("ott 사업자 지원법안", "OTT")
    assert not contains_keyword(None, "방송")
