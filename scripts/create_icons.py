"""Icon generation script for PureClip.

Converts the master image at app/assets/icon.png into all required desktop icon formats:
- assets/icon.png (512x512 master PNG for Linux / macOS / Electron)
- assets/icon.ico (Windows multi-resolution icon: 16, 24, 32, 48, 64, 128, 256)
- app/assets/icon.ico (Windows icon for web and local reference)
"""
from pathlib import Path
from PIL import Image

def generate_icons():
    root_dir = Path(__file__).resolve().parent.parent
    src_img_path = root_dir / "app" / "assets" / "icon.png"
    assets_dir = root_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    app_assets_dir = root_dir / "app" / "assets"
    app_assets_dir.mkdir(parents=True, exist_ok=True)

    if not src_img_path.exists():
        raise FileNotFoundError(f"Source icon not found at {src_img_path}")

    img = Image.open(src_img_path).convert("RGBA")

    # 1. Save standard 512x512 master PNG (for Linux & macOS electron-builder)
    icon_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    png_path = assets_dir / "icon.png"
    icon_512.save(png_path, format="PNG")
    print(f"[OK] Generated: {png_path} (512x512 PNG)")

    # 2. Save multi-resolution Windows ICO (16px to 256px)
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    ico_path = assets_dir / "icon.ico"
    img.save(ico_path, format="ICO", sizes=ico_sizes)
    print(f"[OK] Generated: {ico_path} (Multi-res ICO)")

    app_ico_path = app_assets_dir / "icon.ico"
    img.save(app_ico_path, format="ICO", sizes=ico_sizes)
    print(f"[OK] Generated: {app_ico_path}")

if __name__ == "__main__":
    generate_icons()
