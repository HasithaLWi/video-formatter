"""Video conversion, compression, audio extraction, and GIF engine."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from .ffmpeg_bin import get_ffmpeg_binary
from .presets import PresetProfile, get_preset_config
from .probe import MediaInfo, probe_media


@dataclass
class ProgressInfo:
    """Real-time progress update emitted during conversion."""

    percent: float
    current_seconds: float
    total_seconds: float
    speed: str
    fps: float
    eta_seconds: float
    frame: int

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable representation for Electron IPC."""
        return asdict(self)


@dataclass
class ConversionResult:
    """Summary result returned upon conversion completion."""

    input_path: str
    output_path: str
    target_format: str
    preset: str
    original_size_bytes: int
    output_size_bytes: int
    original_size_mb: float
    output_size_mb: float
    savings_bytes: int
    savings_pct: float
    media_duration_seconds: float
    elapsed_time_seconds: float
    metadata_stripped: bool

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable representation for Electron IPC."""
        return asdict(self)


class VideoConverter:
    """Core engine for converting, compressing, and formatting video and audio files."""

    def __init__(self, ffmpeg_bin: Optional[str] = None):
        self.ffmpeg_bin = ffmpeg_bin or get_ffmpeg_binary()
        self.active_process: Optional[subprocess.Popen] = None

    def convert(
        self,
        input_path: str | Path,
        output_path: Optional[str | Path] = None,
        target_format: Optional[str] = None,
        preset: str = "balanced",
        crf: Optional[int] = None,
        scale: Optional[str] = None,
        fps: Optional[int] = None,
        strip_metadata: bool = True,
        faststart: bool = True,
        target_mb: Optional[float] = None,
        audio_bitrate: Optional[str] = None,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> ConversionResult:
        """Executes a conversion, compression, or format change on a media file.

        Args:
            input_path: Path to the source file.
            output_path: Optional destination path. If omitted, generated in 'output/'.
            target_format: Target extension (e.g. 'mp4', 'mkv', 'webm', 'mov', 'mp3', 'gif').
            preset: Encoding preset name ('stream_copy', 'high_quality', 'balanced', 'compact', 'webm').
            crf: Optional custom Constant Rate Factor (0-51). Overrides preset.
            scale: Optional resolution scaling (e.g. '1920:1080', '1280:720', '720:-1').
            fps: Optional target framerate (e.g. 30, 60).
            strip_metadata: Strip camera GPS, serials, and device metadata (-map_metadata -1).
            faststart: Move moov atom to front for web streaming (-movflags +faststart).
            target_mb: Target file size in MB. Automatically calculates optimal bitrate.
            audio_bitrate: Target audio bitrate (e.g. '192k', '128k', '320k').
            progress_callback: Callback function receiving ProgressInfo objects.

        Returns:
            ConversionResult with file sizes, savings, and duration.
        """
        in_path = Path(input_path).resolve()
        if not in_path.exists():
            raise FileNotFoundError(f"Input file not found: {in_path}")

        info = probe_media(in_path)
        total_duration = max(info.duration_seconds, 0.1)

        # Determine target format and output path
        out_format = self._resolve_target_format(in_path, output_path, target_format)
        out_path = self._resolve_output_path(in_path, output_path, out_format)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.perf_counter()

        # Handle specialized formats
        if out_format == "gif":
            self._convert_to_gif(
                in_path=in_path,
                out_path=out_path,
                scale=scale or "480:-1",
                fps=fps or 15,
                progress_callback=progress_callback,
                total_duration=total_duration,
            )
        elif out_format in ("mp3", "aac", "wav", "flac", "ogg"):
            self._extract_audio(
                in_path=in_path,
                out_path=out_path,
                out_format=out_format,
                bitrate=audio_bitrate or "192k",
                strip_metadata=strip_metadata,
                progress_callback=progress_callback,
                total_duration=total_duration,
            )
        else:
            self._convert_video_standard(
                in_path=in_path,
                out_path=out_path,
                out_format=out_format,
                info=info,
                preset_name=preset,
                crf=crf,
                scale=scale,
                fps=fps,
                strip_metadata=strip_metadata,
                faststart=faststart,
                target_mb=target_mb,
                audio_bitrate=audio_bitrate,
                total_duration=total_duration,
                progress_callback=progress_callback,
            )

        elapsed_sec = time.perf_counter() - start_time
        out_size = out_path.stat().st_size if out_path.exists() else 0
        in_size = in_path.stat().st_size
        savings_bytes = in_size - out_size
        savings_pct = round((savings_bytes / in_size * 100), 1) if in_size > 0 else 0.0

        return ConversionResult(
            input_path=str(in_path),
            output_path=str(out_path),
            target_format=out_format,
            preset=preset,
            original_size_bytes=in_size,
            output_size_bytes=out_size,
            original_size_mb=round(in_size / (1024 * 1024), 2),
            output_size_mb=round(out_size / (1024 * 1024), 2),
            savings_bytes=savings_bytes,
            savings_pct=savings_pct,
            media_duration_seconds=total_duration,
            elapsed_time_seconds=round(elapsed_sec, 2),
            metadata_stripped=strip_metadata,
        )

    def _convert_video_standard(
        self,
        in_path: Path,
        out_path: Path,
        out_format: str,
        info: MediaInfo,
        preset_name: str,
        crf: Optional[int],
        scale: Optional[str],
        fps: Optional[int],
        strip_metadata: bool,
        faststart: bool,
        target_mb: Optional[float],
        audio_bitrate: Optional[str],
        total_duration: float,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
    ):
        preset_cfg = get_preset_config(preset_name)

        cmd = [self.ffmpeg_bin, "-y", "-nostats", "-hide_banner", "-i", str(in_path)]

        # Safely map streams and discard data/timecode streams (e.g. tmcd from ProRes)
        cmd.extend(["-map", "0:v:0"])
        if info.has_audio:
            cmd.extend(["-map", "0:a:0?"])
        else:
            cmd.extend(["-an"])
        cmd.extend(["-dn"])

        # Video filters (scaling, framerate)
        vf_filters: list[str] = []
        if scale:
            vf_filters.append(f"scale={scale}")
        if fps:
            vf_filters.append(f"fps={fps}")

        is_stream_copy = preset_cfg.video_codec == "copy" and not vf_filters and not target_mb

        # Validate container & codec compatibility for stream copy
        v_codec_lower = (info.video_codec or "").lower()
        if is_stream_copy:
            if out_format == "webm" and v_codec_lower not in ("vp9", "vp8", "av1"):
                # WebM strictly forbids ProRes, H.264, etc. Must re-encode!
                is_stream_copy = False
            elif out_format in ("mp4", "m4v") and v_codec_lower not in ("h264", "hevc", "av1", "mp4v", "mpeg4"):
                # MP4 cannot hold ProRes/DNxHD directly. Must re-encode!
                is_stream_copy = False

        if is_stream_copy:
            cmd.extend(["-c:v", "copy"])
            if info.has_audio:
                cmd.extend(["-c:a", "copy"])
        else:
            # Codec selection based on format
            if out_format == "webm":
                vcodec = "libvpx-vp9"
                acodec = "libopus"
            else:
                vcodec = preset_cfg.video_codec if preset_cfg.video_codec != "copy" else "libx264"
                acodec = preset_cfg.audio_codec if preset_cfg.audio_codec != "copy" else "aac"

            cmd.extend(["-c:v", vcodec])

            # Apply filters
            if vf_filters:
                cmd.extend(["-vf", ",".join(vf_filters)])

            # Target file size bitrate calculation OR CRF
            if target_mb and target_mb > 0:
                audio_kbps = 128 if info.has_audio else 0
                target_kbits = target_mb * 8192
                video_kbits = target_kbits - (audio_kbps * total_duration)
                video_bitrate_kbps = max(int(video_kbits / total_duration), 100)
                cmd.extend(["-b:v", f"{video_bitrate_kbps}k", "-maxrate", f"{int(video_bitrate_kbps * 1.5)}k", "-bufsize", f"{video_bitrate_kbps * 2}k"])
            else:
                target_crf = crf if crf is not None else (preset_cfg.crf if preset_cfg.crf is not None else (30 if vcodec == "libvpx-vp9" else 23))
                cmd.extend(["-crf", str(target_crf)])
                if vcodec == "libvpx-vp9":
                    cmd.extend(["-b:v", "0"])

            if preset_cfg.preset_speed and vcodec == "libx264":
                cmd.extend(["-preset", preset_cfg.preset_speed])

            # Universal 8-bit YUV420P pixel format (converts 10-bit/12-bit/YUVA ProRes to universally playable web video)
            if vcodec in ("libx264", "libvpx-vp9"):
                cmd.extend(["-pix_fmt", "yuv420p"])

            # Audio codec & bitrate (only if file has audio)
            if info.has_audio:
                cmd.extend(["-c:a", acodec])
                a_bit = audio_bitrate or ("128k" if acodec == "libopus" else "192k")
                cmd.extend(["-b:a", a_bit])

        # Metadata stripping
        if strip_metadata:
            cmd.extend(["-map_metadata", "-1"])

        # MP4/MOV FastStart (moov atom front-loading)
        if faststart and out_format in ("mp4", "mov"):
            cmd.extend(["-movflags", "+faststart"])

        # Progress reporting via pipe:1
        cmd.extend(["-progress", "pipe:1", str(out_path)])

        self._execute_ffmpeg_progress(cmd, total_duration, progress_callback)

    def _convert_to_gif(
        self,
        in_path: Path,
        out_path: Path,
        scale: str,
        fps: int,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        total_duration: float,
    ):
        """2-pass high-fidelity GIF creation using palettegen and paletteuse."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            palette_png = Path(tmp_dir) / "palette.png"

            # Pass 1: Generate optimal 256-color palette
            pass1_cmd = [
                self.ffmpeg_bin,
                "-y",
                "-nostats",
                "-hide_banner",
                "-i",
                str(in_path),
                "-vf",
                f"fps={fps},scale={scale}:flags=lanczos,palettegen=stats_mode=diff",
                str(palette_png),
            ]
            self._run_silent(pass1_cmd)

            if progress_callback:
                progress_callback(
                    ProgressInfo(
                        percent=50.0,
                        current_seconds=total_duration * 0.5,
                        total_seconds=total_duration,
                        speed="2x",
                        fps=float(fps),
                        eta_seconds=1.0,
                        frame=0,
                    )
                )

            # Pass 2: Apply palette for crisp, artifact-free GIF
            pass2_cmd = [
                self.ffmpeg_bin,
                "-y",
                "-nostats",
                "-hide_banner",
                "-i",
                str(in_path),
                "-i",
                str(palette_png),
                "-filter_complex",
                f"[0:v] fps={fps},scale={scale}:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
                "-progress",
                "pipe:1",
                str(out_path),
            ]
            self._execute_ffmpeg_progress(pass2_cmd, total_duration, progress_callback, base_percent=50.0, scale_factor=0.5)

    def _extract_audio(
        self,
        in_path: Path,
        out_path: Path,
        out_format: str,
        bitrate: str,
        strip_metadata: bool,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        total_duration: float,
    ):
        """Extracts audio track with codec selection and metadata handling."""
        cmd = [self.ffmpeg_bin, "-y", "-nostats", "-hide_banner", "-i", str(in_path), "-vn"]

        if out_format == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
        elif out_format == "aac":
            cmd.extend(["-c:a", "aac", "-b:a", bitrate])
        elif out_format == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])
        elif out_format == "flac":
            cmd.extend(["-c:a", "flac"])
        elif out_format == "ogg":
            cmd.extend(["-c:a", "libvorbis", "-b:a", bitrate])

        if strip_metadata:
            cmd.extend(["-map_metadata", "-1"])

        cmd.extend(["-progress", "pipe:1", str(out_path)])
        self._execute_ffmpeg_progress(cmd, total_duration, progress_callback)

    def _execute_ffmpeg_progress(
        self,
        cmd: list[str],
        total_duration: float,
        progress_callback: Optional[Callable[[ProgressInfo], None]],
        base_percent: float = 0.0,
        scale_factor: float = 1.0,
    ):
        """Runs FFmpeg subprocess and reads real-time progress from pipe:1 safely."""
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
        )
        self.active_process = process

        stderr_lines: list[str] = []

        def _drain_stderr():
            if process.stderr:
                for s_line in iter(process.stderr.readline, ""):
                    stderr_lines.append(s_line)

        stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
        stderr_thread.start()

        current_frame = 0
        current_fps = 0.0
        current_speed = "1.0x"
        current_time_sec = 0.0

        try:
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    line = line.strip()
                    if not line:
                        continue

                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip()

                        if key == "frame":
                            try:
                                current_frame = int(val)
                            except ValueError:
                                pass
                        elif key == "fps":
                            try:
                                current_fps = float(val)
                            except ValueError:
                                pass
                        elif key == "speed":
                            current_speed = val
                        elif key == "out_time_us":
                            try:
                                current_time_sec = int(val) / 1_000_000.0
                            except ValueError:
                                pass
                        elif key == "progress" and progress_callback:
                            raw_pct = min(100.0, (current_time_sec / total_duration) * 100.0) if total_duration > 0 else 0.0
                            adjusted_pct = round(base_percent + (raw_pct * scale_factor), 1)

                            # Calculate ETA
                            speed_mult = 1.0
                            speed_match = re.search(r"(\d+(?:\.\d+)?)x", current_speed)
                            if speed_match:
                                try:
                                    speed_mult = float(speed_match.group(1))
                                except ValueError:
                                    speed_mult = 1.0

                            remaining_sec = max(0.0, total_duration - current_time_sec)
                            eta_sec = round(remaining_sec / max(speed_mult, 0.1), 1)

                            info = ProgressInfo(
                                percent=min(adjusted_pct, 100.0),
                                current_seconds=round(current_time_sec, 2),
                                total_seconds=round(total_duration, 2),
                                speed=current_speed,
                                fps=current_fps,
                                eta_seconds=eta_sec,
                                frame=current_frame,
                            )
                            progress_callback(info)
        finally:
            # Ensure FFmpeg is unconditionally killed if progress loop exits early (e.g. cancelled)
            if process.poll() is None:
                try:
                    process.kill()
                    process.wait(timeout=1.0)
                except Exception:
                    pass
            self.active_process = None

        if process.stdout:
            process.stdout.close()
        process.wait()
        stderr_thread.join(timeout=2.0)
        if process.stderr:
            process.stderr.close()
        stderr_text = "".join(stderr_lines)

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed (code {process.returncode}):\n{stderr_text}")

        # Final 100% callback
        if progress_callback:
            progress_callback(
                ProgressInfo(
                    percent=100.0,
                    current_seconds=round(total_duration, 2),
                    total_seconds=round(total_duration, 2),
                    speed=current_speed,
                    fps=current_fps,
                    eta_seconds=0.0,
                    frame=current_frame,
                )
            )

    def _run_silent(self, cmd: list[str]):
        """Runs an FFmpeg command synchronously without progress output."""
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
        )
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg command failed:\n{res.stderr}")

    def _resolve_target_format(self, in_path: Path, out_path: Optional[Path], target_format: Optional[str]) -> str:
        if target_format:
            return target_format.lstrip(".").lower()
        if out_path:
            return Path(out_path).suffix.lstrip(".").lower()
        return "mp4"

    def _resolve_output_path(self, in_path: Path, out_path: Optional[Path], target_format: str) -> Path:
        if out_path:
            p = Path(out_path)
            if not p.suffix:
                return p.with_suffix(f".{target_format}")
            return p

        # Default to 'output/' folder in project root
        output_dir = in_path.parent / "output" if in_path.parent.name != "output" else in_path.parent
        return output_dir / f"{in_path.stem}_formatted.{target_format}"


# Convenience functional API
def convert_video(
    input_path: str | Path,
    output_path: Optional[str | Path] = None,
    target_format: Optional[str] = None,
    preset: str = "balanced",
    crf: Optional[int] = None,
    scale: Optional[str] = None,
    fps: Optional[int] = None,
    strip_metadata: bool = True,
    faststart: bool = True,
    target_mb: Optional[float] = None,
    audio_bitrate: Optional[str] = None,
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
) -> ConversionResult:
    """Convenience helper to convert or compress a video file."""
    converter = VideoConverter()
    return converter.convert(
        input_path=input_path,
        output_path=output_path,
        target_format=target_format,
        preset=preset,
        crf=crf,
        scale=scale,
        fps=fps,
        strip_metadata=strip_metadata,
        faststart=faststart,
        target_mb=target_mb,
        audio_bitrate=audio_bitrate,
        progress_callback=progress_callback,
    )

