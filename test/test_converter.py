"""Comprehensive test suite for Video Formatter & Compressor."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.my_app.core.converter import VideoConverter, convert_video
from src.my_app.core.ffmpeg_bin import get_ffmpeg_binary
from src.my_app.core.probe import probe_media


class TestVideoConverter(unittest.TestCase):
    """Integration and unit tests for video conversion engine."""

    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_bin = get_ffmpeg_binary()
        cls.test_dir = tempfile.mkdtemp(prefix="vf_test_")
        cls.sample_mp4 = Path(cls.test_dir) / "sample.mp4"

        # Generate a 2-second 320x240 synthetic test video with audio and camera metadata
        cmd = [
            cls.ffmpeg_bin,
            "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-metadata", "title=SampleVideoSecretMeta",
            "-metadata", "artist=TestCameraDevice",
            str(cls.sample_mp4),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to generate synthetic test video:\n{res.stderr}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_ffmpeg_binary_available(self):
        """Validates that FFmpeg binary is detected and operational."""
        path = get_ffmpeg_binary()
        self.assertTrue(os.path.exists(path), f"FFmpeg path does not exist: {path}")

    def test_02_probe_media(self):
        """Validates media inspector returns accurate metadata."""
        info = probe_media(self.sample_mp4)
        self.assertEqual(info.file_name, "sample.mp4")
        self.assertTrue(info.has_video)
        self.assertTrue(info.has_audio)
        self.assertEqual(info.width, 320)
        self.assertEqual(info.height, 240)
        self.assertEqual(info.aspect_ratio, "4:3")
        self.assertAlmostEqual(info.duration_seconds, 2.0, delta=0.5)
        self.assertIn(info.video_codec, ("h264", "libx264"))
        self.assertEqual(info.audio_codec, "aac")

    def test_03_stream_copy_lossless(self):
        """Validates stream copy remuxing (MP4 -> MOV) without re-encoding."""
        out_mov = Path(self.test_dir) / "out_copy.mov"
        result = convert_video(
            input_path=self.sample_mp4,
            output_path=out_mov,
            preset="stream_copy",
        )
        self.assertTrue(out_mov.exists())
        self.assertGreater(out_mov.stat().st_size, 0)
        self.assertEqual(result.target_format, "mov")
        # Stream copy should take well under 2 seconds for a 2s clip
        self.assertLess(result.elapsed_time_seconds, 3.0)

    def test_04_balanced_compression_and_metadata_stripping(self):
        """Validates balanced encoding and metadata stripping."""
        out_mp4 = Path(self.test_dir) / "out_balanced.mp4"
        result = convert_video(
            input_path=self.sample_mp4,
            output_path=out_mp4,
            preset="balanced",
            strip_metadata=True,
            faststart=True,
        )
        self.assertTrue(out_mp4.exists())
        self.assertGreater(out_mp4.stat().st_size, 0)
        self.assertTrue(result.metadata_stripped)

        info = probe_media(out_mp4)
        self.assertTrue(info.has_video)
        self.assertTrue(info.has_audio)

    def test_05_webm_vp9_conversion(self):
        """Validates VP9/Opus WebM conversion."""
        out_webm = Path(self.test_dir) / "out.webm"
        result = convert_video(
            input_path=self.sample_mp4,
            output_path=out_webm,
            preset="webm",
        )
        self.assertTrue(out_webm.exists())
        info = probe_media(out_webm)
        self.assertIn("vp9", info.video_codec.lower())
        self.assertEqual(info.audio_codec.lower(), "opus")

    def test_06_gif_creation(self):
        """Validates 2-pass palette GIF conversion."""
        out_gif = Path(self.test_dir) / "out.gif"
        progress_events = []

        result = convert_video(
            input_path=self.sample_mp4,
            output_path=out_gif,
            target_format="gif",
            scale="160:-1",
            fps=10,
            progress_callback=lambda p: progress_events.append(p.percent),
        )
        self.assertTrue(out_gif.exists())
        self.assertGreater(out_gif.stat().st_size, 0)
        self.assertTrue(len(progress_events) > 0)
        info = probe_media(out_gif)
        self.assertEqual(info.width, 160)

    def test_07_audio_extraction_mp3(self):
        """Validates MP3 audio extraction from video."""
        out_mp3 = Path(self.test_dir) / "audio.mp3"
        result = convert_video(
            input_path=self.sample_mp4,
            output_path=out_mp3,
            target_format="mp3",
            audio_bitrate="128k",
        )
        self.assertTrue(out_mp3.exists())
        info = probe_media(out_mp3)
        self.assertFalse(info.has_video)
        self.assertTrue(info.has_audio)
        self.assertEqual(info.audio_codec, "mp3")

    def test_08_cli_json_stream_output(self):
        """Validates CLI --json flag output structure for Electron IPC."""
        py_exe = sys.executable
        out_json_mp4 = Path(self.test_dir) / "cli_out.mp4"

        cmd = [
            py_exe,
            "-m", "src.my_app.main",
            str(self.sample_mp4),
            "-o", str(out_json_mp4),
            "-f", "mp4",
            "-p", "stream_copy",
            "--json",
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        self.assertEqual(proc.returncode, 0, f"CLI error:\n{proc.stderr}")

        event_types = set()
        for line in proc.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                event_types.add(event.get("type"))
            except json.JSONDecodeError:
                pass

        self.assertIn("probe", event_types)
        self.assertIn("complete", event_types)


if __name__ == "__main__":
    unittest.main()
