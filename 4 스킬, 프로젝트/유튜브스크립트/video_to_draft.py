#!/usr/bin/env python3
"""
영상 → 화면 캡처 + 전사 타임라인 생성기  v2 (2026-11-22)

목적:
    심의안건 '방송내용' 초안을 쓰기 위해, 로컬 방송 영상(mp4·wmv 등)에서
    ① 장면 전환 시점과 일정 간격의 프레임을 PNG로 저장하고
    ② Whisper 전사 결과(또는 사용자가 가진 외부 전사본)를 각 프레임 구간에 붙인 timeline.md를 만든다.
    Claude가 프레임 이미지를 보고 화면 자막·장면을 판독하고 <방송화면> 후보를 고른다.

v2 변경(2026-11-22): 긴 영상(1시간 등)용으로 두 가지를 추가했다. 옵션을 주지 않으면 v1과 같게 동작한다.
    --start/--end   영상의 일부 구간만 처리(프레임 추출은 해당 위치로 건너뛰어 읽고, Whisper도 그 구간만 인식)
    --transcript    클로바노트 등 외부 전사본(txt·srt)을 읽어 Whisper를 건너뜀

사용법 (이 파일이 있는 폴더에서):
    py -3.12 video_to_draft.py "영상경로.mp4"
    py -3.12 video_to_draft.py "영상경로.mp4" --interval 3 --scene-threshold 20
    py -3.12 video_to_draft.py "영상경로.mp4" --start 00:12:00 --end 00:15:30 --transcript 클로바.txt
    py -3.12 video_to_draft.py "영상경로.mp4" --start 00:12:40 --end 00:13:10 --interval 0.5 --min-gap 0.5 --width 480 --no-transcribe -d 임시폴더

시각은 초(90), 분:초(1:30), 시:분:초(01:02:03) 모두 가능하다.

출력 (기본: output\\<영상이름>\\):
    frames\\fNNN_HH-MM-SS.png   저장 프레임(파일명의 시각은 영상 전체 기준)
    <영상이름>.txt / <영상이름>_문단.txt   video_to_script.py와 같은 형식의 전사본(구간 지정 시 이름에 _구간 표시)
    timeline.md                프레임별 구간 + 해당 구간 전사

의존성: faster-whisper(및 그 의존 패키지 av, numpy). ffmpeg 별도 설치 불필요.
주의: av 19.x는 faster-whisper 1.2.1과 맞지 않는다(2026-11-22 확인, 18.1.1 사용).
video_to_script.py는 고치지 않고 함수만 가져다 쓴다.
"""
import argparse
import datetime as dt
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import video_to_script as vts  # noqa: E402

DEFAULT_OUTDIR = SCRIPT_DIR / "output"


def write_png(path: Path, rgb) -> None:
    """numpy RGB 배열(h, w, 3, uint8)을 PNG로 저장(Pillow 없이)."""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def ts_file(sec: float) -> str:
    return vts.fmt_ts(sec).replace(":", "-")


def parse_time(s: str) -> float:
    """'90', '1:30', '01:02:03', '00:12:00.5' → 초. 형식이 틀리면 ValueError."""
    parts = s.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(s)
    vals = [float(x) for x in parts]
    sec = 0.0
    for v in vals:
        sec = sec * 60 + v
    return sec


_TIME = r"(\d{1,3}(?::\d{2}){1,2})(?:[.,]\d+)?"
_RE_SPK = re.compile(rf"^\s*(\S.*?)\s+{_TIME}\s*$")            # 클로바노트: '참석자 1 00:03'
_RE_LEAD = re.compile(rf"^\s*[\[(]?{_TIME}[\])]?\s+(\S.*)$")   # '[00:00:03] 본문' (video_to_script 전사본도 읽힘)
_RE_SRT = re.compile(r"^(\d{2}:\d{2}:\d{2})[,.]\d+\s*-->\s*(\d{2}:\d{2}:\d{2})[,.]\d+")


