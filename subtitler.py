import os
import re
import subprocess
import imageio_ffmpeg

ASS_COLORS = [
    "&H00FFFFFF",
    "&H0000E6FF",
    "&H0014FF39",
]

FONT_FILE_MAP = {
    "Luckiest Guy": "LuckiestGuy-Regular.ttf",
    "Anton": "Anton-Regular.ttf",
    "Bangers": "Bangers-Regular.ttf",
    "Montserrat": "Montserrat-Black.ttf",
    "Poppins": "Poppins-Black.ttf",
    "Oswald": "Oswald-Bold.ttf",
    "Bebas Neue": "BebasNeue-Regular.ttf",
    "Rubik": "Rubik-Black.ttf",
    "Permanent Marker": "PermanentMarker-Regular.ttf",
    "Titan One": "TitanOne-Regular.ttf",
}

_WHISPER_MODEL = None


def _get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def _format_srt_time(sec: float) -> str:
    sec = max(0.0, sec)
    hours = int(sec // 3600)
    minutes = int((sec % 3600) // 60)
    seconds = int(sec % 60)
    millis = int(round((sec - int(sec)) * 1000))
    if millis >= 1000:
        seconds += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def transcribe_audio_to_srt(
    video_path: str,
    srt_output_path: str,
    offset_sec: float = 0.0,
) -> str | None:
    if not video_path or not os.path.isfile(video_path):
        return None

    model = _get_whisper_model()
    if model is None:
        print("[Subtitler] 'faster-whisper' is not installed. Run: pip install faster-whisper")
        return None

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    base_no_ext = os.path.splitext(srt_output_path)[0]
    wav_path = f"{base_no_ext}_speech.wav"

    print("[Subtitler] Detecting speaker voice & transcribing audio automatically...")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        video_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-af",
        "silenceremove=start_periods=1:start_threshold=-40dB:detection=peak",
        wav_path,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    audio_input = (
        wav_path
        if (res.returncode == 0 and os.path.isfile(wav_path) and os.path.getsize(wav_path) > 1000)
        else video_path
    )

    segments, _ = model.transcribe(
        audio_input,
        beam_size=3,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=250),
    )

    srt_blocks = []
    idx = 1
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        start_t = max(0.0, float(seg.start) + float(offset_sec))
        end_t = max(start_t + 0.2, float(seg.end) + float(offset_sec))
        srt_blocks.append(f"{idx}\n{_format_srt_time(start_t)} --> {_format_srt_time(end_t)}\n{text}\n")
        idx += 1

    if os.path.isfile(wav_path):
        try:
            os.remove(wav_path)
        except OSError:
            pass

    if not srt_blocks:
        print("[Subtitler] No clear speech detected in audio.")
        return None

    with open(srt_output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_blocks))

    print(f"[Subtitler] Generated automatic speech captions ({len(srt_blocks)} lines): {srt_output_path}")
    return srt_output_path


def _timestamp_to_seconds(ts: str) -> float:
    cleaned = ts.strip().replace(".", ",")
    hours, minutes, sec_ms = cleaned.split(":")
    if "," in sec_ms:
        seconds, millis = sec_ms.split(",", 1)
    else:
        seconds, millis = sec_ms, "0"
    millis = (millis + "000")[:3]
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000.0


