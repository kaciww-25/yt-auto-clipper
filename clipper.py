import os
import re
import random
import subprocess
from collections import Counter
import imageio_ffmpeg
from subtitler import parse_srt, create_ass_for_clip, transcribe_audio_to_srt

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "you", "are", "was", "were",
    "have", "has", "had", "not", "but", "what", "when", "where", "who", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "than", "too", "very", "can", "will", "just",
    "yang", "dan", "ini", "itu", "untuk", "dengan", "dari", "pada", "adalah",
    "tidak", "bisa", "ada", "akan", "juga", "atau", "kalau", "karena", "jadi",
}

INITIATIVE_HOOKS = [
    "Wait Until The End",
    "Nobody Expected This",
    "Peak Chaos Moment",
    "You Have To See This",
    "Insane Turning Point",
    "Best Scene Of The Run",
    "Watch What Happens Next",
    "Pure Highlight Energy",
]

INITIATIVE_TAG_SETS = [
    ["shorts", "viral", "fyp", "highlights", "trending", "clips", "moment", "mustwatch"],
    ["shorts", "gaming", "gameplay", "clutch", "epic", "reaction", "viral", "fyp"],
    ["shorts", "storytime", "plot twist", "unexpected", "trending", "clips", "viral", "reels"],
    ["shorts", "best moments", "top clips", "highlights", "fyp", "trending", "shortfilm", "viral"],
]


