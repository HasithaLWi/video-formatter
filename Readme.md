# PureClip

<div align="center">
  <img src="app/assets/icon.png" alt="PureClip Logo" width="128" height="128" style="border-radius: 28px; box-shadow: 0 10px 30px rgba(56, 189, 248, 0.35);">
  <br>
  <h3>High-Performance Video Formatter, Privacy Cleaner & Compression Suite</h3>

  [![Platform: Windows | macOS | Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)](#cross-platform-builds)
  [![Electron: 35](https://img.shields.io/badge/Electron-35.7-68217A.svg)](https://www.electronjs.org)
  [![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://www.python.org/downloads/)
  [![FFmpeg: Bundled 7.1](https://img.shields.io/badge/FFmpeg-Bundled%20(7.1)-107C41.svg)](https://ffmpeg.org)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Author](https://img.shields.io/badge/Author-Hasitha%20Wijesinghe-0284c7.svg)](https://github.com/HasithaLWi)
</div>

---

**PureClip** is a professional desktop application and command-line engine designed for ultra-fast media transcoding, intelligent bitrate compression, and privacy-focused metadata stripping.

Built with a modern, glassmorphic **Electron UI** on top of a dedicated **headless Python transcoding engine**, PureClip strips intrusive camera telemetry (GPS coordinates, device serial numbers, hardware gyro logs) while shrinking video file sizes by **up to 75%** with pristine visual fidelity.

---

## ✨ Key Features

- **Multi-Format Transcoding**:
  - **Video**: MP4 (H.264), WebM (VP9 / Opus), MKV, MOV, AVI.
  - **Audio Extraction**: MP3 (LAME), AAC, WAV, FLAC, OGG.
  - **High-Fidelity 2-Pass GIF**: Generates optimized 256-color palettes (`palettegen` + `paletteuse`) for crisp, artifact-free animated GIFs.
- **Instant Lossless Remuxing (`stream_copy`)**:
  - Swap containers (e.g. MOV to MP4, or MP4 to MKV) in **under 1 second** with zero re-encoding or generational quality loss.
- **Privacy Shield (Metadata Stripping)**:
  - Strips GPS location tags, camera serial numbers, camera model data, and gyro telemetry by default (`-map_metadata -1`).
  - Toggle `--keep-metadata` if you wish to retain original camera metadata.
- **FastStart Web Streaming Optimization**:
  - Automatically moves the `moov` index atom to the front of MP4/MOV files (`-movflags +faststart`) so videos stream instantly in web browsers, Discord, and messaging apps without waiting for full downloads.
- **Apple ProRes & High-Bitdepth Ingestion**:
  - Ingests raw ProRes 4444 (12-bit `yuva444p12le`), automatically strips timecode tracks (`tmcd`), and maps pixel formats to universal web standards.
- **GPU Hardware-Accelerated Video Player Preview**:
  - Built-in preview player leverages DirectX 11 / DXVA2 GPU hardware decoding for fluid, stutter-free playback of 4K/60fps video files.
- **Zero-Config Bundled FFmpeg**:
  - Pre-packaged with official FFmpeg 7.1 -- no external installations or system PATH setup required.
- **Process Guardian & Instant Tree Cancellation**:
  - When cancelling a conversion, Windows Process Tree Kill (`taskkill /T /F`) forcefully terminates both Python and FFmpeg child processes immediately with zero background leaks and automatically cleans up partial files.
- **Dual-Distribution Output**:
  - Generates both a standard Windows NSIS setup wizard (`PureClip-Setup-0.1.0.exe`) and a zero-install portable single-file executable (`PureClip-Portable-0.1.0.exe`).

---

## 📥 Download & Releases

Pre-compiled standalone packages for Windows are available in the [Releases](https://github.com/HasithaLWi/video-formatter/releases) section:

| Package | Type | Description |
| :--- | :--- | :--- |
| **`PureClip-Setup-0.1.0.exe`** | **Installer** | Standard Windows installer with Desktop shortcut, Start Menu entry, and clean Windows uninstaller. |
| **`PureClip-Portable-0.1.0.exe`** | **Portable** | Single-file zero-install executable. Runs instantly anywhere (USB flash drive ready). |

---

## 🛠️ Prerequisites (For Developers)

To develop or build PureClip from source, ensure you have:
1. **Python 3.10+**: [Download Python](https://www.python.org/downloads/) *(ensure "Add python.exe to PATH" is checked)*
2. **Node.js 18+ & npm**: [Download Node.js](https://nodejs.org/)
3. **Git**: [Download Git](https://git-scm.com/)

> **Note**: You **do not** need to install FFmpeg separately. PureClip bundles FFmpeg 7.1 automatically through `imageio-ffmpeg`.

---

## 🚀 Quickstart & Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/HasithaLWi/video-formatter.git
cd video-formatter
```

### 2. Set Up the Python Virtual Environment
#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
pip install pyinstaller pillow
```
#### On Windows (Command Prompt):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -e .
pip install pyinstaller pillow
```
#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pyinstaller pillow
```

### 3. Install Desktop GUI Dependencies
```bash
npm install
```

### 4. Launch Desktop GUI in Development
```bash
npm start
```

---

## 📦 Building Standalone Desktop Binaries

PureClip utilizes a **stationary `--onedir` PyInstaller compilation** combined with `electron-builder` to produce self-contained binaries that require no client-side dependencies.

### Windows Builds (Run on Windows)
```cmd
# Build both Installer (.exe) and Portable (.exe)
npm.cmd run build:win

# Build ONLY the Portable standalone (.exe)
npm.cmd run build:win:portable
```
*Output binaries are generated inside the `release/` directory.*

### Cross-Platform Builds
* **macOS:** `npm run build:mac` *(Generates `.dmg` and `.zip`)*
* **Linux:** `npm run build:linux` *(Generates `.AppImage` and `.deb`)*
* **All Platforms via Cloud:** Push a version tag (e.g. `v0.1.0`) to trigger the automated [GitHub Actions CI/CD Workflow](.github/workflows/build.yml), which compiles native Windows, macOS, and Linux packages on cloud runners.

---

## 🛡️ Windows Defender SmartScreen & Antivirus Guide

When end-users download any newly compiled, open-source `.exe` from the web, Microsoft Defender SmartScreen displays a blue banner: *"Windows protected your PC — Unknown publisher"*.

### Why PureClip is Safe & How It Avoids False Positives:
1. **Stationary Engine (No `%TEMP%` Unpacking):**
   Unlike basic PyInstaller `--onefile` tools that unpack Python DLLs into `AppData\Local\Temp\` (which frequently triggers heuristic antivirus alerts like `Trojan:Win32/Wacatac`), PureClip utilizes a stationary `--onedir` directory structure inside `resources/bin/pureclip-engine/`.
2. **First-Time Launching:**
   Users simply click **"More info"** → **"Run anyway"**. Windows remembers this decision and will not prompt again.
3. **Bundled Documentation:**
   A complete [`HOW_TO_USE.txt`](HOW_TO_USE.txt) guide and FAQ is bundled with every release.

---

## 💻 CLI Usage Reference

With the Python environment active, PureClip can be run directly as a high-speed terminal utility:

```bash
# Basic conversion to MP4 with default balanced compression (~65-75% reduction)
pureclip video.mov -f mp4

# Instant lossless remux from MOV to MP4 (<1s, zero re-encoding)
pureclip input.mov -f mp4 -p stream_copy

# Transcode to modern WebM format (VP9 / Opus)
pureclip input.mp4 -f webm

# Convert video clip to crisp animated GIF (480px width at 15 fps)
pureclip clip.mp4 -f gif --scale 480:-1 --fps 15

# Extract high-quality MP3 audio track
pureclip lecture.mp4 -f mp3 --audio-bitrate 192k

# Compress to fit exactly within a target file size (e.g. 25 MB for Discord/Email)
pureclip recording.mp4 --target-mb 25

# Inspect media metadata without converting
pureclip input.mp4 --info

# Real-time machine-readable JSON streaming for external frontends
pureclip input.mp4 -f mp4 --json
```

---

## 🎛️ Optimization Preset Guide

| Preset | Video Codec | Audio Codec | CRF | Description |
| :--- | :--- | :--- | :---: | :--- |
| **`stream_copy`** | `copy` | `copy` | -- | **Instant (<1s)** lossless container swap. Zero quality loss. |
| **`balanced`** *(Default)* | `libx264` | `aac` (128k) | 24 | Optimal size-to-quality balance (**~65-75% reduction**). |
| **`high_quality`** | `libx264` | `aac` (192k) | 20 | Visually indistinguishable from source. Near-original fidelity. |
| **`compact`** | `libx264` | `aac` (96k) | 28 | Maximum compression for messaging and email attachments. |
| **`webm`** | `libvpx-vp9` | `libopus` (128k) | 30 | Modern open-web standard with superior compression efficiency. |

---

## 🧪 Automated Testing

PureClip includes a full automated test suite verifying all transcoding pipelines, format conversions, probe parsing, and JSON IPC streaming:

```bash
python -m unittest discover -s test -p "test_*.py" -v
```

---

## 📁 Repository Structure

```
video-formatter/
├── .github/
│   └── workflows/
│       └── build.yml       # Multi-platform CI/CD (Windows, macOS, Linux builds)
├── app/
│   ├── index.html          # Desktop interface with glassmorphism styling
│   ├── styles.css          # Dark-mode styling, animations, glowing accents
│   ├── renderer.js         # Frontend controller, drag & drop, HTML5 player
│   └── assets/             # Web icons & favicon
├── assets/
│   ├── icon.ico            # Windows multi-resolution icon (16px to 256px)
│   └── icon.png            # 512x512 master application icon
├── electron/
│   ├── main.js             # Electron main process (IPC handlers, process tree killer)
│   └── preload.js          # Secure ContextBridge API
├── scripts/
│   ├── build_engine.py     # Standalone PyInstaller engine compiler
│   └── create_icons.py     # Desktop icon generation script
├── src/
│   ├── run_engine.py       # Engine entry point for PyInstaller compilation
│   └── my_app/
│       ├── config.py       # Application constants & supported format matrix
│       ├── main.py         # Dual-mode CLI entry point
│       └── core/
│           ├── ffmpeg_bin.py   # Bundled FFmpeg locator & validator
│           ├── probe.py        # Media stream inspector (codecs, resolution, fps)
│           ├── presets.py      # Transcoding profiles (CRF, bitrate budgets)
│           └── converter.py    # Non-blocking conversion engine & progress parser
├── test/
│   └── test_converter.py   # Automated unit & integration test suite
├── HOW_TO_USE.txt          # User FAQ & SmartScreen instructions
├── package.json            # Electron app configuration & build scripts
├── pyproject.toml          # PEP 621 Python packaging configuration
├── LICENSE                 # MIT License
└── README.md               # Documentation
```

---

## 👤 Author

**Hasitha Wijesinghe**
- GitHub: [@HasithaLWi](https://github.com/HasithaLWi)
- Email: `hasithalwi@github.com`

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
