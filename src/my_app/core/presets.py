"""Preset configurations and encoding profiles for Video Formatter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PresetProfile:
    """Configuration profile for a conversion or compression run."""

    name: str
    description: str
    video_codec: str
    audio_codec: str
    crf: Optional[int] = None
    preset_speed: str = "medium"
    strip_metadata: bool = True
    faststart: bool = True
    extra_video_flags: Optional[list[str]] = None
    extra_audio_flags: Optional[list[str]] = None


# Standard Preset Profiles
PRESETS: dict[str, PresetProfile] = {
    # 1. Lossless Stream Copy: Instantaneous (< 1 sec) container conversion without re-encoding
    "stream_copy": PresetProfile(
        name="stream_copy",
        description="Instant Lossless Remux (No re-encoding, 0% quality loss, strips metadata)",
        video_codec="copy",
        audio_codec="copy",
        crf=None,
        strip_metadata=True,
        faststart=True,
    ),
    # 2. High Quality: Visually indistinguishable from original, moderate compression
    "high_quality": PresetProfile(
        name="high_quality",
        description="High Quality (CRF 20, near-original fidelity, camera metadata stripped)",
        video_codec="libx264",
        audio_codec="aac",
        crf=20,
        preset_speed="medium",
        strip_metadata=True,
        faststart=True,
        extra_audio_flags=["-b:a", "192k"],
    ),
    # 3. Balanced: Best size-to-quality ratio (~60-75% reduction vs raw camera video)
    "balanced": PresetProfile(
        name="balanced",
        description="Balanced (CRF 24, optimal web & archive size, clean faststart)",
        video_codec="libx264",
        audio_codec="aac",
        crf=24,
        preset_speed="medium",
        strip_metadata=True,
        faststart=True,
        extra_audio_flags=["-b:a", "128k"],
    ),
    # 4. Compact: Maximum size reduction for quick sharing (email, chat)
    "compact": PresetProfile(
        name="compact",
        description="Compact (CRF 28, small size for messaging and attachments)",
        video_codec="libx264",
        audio_codec="aac",
        crf=28,
        preset_speed="fast",
        strip_metadata=True,
        faststart=True,
        extra_audio_flags=["-b:a", "96k"],
    ),
    # 5. WebM (VP9/Opus): Modern open-web format, superior compression
    "webm": PresetProfile(
        name="webm",
        description="Modern WebM (VP9 / Opus, next-gen web standard)",
        video_codec="libvpx-vp9",
        audio_codec="libopus",
        crf=30,
        preset_speed="medium",
        strip_metadata=True,
        faststart=False,
        extra_video_flags=["-b:v", "0"],  # Constrained quality mode for VP9
        extra_audio_flags=["-b:a", "128k"],
    ),
}


def get_preset_config(preset_name: str) -> PresetProfile:
    """Retrieves a preset profile by name with fallback to 'balanced'."""
    key = preset_name.lower().replace("-", "_")
    return PRESETS.get(key, PRESETS["balanced"])
