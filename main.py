import os
import glob
import sys
from downloader import prepare_media, fetch_auto_bgm_list, get_temp_dir, ensure_selected_font, FONT_CATALOG
from clipper import generate_clips


def _prompt_int(prompt_text: str, default: int, min_val: int = 1, max_val: int = 300) -> int:
    raw = input(f"{prompt_text} [default: {default}]: ").strip()
    if not raw:
        return default
    try:
        value = int(raw)
        if min_val <= value <= max_val:
            return value
        print(f"[Warning] Value out of range ({min_val}-{max_val}). Using default ({default}).")
        return default
    except ValueError:
        print(f"[Warning] Invalid number entered. Using default ({default}).")
        return default


def _prompt_float(prompt_text: str, default: float, min_val: float = 0.0, max_val: float = 2.0) -> float:
    raw = input(f"{prompt_text} [default: {default}]: ").strip()
    if not raw:
        return default
    try:
        value = float(raw)
        if min_val <= value <= max_val:
            return value
        print(f"[Warning] Value out of range ({min_val}-{max_val}). Using default ({default}).")
        return default
    except ValueError:
        print(f"[Warning] Invalid decimal entered. Using default ({default}).")
        return default


def _cleanup_cache(cache_dir: str) -> None:
    for file_path in glob.glob(os.path.join(cache_dir, "*")):
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            pass


def run_cli() -> None:
    print("=" * 60)
    print("   YT AUTO-CLIPPER | Long-Form Stream to 9:16 Shorts Tool   ")
    print("=" * 60)

    source = input("\nEnter YouTube URL (max 5 hours) or local MP4 path: ").strip().strip('"')
    if not source:
        print("[Error] Source input cannot be empty.")
        sys.exit(1)

    font_list = list(FONT_CATALOG.keys())
    print("\nAvailable Caption Fonts:")
    for idx, fname in enumerate(font_list, start=1):
        print(f"  {idx}. {fname}")
    font_choice = _prompt_int("Choose font number", default=1, min_val=1, max_val=len(font_list))
    chosen_font = font_list[font_choice - 1]

    source_volume = _prompt_float("Original video audio volume (0.0 to 2.0, 1.0 = normal)", default=1.0, min_val=0.0, max_val=2.0)

    use_bgm = input("Auto-fetch fresh royalty-free background music? (y/n) [default: y]: ").strip().lower()
    enable_bgm = use_bgm != "n"
    same_bgm = False
    bgm_volume = 0.0
    if enable_bgm:
        same_choice = input("Use a different track per clip? (y/n) [default: y]: ").strip().lower()
        same_bgm = same_choice == "n"
        bgm_volume = _prompt_float("Background music volume (0.0 to 1.0)", default=0.22, min_val=0.0, max_val=1.0)

    clip_duration = _prompt_int("Duration per clip in seconds (5 to 180)", default=30, min_val=5, max_val=180)
    max_clips = _prompt_int("Total number of clips to generate (1 to 50)", default=3, min_val=1, max_val=50)

    cache_dir = get_temp_dir()
    fonts_dir = "fonts"

    print("\n--- Starting Pipeline ---")
    try:
        selected_font = ensure_selected_font(font_name=chosen_font, fonts_dir=fonts_dir)
        segments, srt_path = prepare_media(
            source=source,
            output_dir=cache_dir,
            clip_duration=clip_duration,
            max_clips=max_clips,
        )

        bgm_paths: list[str] = []
        if enable_bgm:
            track_count = 1 if same_bgm else len(segments)
            bgm_paths = fetch_auto_bgm_list(
                output_dir=cache_dir,
                duration_sec=clip_duration + 5,
                count=track_count,
            )

        outputs = generate_clips(
            segments=segments,
            srt_path=srt_path,
            output_dir="output",
            bgm_paths=bgm_paths,
            source_volume=source_volume,
            bgm_volume=bgm_volume,
            font_name=selected_font,
            fonts_dir=fonts_dir,
        )

        print("\n" + "=" * 60)
        print("All clips generated successfully:")
        for path in outputs:
            print(f" -> {path}")
        print("=" * 60)

    except Exception as exc:
        print(f"\n[Fatal Error] {exc}")
        sys.exit(1)
    finally:
        _cleanup_cache(cache_dir)


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        from app import run_ui
        run_ui()
        
