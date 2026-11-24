#!/usr/bin/env python3
"""
영상에서 스크립트(자막/대본) 추출기  v2 (2026-11-19)

사용법 (Windows PowerShell, 이 파일이 있는 폴더에서):
    py -3.12 video_to_script.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
    py -3.12 video_to_script.py "https://youtu.be/XXXXXXXXXXX" --whisper -m medium
    py -3.12 video_to_script.py 내영상.mp4 -l ko --srt

설치 (한 번만):
    py -3.12 -m pip install -U faster-whisper youtube-transcript-api yt-dlp

동작 방식:
    - YouTube 링크 -> 등록된 자막(수동 자막 우선, 없으면 자동 생성 자막)을 가져오고,
                      자막이 없거나 가져오지 못하면 오디오를 내려받아 Whisper로 인식
    - 로컬 파일    -> Whisper(faster-whisper)로 음성 인식

출력 (기본 위치: 이 파일 옆 output 폴더):
    <이름>.txt       구간별 타임스탬프 원본(인용 위치 확인용)
    <이름>_문단.txt  약 30초 단위로 묶은 본문(분석·요약용, 분량이 적음)
    <이름>.srt       --srt 옵션을 준 경우
    두 txt 파일 맨 위에 제목·채널·게시일·추출 방식 등 메타데이터가 붙습니다.
"""
import argparse
import datetime as dt
import re
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTDIR = SCRIPT_DIR / "output"


