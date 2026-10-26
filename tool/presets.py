#!/usr/bin/env python3
"""官方驱动预制的长条屏灯效 (圣诞树 / 极光 / 游戏 / 彩虹 / 俄罗斯方块)

来源 (DeviceDriver.exe 1.0.3.3 逆向):
  - 这些灯效不在固件里, 是驱动从 db/ledlayer_v2.data (SQLite) 读帧再下发的
    驱动 0x40d122: "SELECT * FROM t_default_led_frames WHERE layer_id = ?"
  - t_default_led_frames(layer_id, frameIndex, led_index, rgb_value), rgb_value = 0x00BBGGRR
  - layer 1 是 63x5 (开机 logo), layer 2..6 是另一款 70x7 屏的素材, 这里转成 63x5
转换方式按素材挑 (逐个看过渲染效果):
  pick = 70x7 截前 63 列后按最近邻抽 5 行 (树/字母轮廓清楚)
  box  = 面积平均缩放到 63x5 (渐变更顺)
  crop = 直接取 1..5 行 (俄罗斯方块本来只用这 5 行)
"""
import os
import sqlite3

import strip as STRP

_here = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('AMG65_PRESET_DB') or os.path.join(
    os.path.dirname(_here), 'vendor', 'db', 'ledlayer_v2.data')

# name -> (layer_id, 中文名, 转换方式)
PRESETS = {
    'christmas': (2, '圣诞树', 'pick'),
    'aurora':    (3, '极光', 'box'),
    'game':      (4, '游戏', 'pick'),
    'rainbow':   (5, '彩虹', 'box'),
    'tetris':    (6, '俄罗斯方块', 'crop'),
}
MAX_FRAMES = 260          # 04 33 帧数上限 (驱动 0x434a4a mov eax,0x104)
SRC_W, SRC_H = 70, 7

_cache = {}


def _load_images(layer):
    from PIL import Image
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(
            f'官方预制灯效数据库不存在: {DB_PATH}；'
            '请设置 AMG65_PRESET_DB 指向 ledlayer_v2.data')
    db = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    try:
        frames = {}
        for f, li, rgb in db.execute(
                'SELECT frameIndex, led_index, rgb_value FROM t_default_led_frames '
                'WHERE layer_id = ? ORDER BY frameIndex', (layer,)):
            im = frames.get(f)
            if im is None:
                im = frames[f] = Image.new('RGB', (SRC_W, SRC_H))
            if li < SRC_W * SRC_H:
                im.putpixel((li % SRC_W, li // SRC_W), (rgb & 0xFF, (rgb >> 8) & 0xFF, (rgb >> 16) & 0xFF))
        return [frames[k] for k in sorted(frames)]
    finally:
        db.close()


def _to_63x5(im, method):
    from PIL import Image
    if method == 'crop':
        return im.crop((0, 1, STRP.COLS, 1 + STRP.ROWS))
    if method == 'box':
        return im.resize((STRP.COLS, STRP.ROWS), Image.BOX)
    return im.crop((0, 0, STRP.COLS, SRC_H)).resize((STRP.COLS, STRP.ROWS), Image.NEAREST)


def preset_images(name):
    """返回 63x5 的 PIL 帧列表 (超过 260 帧时均匀抽帧)"""
    if name not in _cache:
        layer, _, method = PRESETS[name]
        ims = [_to_63x5(im, method) for im in _load_images(layer)]
        if len(ims) > MAX_FRAMES:
            step = len(ims) / MAX_FRAMES
            ims = [ims[int(i * step)] for i in range(MAX_FRAMES)]
        _cache[name] = ims
    return _cache[name]


def preset_frames(name):
    """返回可直接 upload_anim 的帧 (已按 key_pos 重排)"""
    return [STRP.image_to_frame(im) for im in preset_images(name)]
