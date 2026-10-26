#!/usr/bin/env python3
"""AMG65 点阵屏命令行工具
用法:
  python3 amg65_cli.py color FF8800           # 纯色
  python3 amg65_cli.py gif xxx.gif [--fps 15] # 上传 GIF (自动缩放到 240x135, 最多130帧)
  python3 amg65_cli.py text "你好" [--color FFFFFF] [--bg 101020] [--size 60]
  python3 amg65_cli.py ping
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from amg65 import AMG65, SCREEN_W, SCREEN_H, MAX_FRAMES, FRAME_BYTES


def load_gif(path, fps=None, max_frames=MAX_FRAMES, fit='cover'):
    from PIL import Image, ImageSequence
    im = Image.open(path)
    frames, delays = [], []
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        if i >= max_frames:
            print(f'GIF 超过 {max_frames} 帧, 只取前 {max_frames} 帧')
            break
        rgb = fr.convert('RGB')
        if rgb.size != (SCREEN_W, SCREEN_H):
            rgb = _resize(rgb, fit)
        frames.append(rgb.tobytes())
        d = fr.info.get('duration', 80)
        delays.append(max(20, d))
    if fps:
        delays = [1000 // fps] * len(frames)
    return frames, delays


def _resize(img, fit):
    tw, th = SCREEN_W, SCREEN_H
    sw, sh = img.size
    scale = max(tw / sw, th / sh) if fit == 'cover' else min(tw / sw, th / sh)
    nw, nh = round(sw * scale), round(sh * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def hex2rgb(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def render_text(text, color, bg, size, font_path=None):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (SCREEN_W, SCREEN_H), bg)
    d = ImageDraw.Draw(img)
    if font_path:
        font = ImageFont.truetype(font_path, size)
    else:
        font = ImageFont.load_default()
        try:  # macOS 自带中文字体
            font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', size)
        except Exception:
            try:
                font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', size)
            except Exception:
                pass
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((SCREEN_W - w) // 2 - bbox[0], (SCREEN_H - h) // 2 - bbox[1]), text, font=font, fill=color)
    return [img.tobytes()]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='mode', required=True)
    pg = sub.add_parser('gif'); pg.add_argument('path'); pg.add_argument('--fps', type=int)
    pc = sub.add_parser('color'); pc.add_argument('rgb'); pc.add_argument('--delay', type=int, default=100)
    pt = sub.add_parser('text'); pt.add_argument('text'); pt.add_argument('--color', default='FFFFFF')
    pt.add_argument('--bg', default='101020'); pt.add_argument('--size', type=int, default=64)
    pt.add_argument('--font', default=None)
    sub.add_parser('ping')
    args = ap.parse_args()

    k = AMG65()
    try:
        print('ping:', k.ping().hex()[:8])
        if args.mode == 'ping':
            return
        if args.mode == 'color':
            frames = [k.rgb565_frame(lambda x, y, c=hex2rgb(args.rgb): c)]
            delays = [args.delay]
        elif args.mode == 'gif':
            frames, delays = load_gif(args.path, fps=args.fps)
            print(f'载入 {len(frames)} 帧, 转 RGB565 ...')
            frames = [k.rgb565_frame(f) for f in frames]
        elif args.mode == 'text':
            frames = render_text(args.text, hex2rgb(args.color), hex2rgb(args.bg), args.size, args.font)
            delays = [100]
        print(f'上传 {len(frames)} 帧 ...')
        k.upload_screen(frames, delays)
        print('完成 ✔ 屏幕已更新')
    finally:
        k.close()


if __name__ == '__main__':
    main()
