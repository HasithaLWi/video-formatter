"""CLI Entry Point for Video Formatter & Compressor.

Provides both a human-friendly interactive terminal UI and a machine-readable
newline-delimited JSON stream for Electron IPC / desktop frontends.

Copyright (c) 2026 Hasitha Wijesinghe (https://github.com/HasithaLWi)
Licensed under the MIT License.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .config import ALL_SUPPORTED_FORMATS, APP_NAME, APP_VERSION
from .core.converter import ConversionResult, ProgressInfo, VideoConverter
from .core.presets import PRESETS
from .core.probe import MediaInfo, probe_media

# Configure UTF-8 on Windows consoles to prevent charmap UnicodeEncodeErrors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"
BLUE = "\033[34m"


def emit_json(event_type: str, data: dict):
    """Prints a newline-delimited JSON event to stdout for Electron IPC."""
    payload = {"type": event_type, "data": data}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def format_bytes(bytes_count: int) -> str:
    """Formats bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} TB"


def render_progress_bar(info: ProgressInfo, bar_width: int = 30):
    """Renders a smooth in-place progress bar in the terminal."""
    pct = max(0.0, min(100.0, info.percent))
    filled_len = int(bar_width * pct // 100)
    bar = "█" * filled_len + "░" * (bar_width - filled_len)

    speed_str = f"{info.speed}" if info.speed else "1.0x"
    fps_str = f"{info.fps:.0f} fps" if info.fps > 0 else ""
    eta_str = f"ETA: {int(info.eta_seconds)}s" if info.eta_seconds > 0 else "ETA: 0s"

    parts = [f"{CYAN}{BOLD}[{bar}]{RESET}", f"{GREEN}{pct:5.1f}%{RESET}", f"{DIM}{speed_str}{RESET}"]
    if fps_str:
        parts.append(f"{DIM}{fps_str}{RESET}")
    parts.append(f"{YELLOW}{eta_str}{RESET}")

    line = " | ".join(parts)
    sys.stdout.write(f"\r  {line}   ")
    sys.stdout.flush()


def print_banner():
    """Prints a stylish CLI header."""
    print(f"\n{CYAN}{BOLD}======================================================{RESET}")
    print(f"{CYAN}{BOLD}  🎥  {APP_NAME} v{APP_VERSION}{RESET}")
    print(f"{DIM}  Fast Video Conversion, Compression & Privacy Cleaner{RESET}")
    print(f"{CYAN}{BOLD}======================================================{RESET}\n")


def print_media_info_card(info: MediaInfo):
    """Prints a formatted terminal inspection card."""
    print(f"{BOLD}📂 File Details:{RESET}")
    print(f"  • Name:        {WHITE}{BOLD}{info.file_name}{RESET}")
    print(f"  • Size:        {YELLOW}{info.file_size_mb:.2f} MB{RESET} ({info.file_size_bytes:,} bytes)")
    print(f"  • Duration:    {WHITE}{info.duration_str}{RESET} ({info.duration_seconds:.2f}s)")
    print(f"  • Bitrate:     {WHITE}{info.bitrate_kbps} kbps{RESET}")
    print(f"  • Container:   {MAGENTA}{info.format_name.upper()}{RESET}")

    if info.has_video:
        print(f"\n{BOLD}🎬 Video Stream:{RESET}")
        print(f"  • Codec:       {WHITE}{info.video_codec}{RESET}")
        print(f"  • Resolution:  {GREEN}{info.resolution_str}{RESET} ({info.aspect_ratio})")
        print(f"  • Framerate:   {WHITE}{info.fps:.2f} fps{RESET}" if info.fps else "  • Framerate:   N/A")
        if info.pix_fmt:
            print(f"  • Pixel Fmt:   {DIM}{info.pix_fmt}{RESET}")

    if info.has_audio:
        print(f"\n{BOLD}🎵 Audio Stream:{RESET}")
        print(f"  • Codec:       {WHITE}{info.audio_codec}{RESET}")
        if info.audio_sample_rate_hz:
            print(f"  • Sample Rate: {WHITE}{info.audio_sample_rate_hz} Hz{RESET}")
        if info.audio_channels:
            print(f"  • Channels:    {WHITE}{info.audio_channels}{RESET}")
        if info.audio_bitrate_kbps:
            print(f"  • Bitrate:     {WHITE}{info.audio_bitrate_kbps} kbps{RESET}")
    print()


def print_summary_card(result: ConversionResult):
    """Prints the final summary after conversion."""
    print("\n")
    print(f"{GREEN}{BOLD}══════════════════════════════════════════════════════{RESET}")
    print(f"{GREEN}{BOLD}  ✨ Conversion Complete!{RESET}")
    print(f"{GREEN}{BOLD}══════════════════════════════════════════════════════{RESET}")
    print(f"  • Output:       {WHITE}{BOLD}{result.output_path}{RESET}")
    print(f"  • Target:       {MAGENTA}{result.target_format.upper()}{RESET} ({result.preset} preset)")

    # Size comparison
    if result.savings_pct > 0:
        savings_str = f"{GREEN}-{result.savings_pct:.1f}% ({format_bytes(result.savings_bytes)} saved){RESET}"
    elif result.savings_pct < 0:
        savings_str = f"{YELLOW}+{abs(result.savings_pct):.1f}% (increased){RESET}"
    else:
        savings_str = f"{WHITE}No size change{RESET}"

    print(f"  • Size:         {YELLOW}{result.original_size_mb:.2f} MB{RESET} → {GREEN}{BOLD}{result.output_size_mb:.2f} MB{RESET} [{savings_str}]")
    print(f"  • Time Elapsed: {WHITE}{result.elapsed_time_seconds:.2f}s{RESET}")

    privacy_tag = f"{GREEN}Yes (GPS/Exif removed){RESET}" if result.metadata_stripped else f"{YELLOW}No (Preserved){RESET}"
    print(f"  • Privacy Clean:{privacy_tag}")
    print(f"{GREEN}{BOLD}══════════════════════════════════════════════════════{RESET}\n")


def build_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="video-formatter",
        description=f"{APP_NAME} v{APP_VERSION} - Fast video converter, compressor, and metadata stripper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Preset Profiles:
  stream_copy   Instant (<1s) lossless container conversion without re-encoding
  high_quality  CRF 20, pristine quality, moderate size reduction
  balanced      CRF 24, optimal web & archive balance (Default, ~60-75% reduction)
  compact       CRF 28, small size for messaging, Discord, email attachments
  webm          VP9 / Opus modern open-web format

Examples:
  video-formatter input.mp4 -f webm
  video-formatter input.mov -f mp4 -p stream_copy
  video-formatter input.mp4 -f gif --scale 480:-1 --fps 15
  video-formatter lecture.mp4 -f mp3 --audio-bitrate 192k
  video-formatter input.mp4 --target-mb 25
  video-formatter input.mp4 --info
  video-formatter input.mp4 -f mp4 --json
        """,
    )

    parser.add_argument("input", nargs="?", help="Path to input video or audio file")
    parser.add_argument("-o", "--output", help="Destination output file path or directory")
    parser.add_argument(
        "-f",
        "--format",
        choices=ALL_SUPPORTED_FORMATS,
        help="Target format (mp4, mkv, webm, mov, mp3, aac, wav, gif)",
    )
    parser.add_argument(
        "-p",
        "--preset",
        choices=list(PRESETS.keys()),
        default="balanced",
        help="Encoding preset profile (default: balanced)",
    )
    parser.add_argument("--crf", type=int, help="Custom CRF value (0-51, lower = higher quality)")
    parser.add_argument("--scale", help="Target resolution scale (e.g. 1920:1080, 1280:720, 720:-1)")
    parser.add_argument("--fps", type=int, help="Target framerate (e.g. 30, 60, 15)")
    parser.add_argument("--target-mb", type=float, help="Target output size in Megabytes (MB)")
    parser.add_argument("--audio-bitrate", help="Target audio bitrate (e.g. 128k, 192k, 320k)")
    parser.add_argument(
        "--keep-metadata",
        action="store_true",
        help="Preserve original camera GPS, serial numbers, and device telemetry (default: stripped)",
    )
    parser.add_argument(
        "--no-faststart",
        action="store_true",
        help="Disable FastStart web streaming optimization (moov atom at front)",
    )
    parser.add_argument("--info", action="store_true", help="Inspect and display file metadata then exit")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit newline-delimited JSON events to stdout for Electron IPC / desktop frontends",
    )
    parser.add_argument("-v", "--version", action="version", version=f"{APP_NAME} v{APP_VERSION}")

    return parser


def main():
    """Main CLI execution flow."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        sys.exit(1)

    in_file = Path(args.input).resolve()
    if not in_file.exists():
        if args.json:
            emit_json("error", {"message": f"Input file not found: {in_file}"})
        else:
            print(f"{RED}{BOLD}Error:{RESET} Input file not found: {in_file}", file=sys.stderr)
        sys.exit(1)

    # 1. Probe Input
    try:
        media_info = probe_media(in_file)
    except Exception as exc:
        if args.json:
            emit_json("error", {"message": f"Failed to probe file: {exc}"})
        else:
            print(f"{RED}{BOLD}Error probing file:{RESET} {exc}", file=sys.stderr)
        sys.exit(1)

    # If --info requested, display and exit
    if args.info:
        if args.json:
            emit_json("probe", media_info.to_dict())
        else:
            print_banner()
            print_media_info_card(media_info)
        sys.exit(0)

    # Emit probe event if in JSON mode
    if args.json:
        emit_json("probe", media_info.to_dict())
    else:
        print_banner()
        print_media_info_card(media_info)
        print(f"{CYAN}{BOLD}🚀 Starting conversion...{RESET}")

    # Progress callback
    def on_progress(info: ProgressInfo):
        if args.json:
            emit_json("progress", info.to_dict())
        else:
            render_progress_bar(info)

    converter = VideoConverter()

    try:
        result = converter.convert(
            input_path=in_file,
            output_path=args.output,
            target_format=args.format,
            preset=args.preset,
            crf=args.crf,
            scale=args.scale,
            fps=args.fps,
            strip_metadata=not args.keep_metadata,
            faststart=not args.no_faststart,
            target_mb=args.target_mb,
            audio_bitrate=args.audio_bitrate,
            progress_callback=on_progress,
        )

        if args.json:
            emit_json("complete", result.to_dict())
        else:
            print_summary_card(result)

    except KeyboardInterrupt:
        if args.json:
            emit_json("cancelled", {"message": "Conversion cancelled by user"})
        else:
            print(f"\n{YELLOW}Conversion cancelled by user.{RESET}")
        sys.exit(130)
    except Exception as exc:
        if args.json:
            emit_json("error", {"message": str(exc)})
        else:
            print(f"\n{RED}{BOLD}Conversion error:{RESET} {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
