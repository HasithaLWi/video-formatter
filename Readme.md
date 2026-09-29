# PureClip

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FFmpeg: Bundled](https://img.shields.io/badge/FFmpeg-Bundled%20(7.1)-green.svg)](https://ffmpeg.org)
[![Electron 35](https://img.shields.io/badge/Electron-35.1-68217A.svg)](https://www.electronjs.org)
[![Author](https://img.shields.io/badge/Author-Hasitha%20Wijesinghe-0284c7.svg)](https://github.com/HasithaLWi)

**PureClip** is a high-performance media transcoding, privacy-cleaning, and video compression suite featuring a sleek **glassmorphic desktop GUI** and a dual-mode **command-line engine**.

It strips intrusive tracking metadata (camera serials, GPS coordinates, gyro telemetry) while reducing file sizes by up to **75%** with pristine visual fidelity.

---

## Features

- **Multi-Format Transcoding**:
  - **Video**: MP4 (H.264), WebM (VP9 / Opus), MKV, MOV, AVI.
  - **Audio Extraction**: MP3 (LAME), AAC, WAV, FLAC, OGG.
  - **High-Fidelity 2-Pass GIF**: Generates optimized 256-color palettes (`palettegen` + `paletteuse`) for crisp, artifact-free animated GIFs.
- **Instant Lossless Remuxing (`stream_copy`)**:
  - Change containers (e.g. MOV to MP4, or MP4 to MKV) in **under 1 second** without re-encoding or losing quality.
- **Privacy Shield (Metadata Stripping)**:
  - Strips GPS location tags, camera serial numbers, camera model data, and gyro telemetry by default (`-map_metadata -1`).
  - Toggle `--keep-metadata` if you wish to retain original metadata.
- **FastStart Web Streaming Optimization**:
  - Automatically moves the `moov` index atom to the front of MP4/MOV files (`-movflags +faststart`) so videos stream instantly in browsers and Discord without waiting for full downloads.
- **Apple ProRes & High-Bitdepth Ingestion**:
  - Ingests raw ProRes 4444 (12-bit `yuva444p12le`), automatically strips timecode tracks (`tmcd`), and maps pixel formats to universal web standards.
- **GPU Hardware-Accelerated Video Player Preview**:
  - Built-in preview player leverages DirectX 11 / DXVA2 GPU hardware decoding for fluid, stutter-free playback of 4K/60fps video files.
- **Zero-Config Bundled FFmpeg**:
  - Pre-packaged with FFmpeg 7.1 via `imageio-ffmpeg` -- no external installations or system PATH setup required.
- **Process Guardian & Instant Tree Cancellation**:
  - When cancelling a conversion, Windows Process Tree Kill (`taskkill /T /F`) forcefully terminates both Python and FFmpeg child processes immediately with zero background leaks and automatically cleans up partial files.

---

## Prerequisites

Before setting up the project, make sure you have installed:
1. **Python 3.10+**: [Download Python](https://www.python.org/downloads/) *(check "Add python.exe to PATH" during installation)*
2. **Node.js 18+ & npm**: [Download Node.js](https://nodejs.org/)
3. **Git**: [Download Git](https://git-scm.com/)

> **Note**: You **do not** need to install FFmpeg separately. PureClip bundles FFmpeg 7.1 automatically through `imageio-ffmpeg`.

---

## Quickstart (Installation & Running)

### 1. Clone the Repository

```bash
git clone https://github.com/HasithaLWi/video-formatter.git
cd video-formatter
```

### 2. Set Up Python Backend & Dependencies

#### On Windows (PowerShell):
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\activate

# Install Python backend package in editable mode
pip install -e .
```
*(If PowerShell restricts scripts, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use CMD below)*

#### On Windows (Command Prompt - CMD):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -e .
```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

### 3. Install Desktop GUI Dependencies

In the root directory of the project:

```bash
npm install
```

---

### 4. Run the Application

#### Option A: Launch the Desktop GUI (PureClip)
Make sure the Python virtual environment (`.venv`) is active, then run:

```bash
npm start
```
*The glassmorphic desktop interface will appear. Simply drag and drop any video, select your preferred format, and start compression!*

#### Option B: Run via CLI (Terminal)
With the `.venv` activated, you can run the `pureclip` command directly:

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

# Real-time machine-readable JSON streaming
pureclip input.mp4 -f mp4 --json
```

---

## Optimization Preset Guide

| Preset | Video Codec | Audio Codec | CRF | Description |
| :--- | :--- | :--- | :---: | :--- |
| **`stream_copy`** | `copy` | `copy` | -- | **Instant (<1s)** lossless container swap. Zero quality loss. |
| **`balanced`** *(Default)* | `libx264` | `aac` (128k) | 24 | Optimal size-to-quality balance (**~65-75% reduction**). |
| **`high_quality`** | `libx264` | `aac` (192k) | 20 | Visually indistinguishable from source. Near-original fidelity. |
| **`compact`** | `libx264` | `aac` (96k) | 28 | Maximum compression for messaging and email attachments. |
| **`webm`** | `libvpx-vp9` | `libopus` (128k) | 30 | Next-generation open-web standard with superior compression efficiency. |

---

## CLI Reference

```
usage: pureclip [-h] [-o OUTPUT]
                [-f {mp4,mkv,webm,mov,avi,mp3,aac,wav,flac,ogg,gif}]
                [-p {stream_copy,high_quality,balanced,compact,webm}]
                [--crf CRF] [--scale SCALE] [--fps FPS]
                [--target-mb TARGET_MB] [--audio-bitrate AUDIO_BITRATE]
                [--keep-metadata] [--no-faststart] [--info] [--json]
                [-v] [input]

Options:
  -o, --output OUTPUT       Destination output file path or directory
  -f, --format FORMAT       Target format (mp4, mkv, webm, mov, avi, mp3, aac, wav, flac, ogg, gif)
  -p, --preset PRESET       Encoding profile (default: balanced)
  --crf CRF                 Custom Constant Rate Factor (0-51, lower = higher quality)
  --scale SCALE             Target resolution scale (e.g. 1920:1080, 1280:720, 720:-1)
  --fps FPS                 Target framerate (e.g. 60, 30, 24, 15)
  --target-mb TARGET_MB     Target output size in Megabytes (MB)
  --audio-bitrate BITRATE   Target audio bitrate (e.g. 128k, 192k, 320k)
  --keep-metadata           Preserve camera GPS, serials, and device telemetry
  --no-faststart            Disable FastStart web streaming optimization
  --info                    Inspect and display file metadata then exit
  --json                    Emit newline-delimited JSON events to stdout for IPC
  -v, --version             Show program's version number and exit
```

---

## Testing

PureClip includes an automated test suite verifying all transcoding pipelines, format conversions, probe parsing, and JSON IPC streaming:

```bash
python -m unittest discover -s test -p "test_*.py" -v
```

---

## Project Architecture

```
video-formatter/
├── app/
│   ├── index.html          # Desktop interface with glassmorphism styling
│   ├── styles.css          # Dark-mode styling, animations, glowing accents
│   └── renderer.js         # Frontend controller, drag & drop, HTML5 player
├── electron/
│   ├── main.js             # Electron main process (IPC handlers, process tree killer)
│   └── preload.js          # Secure ContextBridge API
├── src/my_app/
│   ├── config.py           # Application constants & supported format matrix
│   ├── main.py             # Dual-mode CLI entry point
│   └── core/
│       ├── ffmpeg_bin.py   # Bundled FFmpeg locator & validator
│       ├── probe.py        # Media stream inspector (codecs, resolution, fps, duration)
│       ├── presets.py      # Transcoding profiles (CRF, bitrate budgets)
│       └── converter.py    # Non-blocking conversion engine & progress parser
├── test/
│   └── test_converter.py   # Unit & integration test suite
├── package.json            # Electron app configuration & metadata
├── pyproject.toml          # PEP 621 Python packaging
├── LICENSE                 # MIT License
└── README.md               # Documentation
```

---

## Author

**Hasitha Wijesinghe**
- GitHub: [@HasithaLWi](https://github.com/HasithaLWi)
- Email: `hasithalwi@github.com`

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