def fmt_ts(sec: float, srt: bool = False) -> str:
    total_ms = int(round(sec * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract_video_id(url: str):
    m = re.search(r"(?:[?&]v=|youtu\.be/|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def safe_name(text: str, limit: int = 40) -> str:
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", text or "").strip(" .")
    text = re.sub(r"\s+", " ", text)
    return text[:limit].rstrip(" .")


def youtube_info(url: str) -> dict:
    """제목·채널·게시일·길이. 실패해도 진행한다."""
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        d = info.get("upload_date") or ""
        return {
            "title": info.get("title") or "",
            "channel": info.get("channel") or info.get("uploader") or "",
            "upload_date": f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else "",
            "duration": fmt_ts(info["duration"]) if info.get("duration") else "",
        }
    except Exception as e:
        print(f"[영상 정보 조회 실패] {type(e).__name__}: {e}")
        return {}


def youtube_captions(video_id: str, languages):
    """YouTube 등록 자막. 반환: (segments, 설명) 또는 (None, None)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=languages)
        segs = [(s.start, s.start + s.duration, s.text.replace("\n", " ").strip()) for s in fetched]
        segs = [s for s in segs if s[2]]
        kind = "자동 생성 자막" if fetched.is_generated else "수동 등록 자막"
        desc = f"YouTube {kind} ({fetched.language_code})"
        print(f"[자막] {desc}, {len(segs)}구간")
        return segs, desc
    except Exception as e:
        print(f"[자막 가져오기 실패] {type(e).__name__}: 오디오 인식으로 전환합니다.")
        return None, None


def download_audio(url: str, out_dir: str) -> str:
    import yt_dlp

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(out_dir) / "audio.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    print("[오디오 다운로드 중...]")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def transcribe_with_whisper(path: str, model_size: str, language):
    """음성 인식. 비디오 파일도 그대로 입력 가능(오디오 자동 추출). 반환: (segments, 설명)."""
    from faster_whisper import WhisperModel

    print(f"[Whisper:{model_size}] 음성 인식 중... (처음 실행 시 모델 다운로드로 오래 걸릴 수 있습니다)")
    try:
        model = WhisperModel(model_size, device="auto", compute_type="auto")
        segments, info = model.transcribe(path, language=language, vad_filter=True)
    except Exception as e:  # GPU 라이브러리(cuDNN 등) 누락 시 CPU로 재시도
        print(f"[GPU 사용 실패 → CPU로 재시도] {type(e).__name__}: {e}")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(path, language=language, vad_filter=True)
    print(f"감지된 언어: {info.language} (확률 {info.language_probability:.2f})")

    result = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        result.append((seg.start, seg.end, text))
        print(f"  [{fmt_ts(seg.start)}] {text}")
    desc = f"Whisper {model_size} 음성 인식 (언어 {info.language}, 확률 {info.language_probability:.2f})"
    return result, desc


def to_paragraphs(segments, window: float = 30.0):
    """구간을 약 window초 단위 문단으로 묶는다."""
    paras, cur, cur_start = [], [], None
    for start, _, text in segments:
        if cur_start is None:
            cur_start = start
        elif start - cur_start >= window:
            paras.append((cur_start, " ".join(cur)))
            cur, cur_start = [], start
        cur.append(text)
    if cur:
        paras.append((cur_start, " ".join(cur)))
    return paras


def header_lines(meta: dict) -> str:
    rows = [
        ("제목", meta.get("title")),
        ("채널", meta.get("channel")),
        ("게시일", meta.get("upload_date")),
        ("영상 길이", meta.get("duration")),
        ("출처", meta.get("source")),
        ("추출 방식", meta.get("method")),
        ("추출 일시", meta.get("extracted_at")),
    ]
    out = [f"# {k}: {v}" for k, v in rows if v]
    out.append("# 주의: 자동 생성 자막·음성 인식 결과는 기계 전사본이므로, 인용할 대사는 원 영상과 대조해야 합니다.")
    return "\n".join(out) + "\n\n"


def save(segments, out_base: Path, meta: dict, with_srt: bool):
    out_base.parent.mkdir(parents=True, exist_ok=True)
    head = header_lines(meta)

    def path(suffix: str) -> Path:  # 이름에 점이 있어도 잘리지 않도록 직접 붙인다
        return out_base.parent / (out_base.name + suffix)

    txt_path = path(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(head)
        for start, _, text in segments:
            f.write(f"[{fmt_ts(start)}] {text}\n")

    para_path = path("_문단.txt")
    with open(para_path, "w", encoding="utf-8") as f:
        f.write(head)
        for start, text in to_paragraphs(segments):
            f.write(f"[{fmt_ts(start)}] {text}\n\n")

    print(f"\n저장 완료: {txt_path}")
    print(f"저장 완료: {para_path}")

    if with_srt:
        srt_path = path(".srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, (start, end, text) in enumerate(segments, 1):
                f.write(f"{i}\n{fmt_ts(start, True)} --> {fmt_ts(end, True)}\n{text}\n\n")
        print(f"저장 완료: {srt_path}")

    chars = sum(len(t) for _, _, t in segments)
    print(f"[요약] 구간 {len(segments)}개, 본문 약 {chars:,}자, 방식: {meta.get('method')}")


def main():
    for stream in (sys.stdout, sys.stderr):  # Windows에서 출력 리다이렉트 시 한글 깨짐 방지
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    p = argparse.ArgumentParser(description="영상에서 스크립트 추출")
    p.add_argument("source", help="영상 파일 경로 또는 YouTube URL")
    p.add_argument("-l", "--language", default=None, help="언어 코드(예: ko, en). 생략하면 자막은 ko→en 순, Whisper는 자동 감지")
    p.add_argument("-m", "--model", default="medium",
                   help="Whisper 모델: tiny/base/small/medium/large-v3 (기본 medium, 클수록 정확하지만 느림)")
    p.add_argument("-o", "--output", default=None, help="출력 파일 이름(확장자 제외)")
    p.add_argument("-d", "--outdir", default=str(DEFAULT_OUTDIR), help="출력 폴더(기본: 스크립트 옆 output)")
    p.add_argument("--whisper", action="store_true", help="YouTube 자막이 있어도 Whisper 음성 인식 사용")
    p.add_argument("--srt", action="store_true", help="SRT 자막 파일도 생성")
    args = p.parse_args()

    segments, method = None, None
    meta = {"extracted_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    outdir = Path(args.outdir)

    if args.source.startswith(("http://", "https://")):
        vid = extract_video_id(args.source)
        meta.update(youtube_info(args.source))
        meta["source"] = f"https://www.youtube.com/watch?v={vid}" if vid else args.source
        langs = [args.language] if args.language else ["ko", "en"]
        if vid and not args.whisper:
            segments, method = youtube_captions(vid, langs)
        if segments is None:
            with tempfile.TemporaryDirectory() as tmp:
                audio = download_audio(args.source, tmp)
                segments, method = transcribe_with_whisper(audio, args.model, args.language)
        default_name = "_".join(x for x in (
            meta.get("upload_date", "").replace("-", ""), safe_name(meta.get("title", "")), vid or "youtube"
        ) if x)
    else:
        src = Path(args.source)
        if not src.exists():
            sys.exit(f"파일을 찾을 수 없습니다: {src}")
        meta["source"] = str(src.resolve())
        meta["title"] = src.stem
        segments, method = transcribe_with_whisper(str(src), args.model, args.language)
        default_name = src.stem

    if not segments:
        sys.exit("추출된 스크립트가 없습니다.")
    meta["method"] = method
    save(segments, outdir / (args.output or default_name), meta, args.srt)


if __name__ == "__main__":
    main()