def parse_external_transcript(path: Path):
    """클로바노트 등 외부 전사본(txt·srt)을 (start, end, text) 목록으로 읽는다. 반환: (segments, 설명).
    지원 형식: ① '화자 시:분:초' 줄 다음에 본문 ② '[시:분:초] 본문' ③ SRT. 시각이 없으면 SystemExit."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        sys.exit(f"전사본의 문자 인코딩을 읽을 수 없습니다(UTF-8·CP949 아님): {path}")
    lines = text.splitlines()
    items = []  # (start, text)
    if any(_RE_SRT.match(l.strip()) for l in lines):
        cur_t, buf = None, []
        for l in lines + [""]:
            m = _RE_SRT.match(l.strip())
            if m:
                cur_t, buf = parse_time(m.group(1)), []
            elif l.strip() == "":
                if cur_t is not None and buf:
                    items.append((cur_t, " ".join(buf)))
                cur_t, buf = None, []
            elif cur_t is not None:
                buf.append(l.strip())
        kind = "SRT"
    else:
        spk_hits = 0
        i, prev_blank = 0, True
        while i < len(lines):
            l = lines[i]
            m = _RE_SPK.match(l) if prev_blank else None
            if m and not _RE_LEAD.match(l):
                spk, t = m.group(1), parse_time(m.group(2))
                body = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    body.append(lines[i].strip())
                    i += 1
                if body:
                    items.append((t, f"{spk}: " + " ".join(body)))
                    spk_hits += 1
                prev_blank = True
                continue
            m = _RE_LEAD.match(l)
            if m:
                items.append((parse_time(m.group(1)), m.group(2).strip()))
            prev_blank = not l.strip()
            i += 1
        kind = "화자·시각 줄 형식" if spk_hits else "[시각] 본문 형식"
    if not items:
        sys.exit("외부 전사본에서 시각이 붙은 발화를 찾지 못했습니다. 시각(00:03 또는 00:00:03)이 있는 형식으로 내보내 주세요. "
                 f"({path})")
    items.sort(key=lambda x: x[0])
    segs = []
    for k, (t, tx) in enumerate(items):
        end = min(items[k + 1][0], t + 15.0) if k + 1 < len(items) else t + 10.0  # 끝 시각이 없으므로 다음 발화 시작과 15초 중 짧은 쪽
        segs.append((t, end, tx))
    return segs, f"외부 전사본 {path.name} ({kind}, 발화 {len(segs)}개). 화자 표기와 시각은 해당 서비스 값이다"


def transcribe_range(path: str, model_size: str, language, start: float, end):
    """구간만 Whisper로 인식한다. 반환: (segments, 설명). 시각은 영상 전체 기준.
    (faster-whisper의 clip_timestamps는 vad_filter와 함께 쓰면 구간이 무시되어, 오디오를 잘라 넘기고 시각에 start를 더한다.)"""
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio

    print(f"[Whisper:{model_size}] 구간 {vts.fmt_ts(start)}~{vts.fmt_ts(end) if end else '끝'} 음성 인식 중...")
    sr = 16000
    audio = decode_audio(path, sampling_rate=sr)
    # 짧은 조각(약 30초 미만)은 첫 문장 뒤를 잘라 먹는 경우가 있어(2026-11-22 시험), 앞뒤 5초 여유를 두고 최소 30초로 인식한 뒤 구간 안만 남긴다.
    total = len(audio) / sr
    lo = max(0.0, start - 5.0)
    hi = min(total, (end + 5.0) if end else total)
    if hi - lo < 30.0:
        hi = min(total, lo + 30.0)
    audio = audio[int(lo * sr): int(hi * sr)]

    def run(model):
        segs, info = model.transcribe(audio, language=language, vad_filter=True, condition_on_previous_text=False)
        keep = [(s.start + lo, s.end + lo, s.text) for s in segs]
        return [x for x in keep if x[0] >= start - 2.0 and (not end or x[0] <= end)], info

    try:
        model = WhisperModel(model_size, device="auto", compute_type="auto")
        segs, info = run(model)
    except Exception as e:
        print(f"[GPU 사용 실패 → CPU로 재시도] {type(e).__name__}: {e}")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segs, info = run(model)
    out = []
    for s0, s1, tx in segs:
        tx = tx.strip()
        if tx:
            out.append((s0, s1, tx))
            print(f"  [{vts.fmt_ts(s0)}] {tx}")
    return out, f"Whisper {model_size} 구간 음성 인식 (언어 {info.language}, 확률 {info.language_probability:.2f})"


def extract_frames(src: Path, frames_dir: Path, interval: float, threshold: float,
                   min_gap: float, max_frames: int, width: int, start: float = 0.0, end=None):
    """장면 전환 + 최대 간격 기준으로 프레임 저장. start·end(초)를 주면 그 구간만 읽는다. 반환: (frames, info)."""
    import av
    import numpy as np

    frames_dir.mkdir(parents=True, exist_ok=True)
    with av.open(str(src)) as c:
        vs = c.streams.video[0]
        vs.thread_type = "AUTO"
        duration = float(c.duration) / 1e6 if c.duration else 0.0
        src_w, src_h = vs.codec_context.width, vs.codec_context.height
        r_end = min(end, duration) if (end and duration) else (end or duration)
        span = (r_end - start) if r_end else duration
        # 프레임이 상한을 넘지 않도록 간격 조정(구간을 지정하면 구간 길이 기준)
        if span and max_frames:
            interval = max(interval, span / (max_frames / 2))
            min_gap = max(min_gap, span / max_frames)
        out_w = min(width, src_w) if width else src_w
        out_h = int(round(src_h * out_w / src_w / 2)) * 2
        if start > 0:
            c.seek(int(start * 1_000_000))  # 앞쪽 키프레임으로 건너뜀. 정확한 시작 위치는 아래에서 걸러 맞춘다

        frames, last_small, last_t = [], None, None
        for frame in c.decode(vs):
            if frame.time is None:
                continue
            t = float(frame.time)
            if t < start:
                continue
            if r_end and t > r_end:
                break
            small = frame.reformat(width=64, height=36, format="gray").to_ndarray().astype(np.int16)
            reason, diff = None, 0.0
            if last_small is None:
                reason = "시작"
            else:
                gap = t - last_t
                diff = float(np.abs(small - last_small).mean())
                if diff >= threshold and gap >= min_gap:
                    reason = "장면 전환"
                elif gap >= interval:
                    reason = "간격"
            if reason is None:
                continue
            n = len(frames) + 1
            name = f"f{n:03d}_{ts_file(t)}.png"
            rgb = frame.reformat(width=out_w, height=out_h, format="rgb24").to_ndarray()
            write_png(frames_dir / name, rgb)
            frames.append({"n": n, "t": t, "file": name, "reason": reason, "diff": diff})
            last_small, last_t = small, t

    info = {"duration": duration, "size": f"{src_w}x{src_h}", "interval": interval, "min_gap": min_gap,
            "start": start, "end": r_end if (start > 0 or end) else None}
    return frames, info


def build_timeline(frames, segments, info, meta, args, path: Path) -> None:
    dur = info["duration"]
    lines = [
        f"# 타임라인: {meta['title']}",
        "",
        f"- 원본: {meta['source']}",
        f"- 영상 길이: {vts.fmt_ts(dur)} / 해상도: {info['size']}",
        *([f"- 처리 구간: {vts.fmt_ts(info['start'])}~{vts.fmt_ts(info['end'])} (영상 전체가 아니다. 이 밖은 확인하지 않았다)"]
          if info.get("end") else []),
        f"- 전사: {meta['method']}",
        f"- 프레임: {len(frames)}장 (장면 전환 임계값 {args.scene_threshold}, 최대 간격 {info['interval']:.1f}초, "
        f"최소 간격 {info['min_gap']:.1f}초)",
        f"- 생성 일시: {meta['extracted_at']}",
        "- 주의: " + ("외부 전사본의 화자 표기와 시각은 해당 서비스 값이며, 화면과 1~2초 어긋날 수 있다. 인명은 자막과 대조한다."
                     if meta.get("external") else "기계 전사본이며 화자 구분이 없다. 인용할 대사는 원 영상과 대조한다."),
        "",
    ]
    if info.get("end"):  # 구간 지정이면 그 밖의 발화는 타임라인에 넣지 않는다
        lo, hi = info["start"] - 3.0, info["end"] + 3.0
        segments = [s for s in segments if s[1] >= lo and s[0] <= hi]
    for i, fr in enumerate(frames):
        start = fr["t"]
        end = frames[i + 1]["t"] if i + 1 < len(frames) else (info["end"] if info.get("end") else max(dur, start))
        own = [s for s in segments if start <= s[0] < end or (i == 0 and s[0] < start)]
        ongoing = [s for s in segments if s[0] < start and s[1] > start and s not in own]
        reason = fr["reason"] + (f", 차이 {fr['diff']:.1f}" if fr["reason"] == "장면 전환" else "")
        lines.append(f"## f{fr['n']:03d} · {vts.fmt_ts(start)} ({reason})")
        lines.append("")
        lines.append(f"![](frames/{fr['file']})")
        lines.append("")
        lines.append(f"전사({vts.fmt_ts(start)}~{vts.fmt_ts(end)}):")
        for s in ongoing:
            lines.append(f"- ↳ 이어지는 발화 [{vts.fmt_ts(s[0])}] {s[2][:40]}…")
        for s in own:
            lines.append(f"- [{vts.fmt_ts(s[0])}] {s[2]}")
        if not own and not ongoing:
            lines.append("- (전사 없음)")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    p = argparse.ArgumentParser(description="영상에서 프레임 캡처 + 전사 타임라인 생성")
    p.add_argument("source", help="로컬 영상 파일 경로(mp4·wmv 등)")
    p.add_argument("-m", "--model", default="medium", help="Whisper 모델(기본 medium)")
    p.add_argument("-l", "--language", default="ko", help="언어 코드(기본 ko)")
    p.add_argument("--interval", type=float, default=4.0, help="장면 전환이 없어도 프레임을 저장하는 최대 간격(초, 기본 4)")
    p.add_argument("--scene-threshold", type=float, default=30.0,
                   help="장면 전환 판정 기준(축소 회색조 평균 차이 0~255, 기본 30, 낮을수록 프레임 증가)")
    p.add_argument("--min-gap", type=float, default=1.0, help="프레임 사이 최소 간격(초, 기본 1)")
    p.add_argument("--max-frames", type=int, default=200, help="저장 프레임 상한(기본 200)")
    p.add_argument("--width", type=int, default=960, help="저장 PNG 폭(기본 960, 원본보다 크면 원본 크기)")
    p.add_argument("-d", "--outdir", default=str(DEFAULT_OUTDIR), help="출력 상위 폴더(기본: 스크립트 옆 output)")
    p.add_argument("--force", action="store_true", help="같은 이름의 출력 폴더가 있으면 묻지 않고 덮어씀")
    p.add_argument("--no-transcribe", action="store_true", help="전사 없이 프레임만 추출(설정 조정용)")
    p.add_argument("--start", help="처리 시작 시각(초, 분:초, 시:분:초). 긴 영상에서 쟁점 구간만 처리할 때")
    p.add_argument("--end", help="처리 끝 시각(같은 형식). 없으면 끝까지")
    p.add_argument("--transcript", help="외부 전사본(클로바노트 txt·srt 등). 주면 Whisper를 건너뛴다")
    args = p.parse_args()

    src = Path(args.source)
    if not src.exists():
        sys.exit(f"파일을 찾을 수 없습니다: {src}")
    try:
        t_start = parse_time(args.start) if args.start else 0.0
        t_end = parse_time(args.end) if args.end else None
    except ValueError as e:
        sys.exit(f"시각 형식이 맞지 않습니다: {e} (예: 90, 1:30, 01:02:03)")
    if t_end is not None and t_end <= t_start:
        sys.exit("--end는 --start보다 뒤여야 합니다.")
    ext_tr = Path(args.transcript) if args.transcript else None
    if ext_tr and not ext_tr.exists():
        sys.exit(f"전사본 파일을 찾을 수 없습니다: {ext_tr}")
    ranged = bool(args.start or args.end)
    # 구간을 지정하면 전체 처리 결과(같은 이름 폴더)를 지우지 않도록 구간 이름을 붙인 폴더에 저장한다
    tag = f"_구간{ts_file(t_start)}~{ts_file(t_end) if t_end else '끝'}" if ranged else ""
    out_dir = Path(args.outdir) / (src.stem + tag)
    if out_dir.exists():
        if not args.force:
            msg = f"출력 폴더가 이미 있습니다: {out_dir}"
            try:
                ans = input(f"{msg}\n덮어쓸까요? (y/N) ") if sys.stdin.isatty() else ""
            except EOFError:
                ans = ""
            if ans.strip().lower() != "y":
                sys.exit(f"중단했습니다. 덮어쓰려면 --force를 붙이세요. ({msg})")
        shutil.rmtree(out_dir / "frames", ignore_errors=True)

    meta = {"extracted_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": str(src.resolve()), "title": src.stem + tag}

    print("[프레임 추출 중...]")
    frames, info = extract_frames(src, out_dir / "frames", args.interval, args.scene_threshold,
                                  args.min_gap, args.max_frames, args.width, t_start, t_end)
    meta["duration"] = vts.fmt_ts(info["duration"])
    if ranged and not frames:
        sys.exit("지정한 구간에서 프레임을 찾지 못했습니다. 시각이 영상 길이 안인지 확인하세요.")
    by = {}
    for f in frames:
        by[f["reason"]] = by.get(f["reason"], 0) + 1
    print(f"  프레임 {len(frames)}장 저장 ({', '.join(f'{k} {v}' for k, v in by.items())})")

    segments = []
    if args.no_transcribe:
        meta["method"] = "전사 생략(--no-transcribe)"
    elif ext_tr:
        segments, meta["method"] = parse_external_transcript(ext_tr)
        meta["external"] = True
        print(f"  {meta['method']}")
    else:
        if ranged:
            segments, meta["method"] = transcribe_range(str(src), args.model, args.language, t_start, t_end)
            save_stem = src.stem + tag
        else:
            segments, meta["method"] = vts.transcribe_with_whisper(str(src), args.model, args.language)
            save_stem = src.stem
        if segments:
            vts.save(segments, out_dir / save_stem, meta, with_srt=False)
        else:
            print("[경고] 추출된 전사가 없습니다. 타임라인은 프레임만으로 만듭니다.")

    tl = out_dir / "timeline.md"
    build_timeline(frames, segments, info, meta, args, tl)
    print(f"저장 완료: {tl}")


if __name__ == "__main__":
    main()
