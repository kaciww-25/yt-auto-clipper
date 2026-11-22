import builtins as _builtins
import io as _io
from pathlib import Path as _Path


def _strip_metadata_errors(kwargs: dict) -> dict:
    kwargs.pop("metadata_errors", None)
    return kwargs


_orig_builtins_open = _builtins.open
_orig_io_open = _io.open
_orig_path_open = _Path.open


def _safe_builtins_open(*args, **kwargs):
    return _orig_builtins_open(*args, **_strip_metadata_errors(kwargs))


def _safe_io_open(*args, **kwargs):
    return _orig_io_open(*args, **_strip_metadata_errors(kwargs))


def _safe_path_open(self, *args, **kwargs):
    return _orig_path_open(self, *args, **_strip_metadata_errors(kwargs))


_builtins.open = _safe_builtins_open
_io.open = _safe_io_open
_Path.open = _safe_path_open

try:
    import av as _av

    _orig_av_open = _av.open

    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    _av.open = _safe_av_open
except ImportError:
    pass

import io
import os
import re
import json
import zipfile
import threading
import traceback
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from downloader import prepare_media, fetch_auto_bgm_list, get_temp_dir, ensure_selected_font, FONT_CATALOG
from clipper import generate_clips
from main import _cleanup_cache

SAWERIA_URL = "https://saweria.co/naufalique07"

FONT_OPTIONS_HTML = "\n".join(
    f'              <option value="{name}"{" selected" if name == "Luckiest Guy" else ""}>{name}</option>'
    for name in FONT_CATALOG.keys()
)

