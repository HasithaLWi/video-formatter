"""Standalone runner entry point for PyInstaller compilation."""
import sys
from pathlib import Path

# Ensure src directory is in sys.path
src_dir = Path(__file__).resolve().parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from my_app.main import main

if __name__ == "__main__":
    main()
