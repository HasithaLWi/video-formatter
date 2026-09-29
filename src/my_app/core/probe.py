"""Media probing and metadata inspection module using FFmpeg."""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from .ffmpeg_bin import get_ffmpeg_binary


@dataclass
class MediaInfo:
    """Structured media file metadata."""

    file_path: str
    file_name: str
    file_size_bytes: int
    file_size_mb: float
    duration_seconds: float
    duration_str: str
    bitrate_kbps: int
    format_name: str
    has_video: bool
    has_audio: bool

    # Video details
    video_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    pix_fmt: Optional[str] = None

    # Audio details
    audio_codec: Optional[str] = None
    audio_sample_rate_hz: Optional[int] = None
    audio_channels: Optional[str] = None
    audio_bitrate_kbps: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Converts to a JSON-serializable dictionary for Electron IPC."""
        return asdict(self)

    @property
    def resolution_str(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "N/A"

    @property
    def aspect_ratio(self) -> str:
        if self.width and self.height and self.height > 0:
            ratio = self.width / self.height
            if abs(ratio - 16 / 9) < 0.05:
                return "16:9"
            if abs(ratio - 16 / 10) < 0.05 or abs(ratio - 8 / 5) < 0.05:
                return "16:10 (8:5)"
            if abs(ratio - 9 / 16) < 0.05:
                return "9:16 (Vertical/Mobile)"
            if abs(ratio - 4 / 3) < 0.05:
                return "4:3"
            if abs(ratio - 1.0) < 0.05:
                return "1:1 (Square)"
            return f"{ratio:.2f}:1"
        return "N/A"


def probe_media(file_path: str | Path) -> MediaInfo:
    """Inspects a video or audio file and returns detailed MediaInfo.

    Args:
        file_path: Path to the input file.

    Returns:
        MediaInfo object with video, audio, and container metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If FFmpeg fails to read the file.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ffmpeg_bin = get_ffmpeg_binary()
    file_size = path.stat().st_size

    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

    # FFmpeg outputs file probe information to stderr
    proc = subprocess.run(
        [ffmpeg_bin, "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        startupinfo=startupinfo,
    )

    stderr = proc.stderr

    duration_sec, duration_str = _parse_duration(stderr)
    bitrate_kbps = _parse_overall_bitrate(stderr)

    # Video details
    v_match = re.search(r"Stream #\d+:\d+.*?: Video: ([^,\n]+)", stderr)
    has_video = v_match is not None
    v_codec = v_match.group(1).split()[0] if v_match else None

    width, height = _parse_resolution(stderr)
    fps = _parse_fps(stderr)
    pix_fmt = _parse_pix_fmt(stderr)

    # Audio details
    a_match = re.search(r"Stream #\d+:\d+.*?: Audio: ([^,\n]+)", stderr)
    has_audio = a_match is not None
    a_codec = a_match.group(1).split()[0] if a_match else None
    sample_rate = _parse_sample_rate(stderr)
    channels = _parse_channels(stderr)
    audio_bitrate = _parse_audio_bitrate(stderr)

    container = path.suffix.lstrip(".").lower()

    return MediaInfo(
        file_path=str(path),
        file_name=path.name,
        file_size_bytes=file_size,
        file_size_mb=round(file_size / (1024 * 1024), 2),
        duration_seconds=duration_sec,
        duration_str=duration_str,
        bitrate_kbps=bitrate_kbps,
        format_name=container,
        has_video=has_video,
        has_audio=has_audio,
        video_codec=v_codec,
        width=width,
        height=height,
        fps=fps,
        pix_fmt=pix_fmt,
        audio_codec=a_codec,
        audio_sample_rate_hz=sample_rate,
        audio_channels=channels,
        audio_bitrate_kbps=audio_bitrate,
    )


def _parse_duration(stderr: str) -> tuple[float, str]:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr)
    if not match:
        return 0.0, "00:00:00"
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    total_sec = hours * 3600 + minutes * 60 + seconds
    str_repr = f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"
    return round(total_sec, 2), str_repr


def _parse_overall_bitrate(stderr: str) -> int:
    match = re.search(r"bitrate:\s*(\d+)\s*kb/s", stderr)
    return int(match.group(1)) if match else 0


def _parse_resolution(stderr: str) -> tuple[Optional[int], Optional[int]]:
    # Search specifically in the Video stream line first
    for line in stderr.splitlines():
        if "Video:" in line:
            match = re.search(r"\b(\d{2,5})x(\d{2,5})\b", line)
            if match:
                return int(match.group(1)), int(match.group(2))

    # General fallback search across full stderr
    match = re.search(r"\b(\d{2,5})x(\d{2,5})\b", stderr)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def _parse_fps(stderr: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*fps", stderr)
    if match:
        return float(match.group(1))
    return None


def _parse_pix_fmt(stderr: str) -> Optional[str]:
    match = re.search(r"Video:.*?,\s*([a-zA-Z0-9_]+(?:\([a-zA-Z0-9_\s,]+\))?),\s*\d+x\d+", stderr)
    if match:
        return match.group(1)
    return None


def _parse_sample_rate(stderr: str) -> Optional[int]:
    match = re.search(r"Audio:.*?, (\d+) Hz", stderr)
    if match:
        return int(match.group(1))
    return None


def _parse_channels(stderr: str) -> Optional[str]:
    match = re.search(r"Audio:.*?, \d+ Hz,\s*([^,\n]+)", stderr)
    if match:
        return match.group(1).strip()
    return None


def _parse_audio_bitrate(stderr: str) -> Optional[int]:
    match = re.search(r"Audio:.*?,\s*(\d+)\s*kb/s", stderr)
    if match:
        return int(match.group(1))
    return None
