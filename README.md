# YT Auto-Clipper

[![Support on Saweria](https://img.shields.io/badge/Support%20on-Saweria-facc15?style=for-the-badge&logo=buy-me-a-coffee&logoColor=050505)](https://saweria.co/naufalique07)

Convert long-form YouTube videos (up to 5 hours) or local MP4 files into vertical **9:16 YouTube Shorts / TikTok / Reels** with automatic highlight detection, live visual preview, dynamic animated captions, and royalty-free background music — all through a clean local web interface.

## Features

- **Visual Web UI with Live 9:16 Preview (`app.py`):** Real-time interactive preview canvas to adjust caption font, size, layout mode, top hook text, and channel watermark before rendering.
- **Smart Highlight Extraction:** Automatically detects YouTube *Most Replayed* heatmap peaks or spaces clips across key moments of the video.
- **Dynamic Animated Captions:** Smooth pop-in & fade transitions with 10 built-in viral fonts (*Luckiest Guy*, *Anton*, *Bangers*, *Montserrat*, *Poppins*, *Oswald*, *Bebas Neue*, *Rubik*, *Permanent Marker*, *Titan One*), customizable font size, and sync offset fine-tuning.
- **Flexible 9:16 Layouts & Overlays:** Choose between Full-Screen 9:16 Crop or 16:9 Fit with Blurred Background, plus optional top hook banners and channel watermarks.
- **Procedural Royalty-Free BGM:** Fetches fresh, short royalty-free background tracks (different track per clip or single track for all) with independent volume sliders.
- **One-Click Metadata & ZIP Export:** Auto-generates suggested titles and tags per clip along with batch `.ZIP` downloading.

## Quick Start

### 1. Clone & Install Dependencies
```bash
git clone [https://github.com/kaciww-25/yt-auto-clipper.git](https://github.com/kaciww-25/yt-auto-clipper.git)
cd yt-auto-clipper
pip install -r requirements.txt