def _escape_ffmpeg_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _generate_clip_metadata(
    srt_entries: list[dict],
    clip_start: float,
    clip_end: float,
    clip_index: int,
    hook_text: str = "",
    video_title: str = "",
    video_description: str = "",
) -> dict:
    spoken_chunks = [
        entry["text"].strip()
        for entry in srt_entries
        if entry["end"] > clip_start and entry["start"] < clip_end and entry["text"].strip()
    ]
    full_transcript = " ".join(spoken_chunks).strip()

    combined_context = " ".join(
        part.strip() for part in (full_transcript, video_title, video_description) if part and part.strip()
    )
    words = re.findall(r"[a-zA-Z0-9]{3,}", combined_context.lower())
    keywords = [w for w, _ in Counter(w for w in words if w not in STOPWORDS).most_common(8)]

    mm = int(clip_start // 60)
    ss = int(clip_start % 60)
    time_code = f"{mm:02d}:{ss:02d}"

    fallback_hook = INITIATIVE_HOOKS[(clip_index - 1 + random.randint(0, 2)) % len(INITIATIVE_HOOKS)]
    tag_pack = INITIATIVE_TAG_SETS[(clip_index - 1) % len(INITIATIVE_TAG_SETS)]

    if hook_text.strip():
        title = f"{hook_text.strip()} ({time_code}) #Shorts"
    elif full_transcript and keywords:
        top_phrase = " ".join(keywords[:3]).title()
        title = f"{top_phrase} — {fallback_hook} #Shorts"
    elif video_title.strip():
        clean_title = re.sub(r"\s+", " ", video_title.strip())[:44]
        title = f"{clean_title} | {fallback_hook} #Shorts"
    elif video_description.strip() and keywords:
        top_phrase = " ".join(keywords[:3]).title()
        title = f"{top_phrase} ({time_code}) #Shorts"
    else:
        title = f"{fallback_hook} @{time_code} #Shorts"

    merged_tags = list(dict.fromkeys(keywords + tag_pack))[:12]

    return {
        "title": title,
        "tags": ", ".join(merged_tags),
        "transcript_preview": full_transcript[:220] + ("..." if len(full_transcript) > 220 else ""),
    }


def generate_clips(
    segments: list[dict],
    srt_path: str | None = None,
    output_dir: str = "output",
    bgm_paths: list[str] | None = None,
    source_volume: float = 1.0,
    bgm_volume: float = 0.22,
    font_name: str = "Luckiest Guy",
    font_size: int = 74,
    caption_offset: float = 0.0,
    fonts_dir: str = "fonts",
    layout_mode: str = "crop",
    hook_text: str = "",
    watermark_text: str = "",
    video_title: str = "",
    video_description: str = "",
) -> list[dict]:
    os.makedirs(output_dir, exist_ok=True)

    auto_srt_path: str | None = None
    effective_srt = srt_path
    if not effective_srt and segments:
        auto_srt_candidate = os.path.abspath(os.path.join(output_dir, "_auto_speech.srt"))
        generated_srt = transcribe_audio_to_srt(
            video_path=segments[0]["file"],
            srt_output_path=auto_srt_candidate,
            offset_sec=0.0,
        )
        if generated_srt and os.path.isfile(generated_srt):
            effective_srt = generated_srt
            auto_srt_path = generated_srt

    srt_entries = parse_srt(effective_srt) if effective_srt else []
    generated_items: list[dict] = []
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    valid_bgms = [p for p in (bgm_paths or []) if p and os.path.isfile(p)]

    try:
        for clip_index, seg in enumerate(segments, start=1):
            video_path = seg["file"]
            file_offset = float(seg.get("offset_in_file", 0.0))
            orig_start = float(seg.get("orig_start", 0.0))
            actual_dur = float(seg.get("duration", 30.0))
            orig_end = orig_start + actual_dur

            if actual_dur < 5 or not os.path.isfile(video_path):
                continue

            print(f"[Clipper] Fast-rendering Highlight #{clip_index} (from {int(orig_start//60)}m{int(orig_start%60):02d}s)...")

            ass_path = os.path.abspath(os.path.join(output_dir, f"_temp_sub_{clip_index:02d}.ass"))
            active_ass = create_ass_for_clip(
                srt_entries=srt_entries,
                clip_start=orig_start,
                clip_end=orig_end,
                ass_output_path=ass_path,
                font_name=font_name,
                font_size=font_size,
                caption_offset=caption_offset,
                fonts_dir=fonts_dir,
            )

            overlay_filters: list[str] = ["fps=30"]

            if active_ass and os.path.isfile(active_ass):
                print(f"[Clipper] Burning {len(srt_entries)} parsed caption cues into clip #{clip_index}...")
                escaped_ass = active_ass.replace("\\", "/").replace(":", "\\:")
                overlay_filters.append(f"ass='{escaped_ass}'")
            else:
                print(f"[Clipper] No caption entries matched window {orig_start:.1f}s-{orig_end:.1f}s for clip #{clip_index}.")

            if hook_text.strip():
                safe_hook = _escape_ffmpeg_text(hook_text.strip().upper())
                overlay_filters.append(
                    f"drawtext=text='{safe_hook}':fontcolor=white:fontsize=54:box=1:boxcolor=black@0.75:boxborderw=18:x=(w-text_w)/2:y=160"
                )

            if watermark_text.strip():
                safe_wm = _escape_ffmpeg_text(watermark_text.strip())
                overlay_filters.append(
                    f"drawtext=text='{safe_wm}':fontcolor=white@0.65:fontsize=34:borderw=2:bordercolor=black@0.7:x=(w-text_w)/2:y=h-180"
                )

            post_chain = ",".join(overlay_filters)

            if layout_mode == "blur":
                video_graph = (
                    f"[0:v]split=2[bg][fg];"
                    f"[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg_blur];"
                    f"[fg]scale=1080:-2[fg_scaled];"
                    f"[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2,{post_chain}[vout]"
                )
            else:
                video_graph = (
                    f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{post_chain}[vout]"
                )

            output_path = os.path.join(output_dir, f"short_clip_{clip_index:02d}.mp4")
            active_bgm = valid_bgms[(clip_index - 1) % len(valid_bgms)] if valid_bgms else None

            if active_bgm:
                filter_complex = (
                    f"{video_graph};"
                    f"[0:a]volume={source_volume}[a1];"
                    f"[1:a]volume={bgm_volume}[a2];"
                    f"[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                )
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-ss", str(file_offset),
                    "-t", str(actual_dur),
                    "-i", video_path,
                    "-stream_loop", "-1",
                    "-i", active_bgm,
                    "-filter_complex", filter_complex,
                    "-map", "[vout]",
                    "-map", "[aout]",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    output_path,
                ]
            else:
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-ss", str(file_offset),
                    "-t", str(actual_dur),
                    "-i", video_path,
                    "-filter_complex", video_graph,
                    "-af", f"volume={source_volume}",
                    "-map", "[vout]",
                    "-map", "0:a:0?",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    output_path,
                ]

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if active_ass and os.path.isfile(active_ass):
                try:
                    os.remove(active_ass)
                except OSError:
                    pass

            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg rendering error: {res.stderr[-400:]}")

            meta = _generate_clip_metadata(
                srt_entries=srt_entries,
                clip_start=orig_start,
                clip_end=orig_end,
                clip_index=clip_index,
                hook_text=hook_text,
                video_title=video_title,
                video_description=video_description,
            )

            print(f"[Clipper] Saved: {output_path}")
            generated_items.append(
                {
                    "path": output_path,
                    "title": meta["title"],
                    "tags": meta["tags"],
                    "transcript": meta["transcript_preview"],
                }
            )
    finally:
        if auto_srt_path and os.path.isfile(auto_srt_path):
            try:
                os.remove(auto_srt_path)
            except OSError:
                pass

    print(f"[Clipper] Done! Generated {len(generated_items)} highlight clip(s) in '{output_dir}/'.")
    return generated_items