def _seconds_to_ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    hours = int(sec // 3600)
    minutes = int((sec % 3600) // 60)
    seconds = int(sec % 60)
    centis = int(round((sec - int(sec)) * 100))
    if centis >= 100:
        seconds += 1
        centis = 0
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"


def _resolve_chunky_font(font_name: str = "Luckiest Guy", fonts_dir: str = "fonts") -> str:
    chosen = font_name if font_name in FONT_FILE_MAP else "Luckiest Guy"
    expected_file = FONT_FILE_MAP[chosen]
    local_ttf = os.path.join(fonts_dir, expected_file)
    win_dir = os.environ.get("WINDIR", "C:\\Windows")
    windows_fonts = os.path.join(win_dir, "Fonts")

    if (os.path.isfile(local_ttf) and os.path.getsize(local_ttf) > 10000) or os.path.isfile(
        os.path.join(windows_fonts, expected_file)
    ):
        return chosen
    return "Arial Black"


def parse_srt(srt_path: str) -> list[dict]:
    if not srt_path or not os.path.isfile(srt_path):
        return []

    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().strip()

    if not content:
        return []

    blocks = re.split(r"\r?\n\s*\r?\n", content)
    raw_entries = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue

        time_line = ""
        text_start_idx = 0
        for idx, line in enumerate(lines[:3]):
            if "-->" in line:
                time_line = line
                text_start_idx = idx + 1
                break

        if not time_line or "-->" not in time_line:
            continue

        parts = time_line.split("-->")
        if len(parts) < 2:
            continue

        start_sec = _timestamp_to_seconds(parts[0])
        end_sec = _timestamp_to_seconds(parts[1].split()[0])

        raw_text = re.sub(r"<[^>]+>", "", " ".join(lines[text_start_idx:])).strip()
        if not raw_text:
            continue

        words = raw_text.split()
        chunks = [" ".join(words[i : i + 2]).upper() for i in range(0, len(words), 2)]
        effective_start = max(0.0, start_sec - 0.15)
        total_dur = max(0.15, end_sec - effective_start)
        step = total_dur / len(chunks)

        for idx, chunk in enumerate(chunks):
            c_start = effective_start + idx * step
            c_end = min(end_sec, c_start + step)
            if (c_end - c_start) >= 0.05:
                raw_entries.append({"start": c_start, "end": c_end, "text": chunk})

    raw_entries.sort(key=lambda x: x["start"])
    clean_entries = []

    for i, curr in enumerate(raw_entries):
        if (
            clean_entries
            and curr["text"] == clean_entries[-1]["text"]
            and curr["start"] <= clean_entries[-1]["end"] + 0.35
        ):
            clean_entries[-1]["end"] = max(clean_entries[-1]["end"], curr["end"])
            continue

        if i + 1 < len(raw_entries):
            next_start = raw_entries[i + 1]["start"]
            if curr["end"] > next_start:
                curr["end"] = max(curr["start"] + 0.05, next_start - 0.01)

        if (curr["end"] - curr["start"]) >= 0.05:
            clean_entries.append(curr)

    return clean_entries


def create_ass_for_clip(
    srt_entries: list[dict],
    clip_start: float,
    clip_end: float,
    ass_output_path: str,
    font_name: str = "Luckiest Guy",
    font_size: int = 74,
    caption_offset: float = 0.0,
    fonts_dir: str = "fonts",
) -> str | None:
    dialogue_lines = []
    resolved_font = _resolve_chunky_font(font_name=font_name, fonts_dir=fonts_dir)
    safe_font_size = max(36, min(140, int(font_size)))

    for idx, entry in enumerate(srt_entries):
        adj_start = entry["start"] + caption_offset
        adj_end = entry["end"] + caption_offset

        if adj_end <= clip_start or adj_start >= clip_end:
            continue

        rel_start = max(0.0, float(adj_start - clip_start))
        rel_end = min(float(clip_end - clip_start), float(adj_end - clip_start))
        dur_ms = int((rel_end - rel_start) * 1000)
        if dur_ms <= 50:
            continue

        color_code = ASS_COLORS[idx % len(ASS_COLORS)]
        clean_text = entry["text"].replace("{", "").replace("}", "")
        start_ass = _seconds_to_ass_time(rel_start)
        end_ass = _seconds_to_ass_time(rel_end)

        fade_in = min(50, dur_ms // 4)
        fade_out = min(70, dur_ms // 4)
        pop_end = min(90, dur_ms // 2)

        anim_tags = (
            f"{{\\c{color_code}\\fad({fade_in},{fade_out})"
            f"\\fscx85\\fscy85\\t(0,{pop_end},\\fscx103\\fscy103)"
            f"\\t({pop_end},{pop_end + 50},\\fscx100\\fscy100)}}"
        )
        dialogue_lines.append(
            f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{anim_tags}{clean_text}"
        )

    if not dialogue_lines:
        return None

    style_line = (
        f"Style: Default,{resolved_font},{safe_font_size},"
        f"&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        f"-1,0,0,0,100,100,1,0,1,3.5,1.5,2,60,60,540,1"
    )
    header_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style_line,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    full_ass = "\n".join(header_lines + dialogue_lines) + "\n"
    with open(ass_output_path, "w", encoding="utf-8") as f:
        f.write(full_ass)

    return ass_output_path
