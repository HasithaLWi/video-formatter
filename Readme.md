# 🎥 Video Formatter & Compressor

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FFmpeg: Bundled](https://img.shields.io/badge/FFmpeg-Bundled%20(7.1)-green.svg)](https://ffmpeg.org)
[![Electron Ready](https://img.shields.io/badge/Electron-IPC%20Ready-68217A.svg)](https://www.electronjs.org)

A high-performance media conversion, compression, and privacy-cleaning engine written in Python. Designed as both a feature-packed terminal CLI and a backend engine for future **Electron desktop applications** via real-time --json streaming.

---

## ✨ Features

- **Multi-Format Support**:
  - **Video**: MP4 (H.264), MKV, WebM (VP9/Opus), MOV, AVI.
  - **Audio Extraction**: MP3 (LAME), AAC, WAV, FLAC, OGG.
  - **High-Fidelity GIF**: 2-pass palette generation (palettegen + paletteuse) for crisp, artifact-free animated GIFs.
- **Instant Lossless Remuxing (stream_copy)**:
  - Container changes (e.g. MOV to MP4 or MP4 to MKV) complete in under **1 second** with zero re-encoding and zero quality degradation.
- **Privacy Cleaner (Camera & Device Metadata Stripping)**:
  - Strips GPS coordinates, camera serial numbers, camera model data, and gyro telemetry by default (-map_metadata -1).
  - Toggle --keep-metadata if you wish to retain original metadata.
- **Web Streaming Optimization (FastStart)**:
  - Automatically moves the moov atom to the front of MP4/MOV files (-movflags +faststart) so videos begin playback instantly without waiting for the full download.
- **Zero-Config FFmpeg Engine**:
  - Automatically detects and utilizes the bundled FFmpeg binary via imageio-ffmpeg, local binaries, or system PATH.
- **Dual-Mode Architecture**:
  - **Human CLI Mode**: Colorful ANSI summary cards and in-place progress bars with speed, fps, and ETA.
  - **Machine IPC Mode (--json)**: Emits newline-delimited JSON events to stdout for direct consumption by Electron, Node.js, Tauri, or web frontends.

---

## 🚀 Quickstart

### 1. Installation

`ash
# Clone or navigate to the repository
cd  F:\IJSE\THIRED SEM\PYTHON\video-formatter

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install in editable mode
pip install -e .
`

### 2. Basic Usage

`ash
# Convert to MP4 with balanced compression (~60-70% size reduction)
video-formatter video.mov -f mp4

# Instant lossless remux from MOV to MP4 (no quality loss, <1s)
video-formatter input.mov -f mp4 -p stream_copy

# Modern WebM conversion (VP9 / Opus)
video-formatter input.mp4 -f webm

# High-fidelity animated GIF (scaled to 480px width, 15 fps)
video-formatter clip.mp4 -f gif --scale 480:-1 --fps 15

# Extract high-quality MP3 audio track
video-formatter podcast.mp4 -f mp3 --audio-bitrate 192k

# Compress to fit exactly within a 25 MB file size limit (Discord, Email)
video-formatter recording.mp4 --target-mb 25

# Inspect media metadata without converting
video-formatter input.mp4 --info
`

---

## 🎛️ Preset Profiles

| Preset | Video Codec | Audio Codec | CRF | Description |
| :--- | :--- | :--- | :---: | :--- |
| stream_copy | copy | copy | — | **Instant (<1s)** lossless remux. Zero quality loss. |
| high_quality| libx264 | ac (192k) | 20 | Visually indistinguishable from source. Moderate compression. |
| alanced *(Default)* | libx264 | ac (128k) | 24 | Optimal quality-to-size balance (~60-75% reduction). |
| compact | libx264 | ac (96k) | 28 | Max compression for email and messaging attachments. |
| webm | libvpx-vp9 | libopus (128k)| 30 | Next-generation open web standard. Superior compression efficiency. |

---

## ⚙️ CLI Reference

`
usage: video-formatter [-h] [-o OUTPUT] [-f FORMAT] [-p PRESET]
                       [--crf CRF] [--scale SCALE] [--fps FPS]
                       [--target-mb TARGET_MB] [--audio-bitrate AUDIO_BITRATE]
                       [--keep-metadata] [--no-faststart] [--info] [--json]
                       [-v] [input]

Options:
  -o, --output OUTPUT       Destination file or directory
  -f, --format FORMAT       Target format (mp4, mkv, webm, mov, avi, mp3, aac, wav, gif)
  -p, --preset PRESET       Encoding profile (stream_copy, high_quality, balanced, compact, webm)
  --crf CRF                 Custom Constant Rate Factor (0-51)
  --scale SCALE             Target resolution scale (e.g. 1920:1080, 1280:720, 720:-1)
  --fps FPS                 Target framerate (e.g. 60, 30, 15)
  --target-mb TARGET_MB     Target file size in MB (auto-calculates optimal bitrate)
  --audio-bitrate BITRATE   Audio bitrate (e.g. 128k, 192k, 320k)
  --keep-metadata           Preserve camera GPS, serials, and device telemetry
  --no-faststart            Disable FastStart web streaming optimization
  --info                    Inspect and display media metadata, then exit
  --json                    Emit newline-delimited JSON stream for Electron IPC
  -v, --version             Show version number
`

---

## ⚡ Electron Desktop App Integration

When calling ideo-formatter with --json, it streams events as individual JSON objects per line over stdout.

### Electron Main Process Example (main.js / main.ts):

`javascript
const { spawn } = require('child_process');
const readline = require('readline');
const path = require('path');

function runVideoConversion(inputFilePath, options, win) {
  // Path to the Python virtual environment executable
  const pythonBin = path.join(__dirname, '..', '.venv', 'Scripts', 'video-formatter.exe');

  const args = [
    inputFilePath,
    '-f', options.format || 'mp4',
    '-p', options.preset || 'balanced',
    '--json'
  ];

  if (options.scale) args.push('--scale', options.scale);
  if (options.targetMb) args.push('--target-mb', options.targetMb.toString());
  if (options.keepMetadata) args.push('--keep-metadata');

  const child = spawn(pythonBin, args);
  const rl = readline.createInterface({ input: child.stdout });

  rl.on('line', (line) => {
    try {
      const event = JSON.parse(line.trim());
      
      switch (event.type) {
        case 'probe':
          // File inspected: { duration_seconds, resolution_str, format_name, ... }
          win.webContents.send('video:probe', event.data);
          break;

        case 'progress':
          // Live progress: { percent, speed, fps, eta_seconds, ... }
          win.webContents.send('video:progress', event.data);
          break;

        case 'complete':
          // Finished: { output_path, original_size_mb, output_size_mb, savings_pct, ... }
          win.webContents.send('video:complete', event.data);
          break;

        case 'error':
          win.webContents.send('video:error', event.data);
          break;
      }
    } catch (e) {
      console.error('Non-JSON stdout line:', line);
    }
  });

  child.stderr.on('data', (data) => {
    console.error(FFmpeg log: );
  });

  child.on('close', (code) => {
    console.log(Process exited with code );
  });

  return child; // Retain reference to call child.kill() on user cancel
}
`

### JSON Stream Event Schema:

#### 1. probe (Emitted once after file analysis):
`json
{
  type: probe,
  data: {
    file_path: F:\\Videos\\vacation.mov,
    file_name: vacation.mov,
    file_size_mb: 142.5,
    duration_seconds: 34.2,
    duration_str: 00:00:34,
    resolution_str: 3840x2160,
    aspect_ratio: 16:9,
    video_codec: h264,
    fps: 59.94,
    has_audio: true,
    audio_codec: aac
  }
}
`

#### 2. progress (Emitted continuously during encoding):
`json
{
  type: progress,
  data: {
    percent: 45.6,
    current_seconds: 15.6,
    total_seconds: 34.2,
    speed: 2.8x,
    fps: 62.4,
    eta_seconds: 6.6,
    frame: 936
  }
}
`

#### 3. complete (Emitted upon successful encoding):
`json
{
  type: complete,
  data: {
    input_path: F:\\Videos\\vacation.mov,
    output_path: F:\\Videos\\output\\vacation_formatted.mp4,
    target_format: mp4,
    preset: balanced,
    original_size_mb: 142.5,
    output_size_mb: 38.1,
    savings_bytes: 109471334,
    savings_pct: 73.3,
    media_duration_seconds: 34.2,
    elapsed_time_seconds: 12.4,
    metadata_stripped: true
  }
}
`

---

## 🧪 Testing

Run the automated test suite across all media conversion pipelines:

`ash
# Run unit and integration tests
.\.venv\Scripts\python.exe -m unittest discover -s test -p test_*.py -v
`

---

## 📄 License

MIT License. Copyright (c) 2026 Hasitha Wijesinghe.