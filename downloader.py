import os
import glob
import random
import subprocess
import tempfile
import urllib.request
import yt_dlp
import imageio_ffmpeg
from yt_dlp.utils import download_range_func

MAX_SOURCE_DURATION = 5 * 3600

FONT_CATALOG = {
    "Luckiest Guy": (
        "LuckiestGuy-Regular.ttf",
        "https://github.com/google/fonts/raw/main/apache/luckiestguy/LuckiestGuy-Regular.ttf",
    ),
    "Anton": (
        "Anton-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
    ),
    "Bangers": (
        "Bangers-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf",
    ),
    "Montserrat": (
        "Montserrat-Black.ttf",
        "https://github.com/google/fonts/raw/main/ofl/montserrat/static/Montserrat-Black.ttf",
    ),
    "Poppins": (
        "Poppins-Black.ttf",
        "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Black.ttf",
    ),
    "Oswald": (
        "Oswald-Bold.ttf",
        "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf",
    ),
    "Bebas Neue": (
        "BebasNeue-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    ),
    "Rubik": (
        "Rubik-Black.ttf",
        "https://github.com/google/fonts/raw/main/ofl/rubik/static/Rubik-Black.ttf",
    ),
    "Permanent Marker": (
        "PermanentMarker-Regular.ttf",
        "https://github.com/google/fonts/raw/main/apache/permanentmarker/PermanentMarker-Regular.ttf",
    ),
    "Titan One": (
        "TitanOne-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/titanone/TitanOne-Regular.ttf",
    ),
}

BGM_SEARCH_QUERIES = [
    "ytsearch20:no copyright lofi hip hop beat instrumental",
    "ytsearch20:royalty free vlog background music chill",
    "ytsearch20:no copyright gaming background music instrumental",
    "ytsearch20:royalty free synthwave ambient beat",
    "ytsearch20:no copyright upbeat acoustic background music",
    "ytsearch20:royalty free jazz hop chill instrumental",
]

BANNED_BGM_WORDS = ("hour", "hours", "mix", "playlist", "compilation", "live", "24/7", "loop")


def get_temp_dir() -> str:
    temp_dir = os.path.join(tempfile.gettempdir(), "yt_auto_clipper_cache")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def ensure_selected_font(font_name: str = "Luckiest Guy", fonts_dir: str = "fonts") -> str:
    os.makedirs(fonts_dir, exist_ok=True)
    selected = font_name if font_name in FONT_CATALOG else "Luckiest Guy"
    filename, url = FONT_CATALOG[selected]
    font_path = os.path.join(fonts_dir, filename)

    if os.path.isfile(font_path) and os.path.getsize(font_path) > 10000:
        return selected

    print(f"[Downloader] Fetching '{selected}' font automatically...")
    try:
        urllib.request.urlretrieve(url, font_path)
    except Exception:
        pass
    return selected


def fetch_auto_bgm_list(
    output_dir: str | None = None,
    duration_sec: int = 35,
    count: int = 1,
) -> list[str]:
    target_dir = output_dir or get_temp_dir()
    os.makedirs(target_dir, exist_ok=True)
    needed_count = max(1, count)

    for old_bgm in glob.glob(os.path.join(target_dir, "bgm_auto*")):
        try:
            os.remove(old_bgm)
        except OSError:
            pass

    queries = random.sample(BGM_SEARCH_QUERIES, k=min(len(BGM_SEARCH_QUERIES), 2 if needed_count > 1 else 1))
    print(f"[Downloader] Searching for {needed_count} fresh royalty-free background track(s)...")

    search_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
    }

    seen_ids = set()
    valid_entries = []
    with yt_dlp.YoutubeDL(search_opts) as ydl:
        for query in queries:
            result = ydl.extract_info(query, download=False)
            entries = result.get("entries", []) if result else []
            for e in entries:
                vid_id = e.get("id") if e else None
                if not vid_id or len(vid_id) != 11 or vid_id in seen_ids:
                    continue
                title_lower = (e.get("title") or "").lower()
                dur = e.get("duration")
                if not dur or not (45 <= dur <= 240):
                    continue
                if any(bad in title_lower for bad in BANNED_BGM_WORDS):
                    continue
                seen_ids.add(vid_id)
                valid_entries.append(e)

    random.shuffle(valid_entries)
    fetch_cut = max(15, int(duration_sec) + 5)
    downloaded_tracks: list[str] = []

    for chosen in valid_entries:
        if len(downloaded_tracks) >= needed_count:
            break

        track_idx = len(downloaded_tracks) + 1
        bgm_url = f"https://www.youtube.com/watch?v={chosen['id']}"
        print(f"[Downloader] Selected BGM #{track_idx} ({chosen.get('duration')}s): {chosen.get('title', 'Track')}")

        dl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": os.path.join(target_dir, f"bgm_auto_{track_idx:02d}.%(ext)s"),
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
            "download_ranges": download_range_func(None, [(0, fetch_cut)]),
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }

        with yt_dlp.YoutubeDL(dl_opts) as ydl:
            ydl.download([bgm_url])

        bgm_files = [
            f for f in glob.glob(os.path.join(target_dir, f"bgm_auto_{track_idx:02d}.*"))
            if os.path.isfile(f) and os.path.getsize(f) > 10000
        ]
        if bgm_files:
            downloaded_tracks.append(bgm_files[0])

    if not downloaded_tracks:
        print("[Downloader] Could not fetch valid short BGM tracks. Proceeding with original audio only.")
    return downloaded_tracks


