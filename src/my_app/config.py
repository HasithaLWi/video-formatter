"""Configuration and constants for Video Formatter & Compressor.

Copyright (c) 2026 Hasitha Wijesinghe (https://github.com/HasithaLWi)
Licensed under the MIT License.
"""
from pathlib import Path

# Application Metadata
APP_NAME = "PureClip"
APP_VERSION = "0.1.0"
AUTHOR = "Hasitha Wijesinghe"

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

# Supported Formats
SUPPORTED_VIDEO_FORMATS = ("mp4", "mkv", "webm", "mov", "avi")
SUPPORTED_AUDIO_FORMATS = ("mp3", "aac", "wav", "flac", "ogg")
SUPPORTED_ANIM_FORMATS = ("gif",)
ALL_SUPPORTED_FORMATS = SUPPORTED_VIDEO_FORMATS + SUPPORTED_AUDIO_FORMATS + SUPPORTED_ANIM_FORMATS
