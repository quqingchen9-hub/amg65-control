#!/usr/bin/env python3
"""Generate app icon, menu-bar template, and preset preview images."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / 'desktop'
BUILD = DESKTOP / 'build'
PUBLIC = DESKTOP / 'public'

sys.path.insert(0, str(ROOT / 'tool'))
os.environ.setdefault(
    'AMG65_PRESET_DB',
    str(ROOT / 'vendor' / 'db' / 'ledlayer_v2.data'),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = [
        ('/System/Library/Fonts/Avenir Next Condensed.ttc', 8 if bold else 2),
        ('/System/Library/Fonts/Avenir Next.ttc', 8 if bold else 2),
        ('/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf', 0),
    ]
    for name, index in names:
        try:
            return ImageFont.truetype(name, size, index=index)
        except Exception:
            continue
    return ImageFont.load_default()


def make_icon() -> None:
    scale = 4
    size = 1024
    canvas = Image.new('RGBA', (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    margin = 48 * scale
    box = (margin, margin, size * scale - margin, size * scale - margin)

    # Light glass tile with a restrained cool-blue edge.
    radius = 210 * scale
    d.rounded_rectangle(box, radius=radius, fill=(248, 250, 253, 255))
    inner = (
        margin + 4 * scale,
        margin + 4 * scale,
        size * scale - margin - 4 * scale,
        size * scale - margin - 4 * scale,
    )
    d.rounded_rectangle(
        inner,
        radius=radius - 3 * scale,
        outline=(188, 205, 225, 255),
        width=3 * scale,
    )

    # A soft inner pane keeps the icon dimensional without looking like a keycap.
    bx0, by0, bx1, by1 = 112 * scale, 112 * scale, 912 * scale, 912 * scale
    d.rounded_rectangle(
        (bx0, by0, bx1, by1),
        radius=158 * scale,
        fill=(255, 255, 255, 238),
        outline=(255, 255, 255, 255),
        width=2 * scale,
    )

    # The official product carries an AMG wordmark; a compact typographic version
    # stays legible at Dock and Finder sizes without copying a low-res photo.
    f = font(294 * scale, bold=True)
    text = 'AMG'
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(
        ((size * scale - tw) / 2 - bbox[0], (size * scale - th) / 2 - bbox[1] - 6 * scale),
        text,
        font=f,
        fill=(29, 29, 31, 255),
    )

    # Small blue status dot, echoing the app's connection indicator.
    dot_y = 680 * scale
    d.ellipse(
        (504 * scale, dot_y, 520 * scale, dot_y + 16 * scale),
        fill=(10, 132, 255, 255),
    )

    canvas.resize((size, size), Image.LANCZOS).save(BUILD / 'icon-1024.png')

    iconset = BUILD / 'icon.iconset'
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    source = Image.open(BUILD / 'icon-1024.png')
    for points, suffix in [
        (16, '16x16'),
        (32, '16x16@2x'),
        (32, '32x32'),
        (64, '32x32@2x'),
        (128, '128x128'),
        (256, '128x128@2x'),
        (256, '256x256'),
        (512, '256x256@2x'),
        (512, '512x512'),
        (1024, '512x512@2x'),
    ]:
        source.resize((points, points), Image.LANCZOS).save(iconset / f'icon_{suffix}.png')
    os.system(f'iconutil -c icns "{iconset}" -o "{BUILD / "icon.icns"}"')


def make_tray() -> None:
    # macOS template images use black artwork plus alpha. The wordmark is kept
    # visually narrower than the 18pt menu-bar slot, with breathing room around it.
    for scale, suffix in ((1, ''), (2, '@2x')):
        width, height = 34 * scale, 34 * scale
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        f = font(15 * scale, bold=True)
        text = 'AMG'
        bbox = d.textbbox((0, 0), text, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (width - tw) / 2 - bbox[0]
        y = (height - th) / 2 - bbox[1] - 1 * scale
        d.text((x, y), text, font=f, fill=(0, 0, 0, 255))
        image.save(BUILD / f'trayTemplate{suffix}.png')


def make_preset_previews() -> None:
    from presets import DB_PATH

    if not Path(DB_PATH).is_file():
        print(f'Preset previews skipped: {DB_PATH} is not available')
        return

    from presets import PRESETS, preset_images

    out = PUBLIC / 'presets'
    out.mkdir(parents=True, exist_ok=True)
    for name in PRESETS:
        frames = preset_images(name)
        frame = frames[len(frames) // 3]
        frame.resize((504, 40), Image.NEAREST).save(out / f'{name}.png')


def copy_web_assets() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'panel' / 'static' / 'keyboard.png', PUBLIC / 'keyboard.png')


if __name__ == '__main__':
    BUILD.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    make_icon()
    make_tray()
    make_preset_previews()
    copy_web_assets()
    print('Generated desktop assets in', BUILD, 'and', PUBLIC)
