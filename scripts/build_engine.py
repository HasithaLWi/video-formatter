"""Standalone Engine Build Script for PureClip.

Compiles the Python backend and bundles FFmpeg into a stationary '--onedir' package:
- Target directory: bin/pureclip-engine/
- Main executable: pureclip-engine.exe (Windows) or pureclip-engine (macOS/Linux)
- Bundled FFmpeg: ffmpeg.exe (Windows) or ffmpeg (macOS/Linux)

Cross-platform compatible: works on Windows, macOS, and Linux.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


# Configure UTF-8 on Windows consoles to prevent charmap UnicodeEncodeErrors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    print("=" * 60)
    print(">> Building PureClip Standalone Engine (--onedir)")
    print(f"Platform: {sys.platform}")
    print("=" * 60)

    # 1. Resolve FFmpeg executable from imageio-ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg_src = Path(imageio_ffmpeg.get_ffmpeg_exe())
        print(f"Found bundled FFmpeg source: {ffmpeg_src}")
    except Exception as exc:
        print(f"Warning: Could not get FFmpeg from imageio_ffmpeg ({exc}). Checking PATH...")
        system_ffmpeg = shutil.which("ffmpeg")
        if not system_ffmpeg:
            raise RuntimeError("FFmpeg executable not found in imageio-ffmpeg or system PATH!")
        ffmpeg_src = Path(system_ffmpeg)

    # 2. Output and Work directories
    dist_dir = root_dir / "bin"
    work_dir = root_dir / "build" / "pyinstaller"
    spec_dir = root_dir / "build"

    # 3. Assemble PyInstaller command line
    is_win = sys.platform == "win32"
    engine_name = "pureclip-engine"
    exe_name = f"{engine_name}.exe" if is_win else engine_name
    ffmpeg_target_name = "ffmpeg.exe" if is_win else "ffmpeg"

    icon_file = root_dir / "assets" / ("icon.ico" if is_win else "icon.png")
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name", engine_name,
        "--onedir",
        "--noconfirm",
        "--clean",
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--specpath", str(spec_dir),
        "--paths", str(root_dir / "src"),
    ]
    if icon_file.exists():
        pyinstaller_cmd.extend(["--icon", str(icon_file)])
    pyinstaller_cmd.append(str(root_dir / "src" / "run_engine.py"))

    print("\nRunning PyInstaller...")
    print(" ".join(pyinstaller_cmd))
    res = subprocess.run(pyinstaller_cmd)
    if res.returncode != 0:
        print("\n[ERROR] PyInstaller compilation failed!")
        sys.exit(res.returncode)

    # 4. Copy FFmpeg executable into the stationary engine folder
    engine_dir = dist_dir / engine_name
    ffmpeg_dest = engine_dir / ffmpeg_target_name

    print(f"\nCopying FFmpeg binary to stationary engine directory:\n  {ffmpeg_src} -> {ffmpeg_dest}")
    shutil.copy2(ffmpeg_src, ffmpeg_dest)

    # Ensure executable permissions on Unix systems
    if not is_win:
        st = os.stat(ffmpeg_dest)
        os.chmod(ffmpeg_dest, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 5. Sanity Test: Execute compiled pureclip-engine
    built_exe = engine_dir / exe_name
    print(f"\nVerifying compiled engine at: {built_exe}")
    if not built_exe.exists():
        raise FileNotFoundError(f"Expected engine executable not found: {built_exe}")

    test_run = subprocess.run([str(built_exe), "--version"], capture_output=True, text=True)
    if test_run.returncode == 0:
        print(f"[OK] PureClip Engine compiled and verified successfully: {test_run.stdout.strip()}")
    else:
        print(f"[WARN] Engine sanity test returned code {test_run.returncode}: {test_run.stderr}")

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Build Complete: Stationary engine ready at {engine_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