def _get_local_media_duration(file_path: str, ffmpeg_exe: str) -> float:
    res = subprocess.run(
        [ffmpeg_exe, "-i", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            part = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            try:
                h, m, s = part.split(":")
                dur = int(h) * 3600 + int(m) * 60 + float(s)
                if dur > 0:
                    return dur
            except ValueError:
                pass
    return 60.0


def _select_highlight_timestamps(
    total_duration: float,
    clip_duration: int,
    max_clips: int,
    heatmap: list[dict] | None = None,
) -> list[float]:
    if total_duration <= clip_duration:
        return [0.0]

    max_possible = max(1, int(total_duration // clip_duration))
    target_count = min(max_clips, max_possible)
    min_gap = max(float(clip_duration) * 1.5, (total_duration / (target_count + 1)) * 0.65)
    selected: list[float] = []

    if heatmap:
        ranked = sorted(heatmap, key=lambda h: float(h.get("value", 0.0)), reverse=True)
        for item in ranked:
            center = (float(item.get("start_time", 0.0)) + float(item.get("end_time", 0.0))) / 2.0
            start_cand = max(0.0, min(total_duration - clip_duration, center - (clip_duration * 0.35)))
            if all(abs(start_cand - existing) >= min_gap for existing in selected):
                selected.append(round(start_cand, 2))
            if len(selected) >= target_count:
                break

    if len(selected) < target_count:
        usable_start = min(15.0, total_duration * 0.05)
        usable_end = max(usable_start + clip_duration, total_duration - clip_duration)
        span = max(0.0, usable_end - usable_start)
        step = span / max(1, target_count)

        for idx in range(target_count):
            if len(selected) >= target_count:
                break
            zone_start = usable_start + idx * step
            zone_end = min(usable_end, zone_start + max(0.0, step - clip_duration))
            cand = random.uniform(zone_start, max(zone_start, zone_end))
            if all(abs(cand - existing) >= clip_duration for existing in selected):
                selected.append(round(cand, 2))

    selected.sort()
    return selected


def _download_best_subtitle(source: str, info: dict, target_dir: str) -> str | None:
    manual_subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    preferred_langs = ["en", "en-orig", "en-US", "id", "id-orig"]
    chosen_langs: list[str] = []

    for lang in preferred_langs:
        if lang in manual_subs or lang in auto_subs:
            chosen_langs.append(lang)

    if not chosen_langs:
        for lang in list(manual_subs.keys()) + list(auto_subs.keys()):
            if lang and not lang.startswith("live_chat") and lang not in chosen_langs:
                chosen_langs.append(lang)
                if len(chosen_langs) >= 2:
                    break

    if not chosen_langs:
        return None

    sub_opts = {
        "skip_download": True,
        "outtmpl": os.path.join(target_dir, "raw_subs.%(ext)s"),
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": chosen_langs,
        "subtitlesformat": "srt/vtt/best",
        "convertsubtitles": "srt",
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(sub_opts) as ydl:
        ydl.download([source])

    srt_files = [
        f for f in glob.glob(os.path.join(target_dir, "raw_subs*.srt"))
        if os.path.isfile(f) and os.path.getsize(f) > 20
    ]
    return srt_files[0] if srt_files else None


def prepare_media(
    source: str,
    output_dir: str | None = None,
    clip_duration: int = 30,
    max_clips: int = 3,
    display_title: str = "",
) -> tuple[list[dict], str | None, str, str]:
    target_dir = output_dir or get_temp_dir()
    os.makedirs(target_dir, exist_ok=True)

    if os.path.isfile(source):
        print(f"[Downloader] Using local video file: {source}")
        base_name = os.path.splitext(source)[0]
        local_srt = f"{base_name}.srt"
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        total_dur = _get_local_media_duration(source, ffmpeg_exe)
        starts = _select_highlight_timestamps(total_dur, clip_duration, max_clips, heatmap=None)
        segments = [
            {
                "file": source,
                "offset_in_file": st,
                "orig_start": st,
                "duration": min(float(clip_duration), max(0.0, total_dur - st)),
            }
            for st in starts
            if min(float(clip_duration), max(0.0, total_dur - st)) >= 5
        ]
        if not segments and total_dur >= 5:
            segments = [
                {
                    "file": source,
                    "offset_in_file": 0.0,
                    "orig_start": 0.0,
                    "duration": min(float(clip_duration), total_dur),
                }
            ]
        title_out = display_title.strip() or os.path.splitext(os.path.basename(source))[0]
        return segments, (local_srt if os.path.isfile(local_srt) else None), title_out, ""

    print(f"[Downloader] Analyzing video metadata & audience replay heatmap: {source}")
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(source, download=False)
        if not info:
            raise ValueError("Unable to retrieve video metadata. Please verify the YouTube URL.")
        duration = float(info.get("duration") or 0)
        if duration > MAX_SOURCE_DURATION:
            raise ValueError(f"Source video exceeds the 5-hour limit ({duration / 3600:.2f} hours detected).")
        heatmap = info.get("heatmap")
        video_title = str(info.get("title") or "")
        video_description = str(info.get("description") or "")[:600]

    for old_file in glob.glob(os.path.join(target_dir, "raw_seg*")) + glob.glob(os.path.join(target_dir, "raw_subs*")):
        try:
            os.remove(old_file)
        except OSError:
            pass

    starts = _select_highlight_timestamps(duration, clip_duration, max_clips, heatmap=heatmap)
    mode_label = "Most-Replayed Heatmap Peaks" if heatmap else "Spaced Highlight Zones"
    print(f"[Downloader] Selected {len(starts)} distant moments ({mode_label}): {[f'{int(s//60)}m{int(s%60):02d}s' for s in starts]}")

    srt_path = _download_best_subtitle(source, info, target_dir)
    if srt_path:
        print(f"[Downloader] Subtitles found: {srt_path}")
    else:
        print("[Downloader] Subtitles unavailable on YouTube (clips will be generated without captions).")

    segments = []
    for idx, st in enumerate(starts, start=1):
        end_t = min(duration, st + float(clip_duration) + 1.0)
        actual_dur = min(float(clip_duration), duration - st)
        if actual_dur < 5:
            continue

        seg_template = os.path.join(target_dir, f"raw_seg_{idx:02d}.%(ext)s")
        seg_file = os.path.join(target_dir, f"raw_seg_{idx:02d}.mp4")
        print(f"[Downloader] Fetching highlight #{idx} ({int(st//60)}m{int(st%60):02d}s - {int(end_t//60)}m{int(end_t%60):02d}s)...")

        dl_opts = {
            "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "outtmpl": seg_template,
            "merge_output_format": "mp4",
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
            "download_ranges": download_range_func(None, [(st, end_t)]),
            "concurrent_fragment_downloads": 4,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(dl_opts) as ydl:
            ydl.download([source])

        if os.path.isfile(seg_file):
            segments.append(
                {
                    "file": seg_file,
                    "offset_in_file": 0.0,
                    "orig_start": st,
                    "duration": actual_dur,
                }
            )

    if not segments:
        raise FileNotFoundError("Failed to fetch any highlight segments from the source video.")

    return segments, srt_path, video_title, video_description

