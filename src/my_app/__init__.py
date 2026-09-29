"""Video Formatter & Compressor Package.

Copyright (c) 2026 Hasitha Wijesinghe (https://github.com/HasithaLWi)
Licensed under the MIT License.
"""

from .config import APP_NAME, APP_VERSION
from .core.converter import VideoConverter, convert_video
from .core.probe import MediaInfo, probe_media

__version__ = APP_VERSION
__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "VideoConverter",
    "convert_video",
    "MediaInfo",
    "probe_media",
]
