# -*- coding: utf-8 -*-
"""
방송미디어통신심의위원회(KOCSC) 회의록 다운로더

대상 게시판 (2026-07-30 기준, 실제 사이트 조회로 구조 확인함):
  1) 알림마당 > 위원회회의 > 회의록                    (bbsId=Records_main)
     -> 첨부파일 2개(의결서/발언내용) 중 "발언내용" 파일만 다운로드.
  2) 알림마당 > 소위원회 회의 > 방송심의소위원회 회의록 (bbsId=Broadcst_SCommittee_main)
  3) 알림마당 > 소위원회 회의 > 통신심의소위원회 회의록 (bbsId=Communication_SCommittee_main)
  4) 알림마당 > 소위원회 회의 > 광고심의소위원회 회의록 (bbsId=Advertisement_SCommittee_main)
     -> 2~4번은 첨부파일(회의록 PDF)을 그대로 다운로드.

실행 방식:
  - 인자 없이 실행하면 기존과 동일하게 대화형으로 입력받는다 (input()).
  - --boards / --start / --end 중 하나라도 넘기면 비대화형 모드로 동작한다.
    (Claude/Cowork 등 자동화 환경에서 사용하는 모드)

    예) python kocsc_downloader.py --boards 1,2 --start 2026-01-01 --end 2026-07-29
        python kocsc_downloader.py --boards all --start 2026-08-01 --end 2026-08-31

*** 확인된 사이트 구조 ***

1) 목록 조회
   GET https://www.kocsc.or.kr/cop/bbs/selectBoardList.do?bbsId={bbsId}&pageIndex={n}
   -> 응답은 HTML. 각 <tr> 안에:
      - td.title 안의 <a onclick="fn_inqire_notice('nttId','bbsId'); return false;">제목</a>
      - 그 다음 <td>등록일(YYYY-MM-DD)</td>
      - td.atta 안에 fn_downFile(...) 링크가 있으면 첨부파일 존재 (단, 목록 단계에는
        PDF 아이콘만 있고 실제 파일명은 없음 -> 파일명은 상세페이지에서 확인해야 함)
   -> 이 게시판들에는 서버 측 기간 검색 필드가 없음. 목록이 최신순 정렬이라는 가정 하에
      파이썬에서 등록일을 직접 비교해서 필터링하고, 기간보다 오래된 글이 페이지의 절반을
      넘으면 더 이상 뒤지지 않고 종료한다.

2) 상세 조회 (첨부파일 실제 파일명 확인용)
   GET https://www.kocsc.or.kr/cop/bbs/selectBoardArticle.do?bbsId={bbsId}&nttId={nttId}
   -> <a onclick="fn_downFile('atchFileId','fileSn')">실제파일명.pdf</a> 형태로
      실제 파일명이 링크 텍스트에 그대로 노출됨.

3) 첨부파일 다운로드
   GET https://www.kocsc.or.kr/cmm/fms/FileDown.do?atchFileId=...&fileSn=...
   -> 실제 파일명은 응답 Content-Disposition 헤더에서도 추출 가능(안전장치).
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ------------------------------------------------------------------
# 설정값 - 대화형 모드에서 사용할 기본값 (비대화형 모드에서는 --start/--end로 대체됨)
# ------------------------------------------------------------------

BASE_URL = "https://www.kocsc.or.kr"
LIST_URL = f"{BASE_URL}/cop/bbs/selectBoardList.do"
ARTICLE_URL = f"{BASE_URL}/cop/bbs/selectBoardArticle.do"
FILE_DOWN_URL = f"{BASE_URL}/cmm/fms/FileDown.do"

START_DATE = "2026-01-01"          # 기간 시작일 (YYYY-MM-DD), 이 값 이상
END_DATE = "2026-07-29"            # 기간 종료일 (YYYY-MM-DD), 이 값 이하

OUTPUT_DIR = "./downloads"


def filter_records_attachments(attachments):
    """회의록(전체회의) 게시판: '발언내용' 파일만, 없으면 '의결서'가 아닌 첫 파일."""
    speech_files = [a for a in attachments if "발언내용" in a["filename"]]
    if speech_files:
        return speech_files
    fallback = [a for a in attachments if "의결서" not in a["filename"]]
    return fallback[:1]


def filter_all_attachments(attachments):
    """방송심의소위원회 회의록 게시판: 첨부파일을 전부 다운로드."""
    return attachments


BOARD_DEFS = [
    {
        "key": "1",
        "name": "위원회회의 회의록",
        "bbsId": "Records_main",
        "subdir": "전체회의 회의록",
        "attachment_filter": filter_records_attachments,
    },
    {
        "key": "2",
        "name": "방송심의소위원회 회의록",
        "bbsId": "Broadcst_SCommittee_main",
        "subdir": "방송심의소위원회_회의록",
        "attachment_filter": filter_all_attachments,
    },
    {
        "key": "3",
        "name": "통신심의소위원회 회의록",
        "bbsId": "Communication_SCommittee_main",
        "subdir": "통신심의소위원회_회의록",
        "attachment_filter": filter_all_attachments,
    },
    {
        "key": "4",
        "name": "광고심의소위원회 회의록",
        "bbsId": "Advertisement_SCommittee_main",
        "subdir": "광고심의소위원회_회의록",
        "attachment_filter": filter_all_attachments,
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
}

session = requests.Session()
session.headers.update(HEADERS)


# ------------------------------------------------------------------
# 1. 게시판 목록 조회 + 파싱 (제목/날짜/첨부파일 유무)
# ------------------------------------------------------------------
def fetch_list_page(bbs_id: str, page: int = 1) -> str:
    params = {"bbsId": bbs_id, "pageIndex": str(page)}
    resp = session.get(LIST_URL, params=params, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_list_page(html: str, bbs_id: str):
    """
    목록 페이지 HTML에서 각 행(row)의 제목/nttId/등록일/첨부파일 유무를 추출.
    """
    posts = []
    soup = BeautifulSoup(html, "html.parser")

    title_links = soup.find_all("a", onclick=re.compile(r"fn_inqire_notice"))

    for link in title_links:
        row = link.find_parent("tr")
        if row is None:
            continue

        onclick = link.get("onclick", "")
        m = re.search(r"fn_inqire_notice\('([^']+)'\s*,\s*'([^']+)'\)", onclick)
        if not m:
            continue
        ntt_id, row_bbs_id = m.group(1), m.group(2)
        title = link.get_text(strip=True)

        tds = row.find_all("td")
        date_str = None
        for td in tds:
            text = td.get_text(strip=True)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                date_str = text
                break

        has_attachment = bool(row.find("a", onclick=re.compile(r"fn_downFile")))

        posts.append(
            {
                "nttId": ntt_id,
                "bbsId": row_bbs_id or bbs_id,
                "title": title,
                "date": date_str,
                "has_attachment": has_attachment,
            }
        )

    return posts


def in_date_range(date_str: str, start_date: str, end_date: str) -> bool:
    if not date_str:
        return False
    d = datetime.strptime(date_str, "%Y-%m-%d")
    s = datetime.strptime(start_date, "%Y-%m-%d")
    e = datetime.strptime(end_date, "%Y-%m-%d")
    return s <= d <= e


# ------------------------------------------------------------------
# 2. 상세 페이지에서 첨부파일(실제 파일명) 조회
# ------------------------------------------------------------------
def fetch_detail_attachments(bbs_id: str, ntt_id: str):
    params = {"bbsId": bbs_id, "nttId": ntt_id}
    resp = session.get(ARTICLE_URL, params=params, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    attachments = []
    for link in soup.find_all("a", onclick=re.compile(r"fn_downFile")):
        m = re.search(r"fn_downFile\('([^']+)'\s*,\s*'([^']*)'\)", link.get("onclick", ""))
        if not m:
            continue
        atch_file_id, file_sn = m.group(1), m.group(2)
        filename = link.get_text(strip=True)
        if not filename:
            continue
        attachments.append(
            {
                "filename": filename,
                "url": f"{FILE_DOWN_URL}?atchFileId={atch_file_id}&fileSn={file_sn}",
            }
        )
    return attachments


# ------------------------------------------------------------------
# 3. 파일 다운로드 (이미 받은 파일은 스킵)
# ------------------------------------------------------------------
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def download_file(url: str, filename: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, sanitize_filename(filename))

    if os.path.exists(filepath):
        print(f"    스킵(이미 존재): {filepath}")
        return filepath

    resp = session.get(url, timeout=30, stream=True)
    resp.raise_for_status()

    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
    if m:
        header_filename = requests.utils.unquote(m.group(1))
        filepath = os.path.join(out_dir, sanitize_filename(header_filename))
        if os.path.exists(filepath):
            print(f"    스킵(이미 존재): {filepath}")
            return filepath

    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"    다운로드 완료: {filepath}")
    return filepath


# ------------------------------------------------------------------
# 실행 전 사용자 입력 (대화형 모드에서만 사용)
# ------------------------------------------------------------------
def prompt_board_selection():
    print("다운로드할 회의록 유형을 선택하세요.")
    for b in BOARD_DEFS:
        print(f"  {b['key']}. {b['name']}")
    print("  0. 전체")

    raw = input("번호 입력 (여러 개는 쉼표로 구분, 기본값=0 전체): ").strip()
    if not raw or raw == "0":
        return BOARD_DEFS

    keys = {k.strip() for k in raw.split(",") if k.strip()}
    selected = [b for b in BOARD_DEFS if b["key"] in keys]
    if not selected:
        print("올바른 선택이 없어 전체 유형을 대상으로 진행합니다.")
        return BOARD_DEFS
    return selected


def prompt_date(label: str, default: str) -> str:
    while True:
        raw = input(f"{label} (YYYY-MM-DD, 기본값={default}): ").strip()
        if not raw:
            return default
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print("날짜 형식이 올바르지 않습니다. 예: 2026-01-01")


# ------------------------------------------------------------------
# 비대화형 모드 (CLI 인자 / 자동화 실행용)
# ------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="KOCSC 회의록 다운로더 (인자를 하나도 주지 않으면 기존처럼 대화형으로 실행됨)"
    )
    parser.add_argument(
        "--boards",
        help="다운로드할 게시판 키. 쉼표로 구분 (예: 1,2). '0' 또는 'all'이면 전체.",
    )
    parser.add_argument("--start", help="시작일 YYYY-MM-DD")
    parser.add_argument("--end", help="종료일 YYYY-MM-DD")
    parser.add_argument("--output-dir", help="다운로드 저장 폴더 (기본값: ./downloads)")
    return parser.parse_args()


def select_boards_from_arg(raw: str):
    raw = (raw or "").strip()
    if not raw or raw == "0" or raw.lower() == "all":
        return BOARD_DEFS
    keys = {k.strip() for k in raw.split(",") if k.strip()}
    selected = [b for b in BOARD_DEFS if b["key"] in keys]
    if not selected:
        valid_keys = ", ".join(b["key"] for b in BOARD_DEFS)
        raise ValueError(f"알 수 없는 게시판 키: '{raw}' (사용 가능: {valid_keys}, 0, all)")
    return selected


def validate_date(label: str, value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{label} 형식이 올바르지 않습니다: '{value}' (예: 2026-01-01)")
    return value


# ------------------------------------------------------------------
# 메인 실행
# ------------------------------------------------------------------
def crawl_board(board: dict, start_date: str, end_date: str, output_dir: str):
    bbs_id = board["bbsId"]
    print(f"\n=== {board['name']} (bbsId={bbs_id}) ===")
    print(f"기간: {start_date} ~ {end_date}")

    page = 1
    matched_posts = []
    stop = False

    while not stop:
        html = fetch_list_page(bbs_id, page=page)
        posts = parse_list_page(html, bbs_id)
        if not posts:
            print(f"{page}페이지에 결과 없음 - 목록 조회 종료")
            break

        print(f"{page}페이지: {len(posts)}건 확인")

        older_than_range_count = 0
        for post in posts:
            if post["date"] and in_date_range(post["date"], start_date, end_date):
                matched_posts.append(post)
            elif post["date"]:
                d = datetime.strptime(post["date"], "%Y-%m-%d")
                s = datetime.strptime(start_date, "%Y-%m-%d")
                if d < s:
                    older_than_range_count += 1

        # 게시판이 최신순 정렬이라고 가정: 기간보다 오래된 글이
        # 페이지의 절반 이상이면 더 이상 뒤져도 소용없다고 보고 종료
        if older_than_range_count >= len(posts) / 2 and page > 1:
            stop = True

        page += 1
        if page > 100:  # 안전장치
            break
        time.sleep(0.3)

    print(f"조건에 맞는 게시글 {len(matched_posts)}건 발견")

    out_dir = os.path.join(output_dir, board["subdir"])
    downloaded = 0
    for post in matched_posts:
        print(f"- [{post['date']}] {post['title']} (nttId={post['nttId']})")
        if not post["has_attachment"]:
            print("    첨부파일 없음")
            continue

        attachments = fetch_detail_attachments(post["bbsId"], post["nttId"])
        attachments = board["attachment_filter"](attachments)
        if not attachments:
            print("    조건에 맞는 첨부파일 없음")
            continue

        for att in attachments:
            download_file(att["url"], att["filename"], out_dir)
            downloaded += 1
        time.sleep(0.3)

    return len(matched_posts), downloaded


def main():
    args = parse_args()
    non_interactive = bool(args.boards or args.start or args.end)

    if non_interactive:
        boards = select_boards_from_arg(args.boards) if args.boards else BOARD_DEFS
        start_date = validate_date("--start", args.start) if args.start else START_DATE
        end_date = validate_date("--end", args.end) if args.end else END_DATE
    else:
        boards = prompt_board_selection()
        start_date = prompt_date("시작일", START_DATE)
        end_date = prompt_date("종료일", END_DATE)

    output_dir = args.output_dir or OUTPUT_DIR

    summary = []
    for board in boards:
        matched, downloaded = crawl_board(board, start_date, end_date, output_dir)
        summary.append((board["name"], matched, downloaded))

    print("\n=== 전체 완료 ===")
    for name, matched, downloaded in summary:
        print(f"- {name}: 게시글 {matched}건, 첨부파일 {downloaded}건 다운로드/확인")


if __name__ == "__main__":
    main()
