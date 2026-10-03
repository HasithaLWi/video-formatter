"""FFmpeg binary locator and validation module.

Locates bundled FFmpeg (via imageio-ffmpeg) or falls back to system PATH.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

_CACHED_FFMPEG_PATH: Optional[str] = None


def get_ffmpeg_binary() -> str:
    """Finds and returns the absolute path to a working FFmpeg binary.

    Resolution order:
    1. PyInstaller / Nuitka frozen application bundled path
    2. imageio-ffmpeg bundled binary
    3. System PATH (ffmpeg)

    Returns:
        Absolute path to the ffmpeg executable.

    Raises:
        RuntimeError: If no working FFmpeg binary could be found.
    """
    global _CACHED_FFMPEG_PATH
    if _CACHED_FFMPEG_PATH and os.path.exists(_CACHED_FFMPEG_PATH):
        return _CACHED_FFMPEG_PATH

    candidates: list[str] = []

    # 1. Check frozen PyInstaller environment
    if getattr(sys, "frozen", False):
        exe_dir_ffmpeg = Path(sys.executable).parent / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if exe_dir_ffmpeg.exists():
            candidates.append(str(exe_dir_ffmpeg))
        if hasattr(sys, "_MEIPASS"):
            meipass_ffmpeg = Path(sys._MEIPASS) / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
            if meipass_ffmpeg.exists():
                candidates.append(str(meipass_ffmpeg))

    # 2. Check imageio-ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore
        exe_path = imageio_ffmpeg.get_ffmpeg_exe()
        if exe_path and os.path.exists(exe_path):
            candidates.append(exe_path)
    except (ImportError, Exception):
        pass

    # 3. Check System PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        candidates.append(system_ffmpeg)

    # 4. Check local project directory
    local_bin = Path(__file__).resolve().parent.parent / "bin" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    if local_bin.exists():
        candidates.append(str(local_bin))

    for candidate in candidates:
        if _is_working_ffmpeg(candidate):
            _CACHED_FFMPEG_PATH = candidate
            return candidate

    raise RuntimeError(
        "FFmpeg binary not found!\n"
        "Please install 'imageio-ffmpeg' via: pip install imageio-ffmpeg\n"
        "Or install FFmpeg and ensure 'ffmpeg' is on your system PATH."
    )


def _is_working_ffmpeg(path: str) -> bool:
    """Quickly tests if the given path is an executable FFmpeg."""
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        proc = subprocess.run(
            [path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            startupinfo=startupinfo,
        )
        return proc.returncode == 0 and "ffmpeg version" in proc.stdout.lower()
    except Exception:
        return False
