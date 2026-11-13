# 목적: 지정 연도(기본 2019, 2020년분은 인자 2020) 전체회의 의결서 PDF(텍스트 추출 가능 파일)를 md로 기계 변환한다(AGENTS_절차.md 6.7절).
#       pdfplumber 추출 결과를 쪽 단위로 이어 붙이고, 쪽 구분 주석과 사건·절 제목만 추가한다. 원문은 요약·수정하지 않는다.
# 입력: E:\...\전체회의 의결서(모음_자료용)\AI 크롤링 결과물(출범~ )_업데이트 중\텍스트 추출 가능\{연도}년*.pdf (읽기만)
# 출력: J:\AI 자료\1 documents_md\회의록_md\전체회의_md\의결서_md\{연도}\{원본 파일명에서 확장자만 .md}
#       같은 이름이 있으면 덮어쓰지 않고 건너뛴다. 점검 결과는 표준출력으로만 낸다.
# 검증: 쪽 수 = 쪽 주석 수, 의결번호 수, 깨진 글자(U+FFFD·사용자 정의 영역) 비율, 추가 줄 제거 시 원문 글자 수 일치
# 실행: python convert_decisions.py [연도] [--dry]   (--dry: 파일을 쓰지 않고 점검만)
import sys, re, glob, os, datetime
import pdfplumber

SRC = r"E:/1 대구사무소/01-심의/00 회의자료/01.전체회의/전체회의 의결서(모음_자료용)/AI 크롤링 결과물(출범~ )_업데이트 중/텍스트 추출 가능/"
YEAR = next((a for a in sys.argv[1:] if a.isdigit()), "2019")   # 연도 인자(기본 2019)
DST = r"J:/AI 자료/1 documents_md/회의록_md/전체회의_md/의결서_md/" + YEAR + "/"
DRY = "--dry" in sys.argv

re_case = re.compile(r"^\s*의결번호\s*:\s*(제?\s*\d{4}-\S+?호)")
re_sec = {"주 문": "주문", "이 유": "이유"}
re_art = re.compile(r"제\d+조")
bad = re.compile("[\ufffd\ue000-\uf8ff]")

def convert(path):
    name = os.path.basename(path)
    out = []
    added = 0
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        raw_chars = 0
        for i, pg in enumerate(pdf.pages, 1):
            t = (pg.extract_text() or "").replace("\x00", " ")   # 일부 PDF는 공백 글리프가 NUL로 추출된다(쪽 꼬리말)
            raw_chars += len(re.sub(r"\s", "", t))
            out.append(f"<!-- p.{i} -->")
            for line in t.split("\n"):
                m = re_case.match(line)
                if m:
                    out.append(f"## ■ {m.group(1).replace(' ', '')}")
                    added += 1
                elif line.strip() in re_sec:
                    out.append(f"### {re_sec[line.strip()]}")
                    added += 1
                out.append(line)
            out.append("")
    head = [f"<!-- 원본: {name} | 변환: pdfplumber | 변환일: {datetime.date.today()} | 쪽 주석과 제목(##·###)만 추가, 본문은 원문 그대로 -->", ""]
    body = "\n".join(head + out)
    return name, body, n, raw_chars

def check(body, n, raw_chars):
    pages = len(re.findall(r"^<!-- p\.\d+ -->$", body, re.M))
    plain = [l for l in body.split("\n") if not l.startswith(("<!--", "## ", "### "))]
    chars = len(re.sub(r"\s", "", "\n".join(plain)))
    # 제목으로 추가한 줄은 제외했으므로 원문 글자 수와 같아야 한다
    cases = len(re.findall(r"^## ■", body, re.M))
    return pages == n, chars == raw_chars, cases, len(bad.findall(body)), len(re_art.findall(body))

if not DRY:
    os.makedirs(DST, exist_ok=True)
files = sorted(glob.glob(SRC + YEAR + "년*.pdf"))
print("대상", len(files))
tot = {"ok": 0, "skip": 0}
for p in files:
    name, body, n, raw = convert(p)
    outp = DST + os.path.splitext(name)[0] + ".md"
    pg_ok, ch_ok, cases, badc, arts = check(body, n, raw)
    if cases == 0 or arts == 0:
        # 숫자·따옴표 등이 추출되지 않은 파일(글꼴 인코딩 문제)은 변환하지 않고 보고한다
        print(f"제외(숫자·조문 추출 실패): {name} 쪽={n}"); tot["skip"] += 1; continue
    if not DRY:
        if os.path.exists(outp):
            print("건너뜀(이미 있음):", name); tot["skip"] += 1; continue
        with open(outp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
    tot["ok"] += 1
    print(f"{name[:50]:50s} 쪽={n:3d} 쪽주석{'OK' if pg_ok else 'NG'} 글자{'OK' if ch_ok else 'NG'} 사건={cases:3d} 조문={arts:4d} 깨진={badc}")
print(tot)