HTML_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>YT Auto-Clipper | 9:16 Shorts Maker</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Bangers&family=Bebas+Neue&family=Luckiest+Guy&family=Montserrat:wght@700;900&family=Oswald:wght@700&family=Permanent+Marker&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Poppins:wght@900&family=Rubik:wght@900&family=Titan+One&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-yellow: #facc15;
      --card-amber: rgba(251, 191, 36, 0.88);
      --input-bg: rgba(255, 251, 235, 0.95);
      --ink: #0f172a;
      --ink-muted: #334155;
      --maroon: #7f0019;
      --success: #15803d;
      --danger: #b91c1c;
    }}
    * {{ box-sizing: border-box; font-family: 'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif; }}
    body {{
      margin: 0;
      padding: 28px 20px;
      background-color: var(--bg-yellow);
      color: var(--ink);
      display: flex;
      justify-content: center;
      min-height: 100vh;
      position: relative;
      overflow-x: hidden;
    }}
    .bg-decor {{
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
      overflow: hidden;
    }}
    .shape-black-tl {{
      position: absolute; top: -120px; left: -80px;
      width: 340px; height: 340px; border-radius: 50%; background: #050505;
    }}
    .shape-maroon-bl {{
      position: absolute; bottom: -140px; left: -90px;
      width: 420px; height: 420px; border-radius: 50%; background: var(--maroon);
    }}
    .shape-black-br {{
      position: absolute; bottom: -110px; right: -110px;
      width: 440px; height: 440px; border-radius: 50%; background: #050505;
    }}
    .bg-svg-lines {{
      position: absolute; inset: 0; width: 100%; height: 100%;
    }}
    .container {{
      width: 100%; max-width: 1140px; position: relative; z-index: 1;
    }}
    .header {{
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 14px; margin-bottom: 22px;
      background: rgba(255, 255, 255, 0.72); backdrop-filter: blur(10px);
      border: 3px solid #ffffff; border-radius: 24px; padding: 16px 24px;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    }}
    .header-title h1 {{
      margin: 0 0 4px; font-size: 1.75rem; font-weight: 800;
      letter-spacing: -0.6px; color: #050505;
    }}
    .header-title p {{
      margin: 0; color: var(--ink-muted); font-size: 0.9rem; font-weight: 600;
    }}
    .saweria-btn {{
      display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px;
      border-radius: 999px; background: #050505; color: #facc15;
      text-decoration: none; font-weight: 800; font-size: 0.88rem;
      border: 2px solid #ffffff; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
      transition: transform 0.15s ease, background 0.15s ease;
    }}
    .saweria-btn:hover {{
      background: var(--maroon); color: #ffffff; transform: translateY(-2px);
    }}
    .workspace {{
      display: grid; grid-template-columns: 1fr 345px; gap: 22px; align-items: start;
    }}
    .card {{
      background: var(--card-amber); backdrop-filter: blur(12px);
      border: 3.5px solid #ffffff; border-radius: 34px; padding: 26px;
      margin-bottom: 20px; box-shadow: 0 16px 36px rgba(15, 23, 42, 0.12);
    }}
    .source-box {{
      background: rgba(255, 255, 255, 0.45);
      border: 2px solid #ffffff;
      border-radius: 20px;
      padding: 16px;
      margin-bottom: 18px;
    }}
    .local-file-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1.5px dashed rgba(5, 5, 5, 0.22);
    }}
    .file-picker-btn {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 16px;
      border-radius: 12px;
      background: #050505;
      color: #facc15;
      border: 2px solid #ffffff;
      font-size: 0.86rem;
      font-weight: 800;
      cursor: pointer;
      transition: background 0.15s, transform 0.15s;
    }}
    .file-picker-btn:hover {{
      background: var(--maroon);
      color: #ffffff;
      transform: translateY(-1px);
    }}
    .file-picker-btn.secondary-pick {{
      background: var(--maroon);
      color: #ffffff;
    }}
    .file-picker-btn.secondary-pick:hover {{
      background: #050505;
      color: #facc15;
    }}
    .picked-file-name {{
      font-size: 0.84rem;
      font-weight: 700;
      color: #050505;
      background: rgba(255, 255, 255, 0.8);
      padding: 6px 12px;
      border-radius: 10px;
      border: 1.5px solid #ffffff;
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .clear-file-btn {{
      background: transparent;
      border: 1.5px solid #050505;
      color: #050505;
      border-radius: 8px;
      padding: 4px 9px;
      font-size: 0.76rem;
      font-weight: 700;
      cursor: pointer;
    }}
    .clear-file-btn:hover {{
      background: #050505;
      color: #ffffff;
    }}
    .form-group {{ margin-bottom: 16px; }}
    label.field-label {{
      display: flex; justify-content: space-between; font-weight: 700;
      margin-bottom: 7px; font-size: 0.88rem; color: #050505;
    }}
    label.field-label span.val {{
      background: #050505; color: #facc15; padding: 1px 8px;
      border-radius: 999px; font-size: 0.78rem; font-weight: 800;
    }}
    input[type="text"], input[type="number"], select {{
      width: 100%; padding: 11px 14px; border-radius: 14px;
      border: 2px solid #ffffff; background: var(--input-bg);
      color: #050505; font-size: 0.92rem; font-weight: 600; outline: none;
    }}
    input[type="text"]:focus, input[type="number"]:focus, select:focus {{
      border-color: #050505; box-shadow: 0 0 0 3px rgba(5, 5, 5, 0.12);
    }}
    input[type="range"] {{
      width: 100%; accent-color: #050505; cursor: pointer;
    }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1.2fr; gap: 14px; }}
    .toggle-row {{
      display: flex; align-items: center; justify-content: flex-start;
      gap: 10px; margin-bottom: 14px; cursor: pointer; font-weight: 700;
      font-size: 0.9rem; color: #050505;
    }}
    .toggle-row input {{
      width: 18px; height: 18px; margin: 0; accent-color: #050505; cursor: pointer;
    }}
    .custom-bgm-box {{
      background: rgba(255, 255, 255, 0.45);
      border: 2px solid #ffffff;
      border-radius: 16px;
      padding: 12px 14px;
      margin-bottom: 16px;
      display: none;
    }}
    button.primary {{
      width: 100%; padding: 15px; border: 2.5px solid #ffffff;
      border-radius: 16px; background: #050505; color: #facc15;
      font-size: 1rem; font-weight: 800; letter-spacing: 0.2px;
      cursor: pointer; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
      transition: background 0.2s, color 0.2s, transform 0.15s;
    }}
    button.primary:hover:not(:disabled) {{
      background: var(--maroon); color: #ffffff; transform: translateY(-1px);
    }}
    button.primary:disabled {{ opacity: 0.65; cursor: not-allowed; }}
    .status {{
      margin-top: 16px; padding: 12px 16px; border-radius: 14px;
      background: rgba(255, 255, 255, 0.88); border: 2px solid #ffffff;
      font-size: 0.9rem; font-weight: 600; color: #050505; display: none;
    }}
    .status.active {{ display: block; }}
    .status.error {{ border-color: var(--danger); color: var(--danger); background: #fef2f2; }}
    .status.done {{ border-color: var(--success); color: var(--success); background: #f0fdf4; }}

    .preview-sticky {{ position: sticky; top: 20px; }}
    .preview-title {{
      font-size: 0.95rem; font-weight: 800; margin: 0 0 12px;
      display: flex; justify-content: space-between; align-items: center; color: #050505;
    }}
    .preview-badge {{
      font-size: 0.72rem; background: #050505; color: #facc15;
      padding: 3px 9px; border-radius: 999px; font-weight: 800;
    }}
    .phone-frame {{
      width: 100%; aspect-ratio: 9/16; border-radius: 22px; overflow: hidden;
      position: relative; background: #050505; border: 3px solid #ffffff;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
    }}
    .dummy-bg-blur {{
      position: absolute; inset: 0;
      background: radial-gradient(circle at 30% 25%, #7f0019 0%, #1e1b4b 50%, #050505 100%);
      filter: blur(18px) brightness(0.8); transform: scale(1.15);
    }}
    .dummy-video-box {{
      position: absolute; inset: 0; display: flex; align-items: center;
      justify-content: center; transition: all 0.25s ease;
    }}
    .dummy-video-box.mode-crop {{
      width: 100%; height: 100%;
      background: linear-gradient(135deg, #18181b 0%, #7f0019 55%, #b45309 100%);
    }}
    .dummy-video-box.mode-blur {{
      width: 100%; height: 31.6%; top: 34.2%;
      background: linear-gradient(135deg, #09090b 0%, #9f1239 55%, #d97706 100%);
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.65);
      border-top: 1.5px solid rgba(255, 255, 255, 0.35);
      border-bottom: 1.5px solid rgba(255, 255, 255, 0.35);
    }}
    .dummy-scene-label {{
      color: rgba(255, 255, 255, 0.45); font-size: 0.78rem;
      font-weight: 800; letter-spacing: 1px; text-transform: uppercase;
    }}
    .preview-hook {{
      position: absolute; top: 8.5%; left: 50%; transform: translateX(-50%);
      background: rgba(0, 0, 0, 0.82); color: #fff; font-weight: 800;
      font-size: 0.85rem; padding: 5px 12px; border-radius: 6px;
      text-align: center; max-width: 88%; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; display: none; z-index: 4;
    }}
    .preview-caption {{
      position: absolute; bottom: 26%; left: 50%; transform: translateX(-50%);
      width: 90%; text-align: center; font-weight: 900; text-transform: uppercase;
      color: #00e6ff; line-height: 1.1; z-index: 4;
      text-shadow: -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0 3px 6px rgba(0, 0, 0, 0.85);
      transition: font-size 0.1s ease;
    }}
    .preview-watermark {{
      position: absolute; bottom: 8.5%; left: 50%; transform: translateX(-50%);
      color: rgba(255, 255, 255, 0.75); font-size: 0.72rem; font-weight: 700;
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9); z-index: 4; display: none;
    }}
    .preview-controls {{
      margin-top: 12px; display: flex; gap: 8px; justify-content: center;
    }}
    .preview-controls button {{
      background: rgba(255, 255, 255, 0.88); border: 2px solid #ffffff;
      color: #050505; padding: 6px 12px; border-radius: 999px;
      font-size: 0.75rem; font-weight: 700; cursor: pointer;
    }}
    .preview-controls button:hover {{
      background: #050505; color: #facc15;
    }}
    .results-header {{
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
    }}
    .zip-btn {{
      padding: 10px 18px; border-radius: 999px; background: #050505;
      color: #facc15; border: 2px solid #ffffff; text-decoration: none;
      font-size: 0.88rem; font-weight: 800;
    }}
    .results-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;
    }}
    .clip-card {{
      background: rgba(255, 255, 255, 0.88); border: 2.5px solid #ffffff;
      border-radius: 20px; padding: 12px; display: flex; flex-direction: column;
    }}
    .clip-card video {{
      width: 100%; border-radius: 14px; aspect-ratio: 9/16; background: #000;
    }}
    .meta-box {{
      margin-top: 10px; padding: 10px; border-radius: 12px;
      background: #fef9c3; border: 1px solid #fde047; font-size: 0.8rem;
      color: #1e293b; text-align: left; flex-grow: 1;
    }}
    .meta-box strong {{ color: #050505; display: block; margin-bottom: 4px; }}
    .meta-tags {{ color: #475569; font-size: 0.75rem; margin-top: 4px; }}
    .clip-actions {{ display: flex; gap: 8px; margin-top: 10px; }}
    .clip-actions a, .clip-actions button {{
      flex: 1; text-align: center; padding: 9px 10px; border-radius: 10px;
      border: none; background: #050505; color: #facc15; text-decoration: none;
      font-size: 0.8rem; font-weight: 700; cursor: pointer;
    }}
    .clip-actions button.copy-btn {{ background: var(--maroon); color: #ffffff; }}
    @media (max-width: 900px) {{
      .workspace {{ grid-template-columns: 1fr; }}
      .preview-sticky {{ position: static; max-width: 345px; margin: 0 auto; }}
    }}
    @media (max-width: 640px) {{ .grid-2, .grid-3 {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="bg-decor" aria-hidden="true">
    <div class="shape-black-tl"></div>
    <div class="shape-maroon-bl"></div>
    <div class="shape-black-br"></div>
    <svg class="bg-svg-lines" viewBox="0 0 1440 900" preserveAspectRatio="none">
      <path d="M -20 320 L 680 650 L 680 90" fill="none" stroke="#050505" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M 1100 -20 L 1260 135 C 1285 158 1265 182 1225 192 L 980 255" fill="none" stroke="#050505" stroke-width="5" stroke-linecap="round"/>
      <path d="M 1460 65 L 1015 615" fill="none" stroke="#7f0019" stroke-width="5" stroke-linecap="round"/>
    </svg>
  </div>

  <div class="container">
    <div class="header">
      <div class="header-title">
        <h1>YT Auto-Clipper</h1>
        <p>Convert YouTube videos or local MP4 files into 9:16 Shorts with live preview, dynamic captions & BGM</p>
      </div>
      <a class="saweria-btn" href="{SAWERIA_URL}" target="_blank" rel="noopener noreferrer">
        <span>&#9749;</span> Support on Saweria
      </a>
    </div>

    <div class="workspace">
      <div>
        <div class="card">
          <div class="source-box">
            <div class="form-group" style="margin-bottom:0;">
              <label class="field-label">Option 1: Paste YouTube URL (Max 5 Hours)</label>
              <input type="text" id="youtubeUrl" placeholder="https://www.youtube.com/watch?v=..." oninput="onYoutubeInput()" />
            </div>

            <div class="local-file-row">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <label class="file-picker-btn" for="localVideoFile">
                  <span>&#128194;</span> Select File (Local MP4)
                </label>
                <input type="file" id="localVideoFile" accept="video/mp4,.mp4" style="display:none;" onchange="onLocalVideoSelected(this)" />
                <span class="picked-file-name" id="localVideoLabel">No local MP4 selected</span>
              </div>
              <button type="button" class="clear-file-btn" id="clearVideoBtn" onclick="clearLocalVideo()" style="display:none;">Clear</button>
            </div>

            <div class="local-file-row" id="localSrtRow" style="display:none;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <label class="file-picker-btn secondary-pick" for="localSrtFile">
                  <span>&#128172;</span> Select .SRT Caption (Optional)
                </label>
                <input type="file" id="localSrtFile" accept=".srt,text/plain" style="display:none;" onchange="onLocalSrtSelected(this)" />
                <span class="picked-file-name" id="localSrtLabel">No .SRT selected (auto-transcribe voice if needed)</span>
              </div>
              <button type="button" class="clear-file-btn" id="clearSrtBtn" onclick="clearLocalSrt()" style="display:none;">Clear</button>
            </div>
          </div>

          <div class="grid-3">
            <div class="form-group">
              <label class="field-label">Duration per Clip (s)</label>
              <input type="number" id="clipDuration" value="30" min="5" max="180" />
            </div>
            <div class="form-group">
              <label class="field-label">Max Clips</label>
              <input type="number" id="maxClips" value="3" min="1" max="50" />
            </div>
            <div class="form-group">
              <label class="field-label">Caption Font</label>
              <select id="fontName" onchange="updatePreview()">
{FONT_OPTIONS_HTML}
              </select>
            </div>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="field-label">Caption Font Size <span class="val" id="fontSizeLabel">74 px</span></label>
              <input type="range" id="fontSize" min="40" max="120" step="2" value="74" oninput="updatePreview()" />
            </div>
            <div class="form-group">
              <label class="field-label">Caption Sync Offset <span class="val" id="offsetLabel">0.0s</span></label>
              <input type="range" id="captionOffset" min="-2.0" max="2.0" step="0.1" value="0.0"
                     oninput="document.getElementById('offsetLabel').textContent = parseFloat(this.value).toFixed(1) + 's'" />
            </div>
          </div>

          <div class="grid-3">
            <div class="form-group">
              <label class="field-label">Video Layout Mode</label>
              <select id="layoutMode" onchange="updatePreview()">
                <option value="crop" selected>Full-Screen 9:16 Crop</option>
                <option value="blur">16:9 Fit + Blurred BG</option>
              </select>
            </div>
            <div class="form-group">
              <label class="field-label">Top Hook Text (Optional)</label>
              <input type="text" id="hookText" placeholder="e.g. WAIT FOR THE END" maxlength="42" oninput="updatePreview()" />
            </div>
            <div class="form-group">
              <label class="field-label">Channel Watermark (Optional)</label>
              <input type="text" id="watermarkText" placeholder="e.g. @YourChannel" maxlength="32" oninput="updatePreview()" />
            </div>
          </div>

          <div class="form-group">
            <label class="field-label">Original Video Volume <span class="val" id="srcVolLabel">1.0</span></label>
            <input type="range" id="sourceVolume" min="0" max="2" step="0.05" value="1.0"
                   oninput="document.getElementById('srcVolLabel').textContent = this.value" />
          </div>

          <label class="toggle-row">
            <input type="checkbox" id="enableBgm" checked onchange="toggleBgmSection()" />
            <span>Include Background Music</span>
          </label>

          <div id="bgmSection">
            <div class="grid-2">
              <div class="form-group">
                <label class="field-label">BGM Source</label>
                <select id="bgmSourceType" onchange="toggleBgmSourceType()">
                  <option value="auto" selected>Auto-Fetch Royalty-Free Music</option>
                  <option value="custom">Use My Own Audio File</option>
                </select>
              </div>
              <div class="form-group">
                <label class="field-label">Background Music Volume <span class="val" id="bgmVolLabel">0.22</span></label>
                <input type="range" id="bgmVolume" min="0" max="1" step="0.02" value="0.22"
                       oninput="document.getElementById('bgmVolLabel').textContent = this.value" />
              </div>
            </div>

            <div class="form-group" id="autoBgmModeGroup">
              <label class="field-label">Auto-Fetched Track Mode</label>
              <select id="bgmMode">
                <option value="per_clip" selected>Different Track per Clip</option>
                <option value="same_all">Same Track for All Clips</option>
              </select>
            </div>

            <div class="custom-bgm-box" id="customBgmGroup">
              <div class="local-file-row" style="margin-top:0;padding-top:0;border-top:none;">
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                  <label class="file-picker-btn secondary-pick" for="customBgmFile">
                    <span>&#127925;</span> Select Audio File
                  </label>
                  <input type="file" id="customBgmFile" accept="audio/*,.mp3,.m4a,.wav,.ogg" style="display:none;" onchange="onCustomBgmSelected(this)" />
                  <span class="picked-file-name" id="customBgmLabel">No custom audio selected</span>
                </div>
                <button type="button" class="clear-file-btn" id="clearBgmBtn" onclick="clearCustomBgm()" style="display:none;">Clear</button>
              </div>
            </div>
          </div>

          <button class="primary" id="generateBtn" onclick="startClipping()">Generate Shorts Clips</button>
          <div class="status" id="statusBox"></div>
        </div>
      </div>

      <div class="card preview-sticky">
        <div class="preview-title">
          <span>Live 9:16 Style Preview</span>
          <span class="preview-badge">1080x1920</span>
        </div>
        <div class="phone-frame" id="phoneFrame">
          <div class="dummy-bg-blur"></div>
          <div class="dummy-video-box mode-crop" id="dummyVideoBox">
            <span class="dummy-scene-label">16:9 Dummy Scene</span>
          </div>
          <div class="preview-hook" id="previewHook"></div>
          <div class="preview-caption" id="previewCaption">SAMPLE TEXT</div>
          <div class="preview-watermark" id="previewWatermark"></div>
        </div>
        <div class="preview-controls">
          <button type="button" onclick="cycleSamplePhrase()">Switch Sample Text</button>
          <button type="button" onclick="cycleSampleColor()">Switch Color</button>
        </div>
      </div>
    </div>

    <div class="card" id="resultsCard" style="display:none;">
      <div class="results-header">
        <h3 style="margin:0;color:#050505;">Generated Clips</h3>
        <a class="zip-btn" id="zipDownloadBtn" href="#">Download All (.ZIP)</a>
      </div>
      <div class="results-grid" id="resultsGrid"></div>
    </div>
  </div>

  <script>
    const SAMPLE_PHRASES = ["INSANE CLUTCH!", "NO WAY BRO", "WATCH THIS", "EPIC MOMENT"];
    const SAMPLE_COLORS = ["#00e6ff", "#ffffff", "#39ff14"];
    let phraseIdx = 0;
    let colorIdx = 0;

    function onYoutubeInput() {{
      const urlVal = document.getElementById('youtubeUrl').value.trim();
      const fileInput = document.getElementById('localVideoFile');
      if (urlVal && fileInput.files.length > 0) {{
        clearLocalVideo();
      }}
    }}

    function onLocalVideoSelected(input) {{
      if (input.files && input.files.length > 0) {{
        const file = input.files[0];
        document.getElementById('localVideoLabel').textContent = file.name;
        document.getElementById('clearVideoBtn').style.display = 'inline-block';
        document.getElementById('localSrtRow').style.display = 'flex';
        document.getElementById('youtubeUrl').value = '';
      }}
    }}

    function clearLocalVideo() {{
      document.getElementById('localVideoFile').value = '';
      document.getElementById('localVideoLabel').textContent = 'No local MP4 selected';
      document.getElementById('clearVideoBtn').style.display = 'none';
      document.getElementById('localSrtRow').style.display = 'none';
      clearLocalSrt();
    }}

    function onLocalSrtSelected(input) {{
      if (input.files && input.files.length > 0) {{
        document.getElementById('localSrtLabel').textContent = input.files[0].name;
        document.getElementById('clearSrtBtn').style.display = 'inline-block';
      }}
    }}

    function clearLocalSrt() {{
      document.getElementById('localSrtFile').value = '';
      document.getElementById('localSrtLabel').textContent = 'No .SRT selected (auto-transcribe voice if needed)';
      document.getElementById('clearSrtBtn').style.display = 'none';
    }}

    function onCustomBgmSelected(input) {{
      if (input.files && input.files.length > 0) {{
        const file = input.files[0];
        document.getElementById('customBgmLabel').textContent = file.name;
        document.getElementById('clearBgmBtn').style.display = 'inline-block';
      }}
    }}

    function clearCustomBgm() {{
      document.getElementById('customBgmFile').value = '';
      document.getElementById('customBgmLabel').textContent = 'No custom audio selected';
      document.getElementById('clearBgmBtn').style.display = 'none';
    }}

    function toggleBgmSection() {{
      const enabled = document.getElementById('enableBgm').checked;
      document.getElementById('bgmSection').style.display = enabled ? 'block' : 'none';
    }}

    function toggleBgmSourceType() {{
      const bgmType = document.getElementById('bgmSourceType').value;
      document.getElementById('autoBgmModeGroup').style.display = bgmType === 'auto' ? 'block' : 'none';
      document.getElementById('customBgmGroup').style.display = bgmType === 'custom' ? 'block' : 'none';
    }}

    function cycleSamplePhrase() {{
      phraseIdx = (phraseIdx + 1) % SAMPLE_PHRASES.length;
      document.getElementById('previewCaption').textContent = SAMPLE_PHRASES[phraseIdx];
    }}

    function cycleSampleColor() {{
      colorIdx = (colorIdx + 1) % SAMPLE_COLORS.length;
      document.getElementById('previewCaption').style.color = SAMPLE_COLORS[colorIdx];
    }}

    function updatePreview() {{
      const fontName = document.getElementById('fontName').value;
      const fontSize = parseInt(document.getElementById('fontSize').value, 10);
      const layoutMode = document.getElementById('layoutMode').value;
      const hookText = document.getElementById('hookText').value.trim();
      const watermarkText = document.getElementById('watermarkText').value.trim();

      document.getElementById('fontSizeLabel').textContent = fontSize + ' px';

      const phoneFrame = document.getElementById('phoneFrame');
      const scaleRatio = phoneFrame.clientWidth / 1080.0;
      const scaledPx = Math.max(12, Math.round(fontSize * scaleRatio));

      const capEl = document.getElementById('previewCaption');
      capEl.style.fontFamily = `'${{fontName}}', 'Arial Black', sans-serif`;
      capEl.style.fontSize = scaledPx + 'px';

      const boxEl = document.getElementById('dummyVideoBox');
      boxEl.className = 'dummy-video-box ' + (layoutMode === 'blur' ? 'mode-blur' : 'mode-crop');

      const hookEl = document.getElementById('previewHook');
      if (hookText) {{
        hookEl.style.display = 'block';
        hookEl.textContent = hookText.toUpperCase();
      }} else {{
        hookEl.style.display = 'none';
      }}

      const wmEl = document.getElementById('previewWatermark');
      if (watermarkText) {{
        wmEl.style.display = 'block';
        wmEl.textContent = watermarkText;
      }} else {{
        wmEl.style.display = 'none';
      }}
    }}

    window.addEventListener('resize', updatePreview);
    window.addEventListener('DOMContentLoaded', () => {{
      updatePreview();
      toggleBgmSourceType();
    }});

    function copyMeta(btn, text) {{
      navigator.clipboard.writeText(text);
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => {{ btn.textContent = orig; }}, 1500);
    }}

    async function startClipping() {{
      const youtubeUrl = document.getElementById('youtubeUrl').value.trim();
      const localVideoInput = document.getElementById('localVideoFile');
      const hasLocalVideo = localVideoInput.files && localVideoInput.files.length > 0;
      const localSrtInput = document.getElementById('localSrtFile');
      const hasLocalSrt = hasLocalVideo && localSrtInput.files && localSrtInput.files.length > 0;

      const enableBgm = document.getElementById('enableBgm').checked;
      const bgmSourceType = document.getElementById('bgmSourceType').value;
      const customBgmInput = document.getElementById('customBgmFile');
      const hasCustomBgm = customBgmInput.files && customBgmInput.files.length > 0;

      const statusBox = document.getElementById('statusBox');
      const btn = document.getElementById('generateBtn');
      const resultsCard = document.getElementById('resultsCard');
      const resultsGrid = document.getElementById('resultsGrid');

      if (!youtubeUrl && !hasLocalVideo) {{
        statusBox.className = 'status active error';
        statusBox.textContent = 'Please paste a YouTube URL or click Select File to choose a local MP4.';
        return;
      }}

      if (enableBgm && bgmSourceType === 'custom' && !hasCustomBgm) {{
        statusBox.className = 'status active error';
        statusBox.textContent = 'Please click Select Audio File to choose your background music track.';
        return;
      }}

      btn.disabled = true;
      btn.textContent = 'Processing... (Check terminal for live progress)';
      statusBox.className = 'status active';
      statusBox.textContent = 'Uploading local files (if selected) and rendering 9:16 highlight clips...';
      resultsCard.style.display = 'none';
      resultsGrid.innerHTML = '';

      const formData = new FormData();
      formData.append('youtube_url', youtubeUrl);
      if (hasLocalVideo) {{
        formData.append('local_video', localVideoInput.files[0], localVideoInput.files[0].name);
      }}
      if (hasLocalSrt) {{
        formData.append('local_srt', localSrtInput.files[0], localSrtInput.files[0].name);
      }}
      formData.append('source_volume', document.getElementById('sourceVolume').value);
      formData.append('enable_bgm', enableBgm ? 'true' : 'false');
      formData.append('bgm_source_type', bgmSourceType);
      formData.append('bgm_mode', document.getElementById('bgmMode').value);
      formData.append('bgm_volume', document.getElementById('bgmVolume').value);
      if (enableBgm && bgmSourceType === 'custom' && hasCustomBgm) {{
        formData.append('custom_bgm', customBgmInput.files[0], customBgmInput.files[0].name);
      }}
      formData.append('clip_duration', document.getElementById('clipDuration').value);
      formData.append('max_clips', document.getElementById('maxClips').value);
      formData.append('font_name', document.getElementById('fontName').value);
      formData.append('font_size', document.getElementById('fontSize').value);
      formData.append('caption_offset', document.getElementById('captionOffset').value);
      formData.append('layout_mode', document.getElementById('layoutMode').value);
      formData.append('hook_text', document.getElementById('hookText').value);
      formData.append('watermark_text', document.getElementById('watermarkText').value);

      try {{
        const res = await fetch('/api/generate', {{
          method: 'POST',
          body: formData
        }});
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'An error occurred during rendering.');

        statusBox.className = 'status active done';
        statusBox.textContent = `Done! ${{data.clips.length}} highlight clip(s) generated successfully.`;
        resultsCard.style.display = 'block';

        const filenames = [];
        data.clips.forEach((itemData, idx) => {{
          const clipPath = itemData.path;
          const filename = clipPath.split(/[\\\\/]/).pop();
          filenames.push(filename);
          const url = '/output/' + encodeURIComponent(filename);
          const metaCopyText = `Title: ${{itemData.title}}\\nTags: ${{itemData.tags}}`;

          const card = document.createElement('div');
          card.className = 'clip-card';
          card.innerHTML = `
            <video src="${{url}}" controls preload="metadata"></video>
            <div class="meta-box">
              <strong>Clip #${{idx + 1}}: ${{itemData.title}}</strong>
              <div class="meta-tags">Tags: ${{itemData.tags}}</div>
            </div>
            <div class="clip-actions">
              <a href="${{url}}" download="${{filename}}">Download MP4</a>
              <button class="copy-btn" type="button">Copy Title & Tags</button>
            </div>
          `;
          card.querySelector('.copy-btn').addEventListener('click', (e) => copyMeta(e.target, metaCopyText));
          resultsGrid.appendChild(card);
        }});

        const zipBtn = document.getElementById('zipDownloadBtn');
        zipBtn.href = '/api/zip?files=' + encodeURIComponent(filenames.join(','));
      }} catch (err) {{
        statusBox.className = 'status active error';
        statusBox.textContent = 'Error: ' + err.message;
      }} finally {{
        btn.disabled = false;
        btn.textContent = 'Generate Shorts Clips';
      }}
    }}
  </script>
</body>
</html>
"""


def _parse_multipart_form(content_type: str, raw_body: bytes) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}

    match = re.search(r'boundary=(?:"([^"]+)"|([^;\s]+))', content_type, re.IGNORECASE)
    if not match:
        return fields, files

    boundary_str = (match.group(1) or match.group(2) or "").strip()
    if not boundary_str:
        return fields, files

    delimiter = f"--{boundary_str}".encode("utf-8")
    chunks = raw_body.split(delimiter)

    for chunk in chunks[1:]:
        if chunk.startswith(b"--"):
            break
        part = chunk[2:] if chunk.startswith(b"\r\n") else chunk
        if part.endswith(b"\r\n"):
            part = part[:-2]
        if not part:
            continue

        header_sep = part.find(b"\r\n\r\n")
        if header_sep == -1:
            continue

        headers_raw = part[:header_sep].decode("utf-8", errors="replace")
        body_bytes = part[header_sep + 4 :]

        disp_match = re.search(r"Content-Disposition:[^\r\n]*", headers_raw, re.IGNORECASE)
        if not disp_match:
            continue
        disp_line = disp_match.group(0)

        name_match = re.search(r'\bname="([^"]+)"', disp_line)
        if not name_match:
            continue
        field_name = name_match.group(1)

        fname_match = re.search(r'\bfilename="([^"]*)"', disp_line)
        if fname_match is not None:
            orig_filename = os.path.basename(fname_match.group(1))
            if orig_filename:
                files[field_name] = (orig_filename, body_bytes)
        else:
            fields[field_name] = body_bytes.decode("utf-8", errors="replace")

    return fields, files


def _safe_filename(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(name))
    return cleaned or fallback


class ClipMakerHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/zip":
            qs = urllib.parse.parse_qs(parsed.query)
            raw_files = qs.get("files", [""])[0].split(",")
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for raw_name in raw_files:
                    safe_name = os.path.basename(raw_name.strip())
                    full_path = os.path.join("output", safe_name)
                    if safe_name and os.path.isfile(full_path):
                        zf.write(full_path, arcname=safe_name)
            zip_bytes = mem_zip.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="yt_shorts_clips.zip"')
            self.send_header("Content-Length", str(len(zip_bytes)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(zip_bytes)
            return

        if parsed.path.startswith("/output/"):
            filename = os.path.basename(urllib.parse.unquote(parsed.path[len("/output/"):]))
            file_path = os.path.join("output", filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Connection", "close")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        raw_body = self.rfile.read(content_length)
        cache_dir = get_temp_dir()
        fonts_dir = "fonts"

        try:
            if "multipart/form-data" in content_type:
                fields, files = _parse_multipart_form(content_type, raw_body)
            else:
                json_data = json.loads(raw_body.decode("utf-8"))
                fields = {k: str(v) for k, v in json_data.items() if v is not None}
                files = {}

            youtube_url = str(fields.get("youtube_url", fields.get("source", ""))).strip().strip('"')
            source = youtube_url
            display_title = ""
            uploaded_srt_path: str | None = None

            if "local_video" in files:
                orig_vid_name, vid_bytes = files["local_video"]
                if vid_bytes:
                    safe_vid = _safe_filename(orig_vid_name, "uploaded_source.mp4")
                    if not safe_vid.lower().endswith(".mp4"):
                        safe_vid = f"{safe_vid}.mp4"
                    uploaded_vid_path = os.path.join(cache_dir, f"upload_{safe_vid}")
                    with open(uploaded_vid_path, "wb") as f_out:
                        f_out.write(vid_bytes)
                    source = uploaded_vid_path
                    display_title = os.path.splitext(orig_vid_name)[0]

            if "local_srt" in files:
                orig_srt_name, srt_bytes = files["local_srt"]
                if srt_bytes:
                    safe_srt = _safe_filename(orig_srt_name, "uploaded_caption.srt")
                    if not safe_srt.lower().endswith(".srt"):
                        safe_srt = f"{safe_srt}.srt"
                    uploaded_srt_path = os.path.join(cache_dir, f"upload_{safe_srt}")
                    with open(uploaded_srt_path, "wb") as f_srt:
                        f_srt.write(srt_bytes)

            if not source:
                raise ValueError("Please paste a YouTube URL or select a local MP4 file.")

            source_volume = float(fields.get("source_volume", 1.0))
            enable_bgm = str(fields.get("enable_bgm", "true")).lower() in ("true", "1", "yes", "on")
            bgm_source_type = str(fields.get("bgm_source_type", "auto")).strip()
            bgm_mode = str(fields.get("bgm_mode", "per_clip")).strip()
            bgm_volume = float(fields.get("bgm_volume", 0.22)) if enable_bgm else 0.0
            clip_duration = int(fields.get("clip_duration", 30))
            max_clips = int(fields.get("max_clips", 3))
            font_name = str(fields.get("font_name", "Luckiest Guy")).strip()
            font_size = int(fields.get("font_size", 74))
            caption_offset = float(fields.get("caption_offset", 0.0))
            layout_mode = str(fields.get("layout_mode", "crop")).strip()
            hook_text = str(fields.get("hook_text", "")).strip()
            watermark_text = str(fields.get("watermark_text", "")).strip()

            selected_font = ensure_selected_font(font_name=font_name, fonts_dir=fonts_dir)
            segments, srt_path, video_title, video_description = prepare_media(
                source=source,
                output_dir=cache_dir,
                clip_duration=clip_duration,
                max_clips=max_clips,
                display_title=display_title,
            )
            effective_srt = uploaded_srt_path or srt_path

            bgm_paths: list[str] = []
            if enable_bgm:
                if bgm_source_type == "custom":
                    if "custom_bgm" not in files or not files["custom_bgm"][1]:
                        raise ValueError("Custom BGM selected, but no audio file was uploaded.")
                    orig_bgm_name, bgm_bytes = files["custom_bgm"]
                    safe_bgm = _safe_filename(orig_bgm_name, "custom_bgm.mp3")
                    custom_bgm_path = os.path.join(cache_dir, f"upload_bgm_{safe_bgm}")
                    with open(custom_bgm_path, "wb") as f_bgm:
                        f_bgm.write(bgm_bytes)
                    bgm_paths = [custom_bgm_path]
                else:
                    track_count = len(segments) if bgm_mode == "per_clip" else 1
                    bgm_paths = fetch_auto_bgm_list(
                        output_dir=cache_dir,
                        duration_sec=clip_duration + 5,
                        count=track_count,
                    )

            outputs = generate_clips(
                segments=segments,
                srt_path=effective_srt,
                output_dir="output",
                bgm_paths=bgm_paths,
                source_volume=source_volume,
                bgm_volume=bgm_volume,
                font_name=selected_font,
                font_size=font_size,
                caption_offset=caption_offset,
                fonts_dir=fonts_dir,
                layout_mode=layout_mode,
                hook_text=hook_text,
                watermark_text=watermark_text,
                video_title=video_title,
                video_description=video_description,
            )
            self._send_json(200, {"clips": outputs})
        except Exception as exc:
            traceback.print_exc()
            self._send_json(400, {"error": str(exc)})
        finally:
            _cleanup_cache(cache_dir)


def run_ui(host: str = "127.0.0.1", port: int = 7860) -> None:
    server = HTTPServer((host, port), ClipMakerHandler)
    url = f"http://{host}:{port}"
    print("=" * 60)
    print(f"   YT AUTO-CLIPPER UI running at: {url}")
    print("   Press Ctrl+C in terminal to stop the server.")
    print("=" * 60)
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Stopped.")
        server.server_close()


if __name__ == "__main__":
    run_ui()
    



