#!/usr/bin/env python3
"""LEOBOG AMG65 长条点阵屏 (63x5 = 315 LED) 渲染与上传

全部参数由 DeviceDriver.exe 机器码确认:
  - 63 列 x 5 行 = 315 灯        (0x457010: SetLEDCount(63, 5); [0x52b24]=0x13b)
  - 每灯 3 字节, 帧长 945 字节    (0x43472c lea ecx,[esi+edx*2] + 0x43476b [edx+ecx+4] => base+edx*3+4)
  - 数据须按 key_pos 重排        (0x43466e 取 key_pos 表; 0x4346eb 写) data[key_pos[led]] = color[led]
  - 常驻: 04 33 -> 灯效槽 6, 固件无限循环 (旧代码用的 04 31 是"开机动画", 只播一次)
  - 实时: 04 35 -> 直接写显存, 约 2.5 秒后自动退出, 每秒补发即可
  - 04 F0 = 保存设置到 flash (固件 0xdd6a), 不是"渲染"命令
  详见文件后半部分的协议注释
"""
import json
import os
import sys
import time
import datetime

COLS, ROWS = 63, 5
N_LEDS = COLS * ROWS          # 315
FRAME_LEN = N_LEDS * 3        # 945 字节/帧

_here = os.path.dirname(os.path.abspath(__file__))
_key_pos_path = os.environ.get('AMG65_KEY_POS') or os.path.join(_here, 'key_pos.json')
if not os.path.exists(_key_pos_path):
    # PyInstaller's one-dir layout keeps datas under _internal; the module may
    # still be imported from the outer archive.
    _key_pos_path = os.path.join(
        getattr(sys, '_MEIPASS', _here), 'tool', 'key_pos.json')
with open(_key_pos_path) as f:
    KEY_POS = json.load(f)     # 315 项排列: 逻辑灯序 -> 硬件灯位

FONT3x5 = {
 '0': ["###","#.#","#.#","#.#","###"], '1': [".#.","##.",".#.",".#.","###"],
 '2': ["###","..#","###","#..","###"], '3': ["###","..#","##.","..#","###"],
 '4': ["#.#","#.#","###","..#","..#"], '5': ["###","#..","###","..#","###"],
 '6': ["###","#..","###","#.#","###"], '7': ["###","..#","..#",".#.","..#"],
 '8': ["###","#.#","###","#.#","###"], '9': ["###","#.#","###","..#","###"],
 ':': ["...",".#.","...",".#.","..."], ' ': ["..."]*5,
 '-': ["...","...","###","...","..."], '.': ["...","...","...","...",".#."],
 'A': ["###","#.#","###","#.#","#.#"], 'B': ["##.","#.#","##.","#.#","##."],
 'C': ["###","#..","#..","#..","###"], 'D': ["##.","#.#","#.#","#.#","##."],
 'E': ["###","#..","##.","#..","###"], 'F': ["###","#..","##.","#..","#.."],
 'G': ["###","#..","#.#","#.#","###"], 'H': ["#.#","#.#","###","#.#","#.#"],
 'I': ["###",".#.",".#.",".#.","###"], 'J': ["..#","..#","..#","#.#","###"],
 'K': ["#.#","#.#","##.","#.#","#.#"], 'L': ["#..","#..","#..","#..","###"],
 'M': ["#.#","###","###","#.#","#.#"], 'N': ["#.#","###","###","###","#.#"],
 'O': ["###","#.#","#.#","#.#","###"], 'P': ["###","#.#","###","#..","#.."],
 'Q': ["###","#.#","#.#","###","..#"], 'R': ["###","#.#","##.","#.#","#.#"],
 'S': ["###","#..","###","..#","###"], 'T': ["###",".#.",".#.",".#.",".#."],
 'U': ["#.#","#.#","#.#","#.#","###"], 'V': ["#.#","#.#","#.#","#.#",".#."],
 'W': ["#.#","#.#","###","###","#.#"], 'X': ["#.#","#.#",".#.","#.#","#.#"],
 'Y': ["#.#","#.#",".#.",".#.",".#."], 'Z': ["###","..#",".#.","#..","###"],
 '!': [".#.",".#.",".#.","...",".#."], '%': ["#.#","..#",".#.","#..","#.#"],
 '#': ["#.#","###","#.#","###","#.#"], '?': ["###","..#",".##","...",".#."],
}
SCALE = 2   # 横向放大 2 倍 → 每字 6 列宽, 5 字 = 34 列


def _blank():
    return bytearray(N_LEDS * 3)


def _set(buf, r, c, rgb):
    """逻辑坐标写入 (行优先: led = r*COLS + c); 重排在 _finish 做"""
    if not (0 <= r < ROWS and 0 <= c < COLS):
        return
    pos = r * COLS + c
    if pos * 3 + 3 <= len(buf):
        buf[pos*3:pos*3+3] = bytes(rgb)


def _finish(buf):
    """逻辑灯序 -> 硬件灯位: out[key_pos[led]] = buf[led]"""
    out = bytearray(FRAME_LEN)
    for led in range(N_LEDS):
        p = KEY_POS[led]
        out[p*3:p*3+3] = buf[led*3:led*3+3]
    return bytes(out)

def text_frame(text, color=(0,255,200), bg=(0,0,0)):
    """63x5, 3x5 字体横向放大 2 倍"""
    chars = [FONT3x5.get(c.upper(), FONT3x5[' ']) for c in text]
    cw = 3 * SCALE
    total = len(chars) * cw + max(0, len(chars) - 1)
    buf = _blank()
    x = max(0, (COLS - total) // 2)
    for g in chars:
        for ry in range(5):
            for rx in range(3):
                if g[ry][rx] == '#':
                    for dx in range(SCALE):
                        _set(buf, ry, x + rx*SCALE + dx, color)
        x += cw + 1
    return _finish(buf)

def clock_frame(colon_on=True, color=(0,255,200)):
    import datetime
    n = datetime.datetime.now()
    return text_frame(f"{n.hour:02d}{':' if colon_on else ' '}{n.minute:02d}", color)


def hsv_to_rgb(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)




def bars_frame(values, color=(80, 255, 120), bg=(15, 0, 30)):
    """values: ≤63 个 0..1 → 柱状图"""
    buf = _blank()
    for c in range(COLS):
        v = values[c] if c < len(values) else 0.0
        v = max(0.0, min(1.0, float(v)))
        lit_rows = int(round(v * ROWS))
        for ry in range(ROWS):
            _set(buf, ROWS - 1 - ry, c, color if ry < lit_rows else bg)
    return _finish(buf)


def rainbow_frame(t):
    buf = _blank()
    for r in range(ROWS):
        for c in range(COLS):
            _set(buf, r, c, hsv_to_rgb((c + t) / COLS, 1.0, 1.0))
    return _finish(buf)


def sit_remind_frame(phase, color=(255, 30, 60), alt=(0, 0, 0)):
    """久坐提醒: 9 颗心 (mui.dll UpdateSitRemindLayer 0x1005e320 还原)
    心中心列 c = 6, 12 .. 54; 轮廓常亮, 心内部按 (第几颗 & 1) == phase 在 color/alt 间交替,
    驱动每 500 ms 翻转一次 phase。"""
    outline = [(0, -2), (0, 0), (1, -3), (1, -1), (1, 1), (2, -3), (2, 1), (3, -2), (3, 0), (4, -1)]
    inner = [(1, -2), (1, 0), (2, -2), (2, -1), (2, 0), (3, -1)]
    buf = _blank()
    for k, c in enumerate(range(6, 60, 6)):
        for r, dc in outline:
            _set(buf, r, c + dc, color)
        fill = color if (k & 1) == phase else alt
        for r, dc in inner:
            _set(buf, r, c + dc, fill)
    return _finish(buf)


AGENT_COLORS = {'working': (255, 170, 0), 'waiting': (255, 20, 20), 'done': (0, 220, 60)}


def agent_frame(states, tick):
    """编程状态红绿黄灯: states = [('CC', state), ('CX', state)], 每块 31 列
    state: idle / working(黄, 流水) / waiting(红, 闪) / done(绿, 常亮); tick 约每 0.25 s +1"""
    buf = _blank()
    for k, (label, state) in enumerate(states):
        x0 = k * 32
        lab = (200, 200, 200) if state != 'idle' else (50, 50, 50)
        x = x0
        for ch in label:
            g = FONT3x5.get(ch, FONT3x5[' '])
            for ry in range(5):
                for rx in range(3):
                    if g[ry][rx] == '#':
                        _set(buf, ry, x + rx, lab)
            x += 4
        lx0, lx1 = x0 + 9, x0 + 31          # 灯区 22 列
        w = lx1 - lx0
        color = AGENT_COLORS.get(state)
        for c in range(lx0, lx1):
            for r in range(ROWS):
                if state == 'idle':
                    rgb = (12, 12, 12) if r in (0, ROWS - 1) or c in (lx0, lx1 - 1) else (0, 0, 0)
                elif state == 'working':
                    span = 2 * (w - 4)
                    p = tick % span
                    head = p if p < w - 4 else span - p   # 来回扫
                    d = c - lx0 - head
                    f = 1.0 if 0 <= d < 4 else 0.12
                    rgb = tuple(int(v * f) for v in color)
                elif state == 'waiting':
                    on = (tick // 2) % 2 == 0           # 约 1 Hz 闪烁
                    rgb = color if on else tuple(v // 10 for v in color)
                else:
                    rgb = color
                _set(buf, r, c, rgb)
    return _finish(buf)


def image_to_frame(pil_image):
    """PIL Image → 63x5 内容, 补足到 490 灯帧长"""
    im = pil_image.convert('RGB').resize((COLS, ROWS))
    buf = _blank()
    px = im.load()
    for r in range(ROWS):
        for c in range(COLS):
            _set(buf, r, c, px[c, r])
    return _finish(buf)


# ======================================================================
#  上传协议 —— 依据固件 V1.31 (r4000.bin, SN32F290) 反汇编确认
# ----------------------------------------------------------------------
#  固件 04 命令分发: 0x4898.   长条屏有 8 个灯效槽 (0x20000196 = 0..7),
#  每个槽都是 SPI flash 里的一段循环动画, 起始地址:
#      槽6 = 0xFC0000  <-- 04 33 "动画" 上传的就是这里, 播放时无限循环
#      开机动画 = 0xEB0000 <-- 04 31 上传到这里, 只播一次, 播完回到当前槽
#  旧代码用的是 04 31, 所以"播完回默认"—— 不是固件限制, 是选错了通道。
#
#  04 33 数据块收完后固件自动: 灯效槽=6, 立即开始循环播放 (0x445e..0x447e)
#  04 F0 = 把当前设置(含槽号)存进 flash (0xdd6a), 断电后仍是槽 6
#
#  04 35 = 实时帧 (官方"屏幕取色/编辑预览"用): 走命令通道,
#      写进 LED 显存并暂停灯效渲染 (0x2000029d=1), 保持约 50 个慢节拍
#      (约 2.5 秒) 后自动退出 —— 所以要每 ~1 秒补发一次, 内容不变就不会闪。
# ======================================================================

ANIM_MAX_FRAMES = 260        # 驱动 0x434a4a: mov eax,0x104
BOOT_MAX_FRAMES = 200        # 驱动 0x4344e8: mov eax,0xc8


def _speed_field(delay_ms):
    """帧头[2..3]。固件 0x6b6c: period = (v*5) & 0xFF 个节拍 —— v>51 会回绕。
    节拍按 1ms 估算(未实测), 所以 v = ms/5, 上限 51 (≈255ms)。"""
    return max(1, min(51, int(round(delay_ms / 5.0))))


def _expand_delay(frames, delay_ms):
    """单帧最多约 255ms; 更长的延时用重复帧实现"""
    rep = max(1, -(-int(delay_ms) // 255))
    out = [f for f in frames for _ in range(rep)]
    return out, delay_ms / rep


def pack_frames(frames_rgb888, delay_ms=80):
    """动画数据: [帧数 u16][速度 u16][帧0 945B][帧1]...[1 字节空][AA 55]
    (驱动 0x4347b0: AA55 写在 4+945n+1, 比数据末尾多空一个字节)"""
    n = len(frames_rgb888)
    v = _speed_field(delay_ms)
    out = bytearray([n & 0xFF, n >> 8, v & 0xFF, v >> 8])
    for f in frames_rgb888:
        assert len(f) == FRAME_LEN, f'帧大小 {len(f)} != {FRAME_LEN}'
        out += f
    out += b'\x00\xAA\x55'
    return bytes(out)


def _upload_blocks(kb, sub, frames_rgb888, delay_ms, max_frames, progress=None, save=True):
    """04 18 -> 04 <sub>(块数@D[8..9]) -> n x 4096B(数据通道) -> 04 02 -> [04 F0]"""
    frames, d = _expand_delay(list(frames_rgb888), delay_ms)
    if len(frames) > max_frames:
        raise ValueError(f'帧数 {len(frames)} 超过上限 {max_frames}')
    data = pack_frames(frames, d)
    nblocks = max(1, (4 + FRAME_LEN * len(frames) + 4095) // 4096)   # 驱动 0x4344f2: ceil((945n+4)/4096)
    padded = data.ljust(nblocks * 4096, b'\x00')[:nblocks * 4096]
    kb._drain(80)
    kb.cmd([0x04, 0x18], timeout_ms=400, retries=1)
    kb.cmd([0x04, sub, 0, 0, 0, 0, 0, 0, nblocks & 0xFF, nblocks >> 8],
           timeout_ms=400, retries=1)
    time.sleep(0.03)
    kb._drain(40)
    for i in range(nblocks):
        blk = padded[i * 4096:(i + 1) * 4096]
        if not kb._send_block(blk):
            raise IOError(f'第 {i} 块无 ACK')
        if progress:
            progress(i + 1, nblocks)
    r = kb.cmd([0x04, 0x02], timeout_ms=600, retries=1)
    if save:
        kb.cmd([0x04, 0xF0], timeout_ms=600, retries=1)
    return r


def upload_anim(kb, frames_rgb888, delay_ms=100, progress=None, save=True):
    """★ 常驻方案: 04 33 写入灯效槽 6, 固件自动切到槽 6 并无限循环。
    存 flash —— 断电保留, 不要高频调用(每次都擦写 flash)。静态图传 1 帧即可。"""
    return _upload_blocks(kb, 0x33, frames_rgb888, delay_ms, ANIM_MAX_FRAMES, progress, save)


def upload_boot(kb, frames_rgb888, delay_ms=100, progress=None):
    """04 31 开机动画: 播一次就回到当前灯效(旧代码一直在用的就是这个)"""
    return _upload_blocks(kb, 0x31, frames_rgb888, delay_ms, BOOT_MAX_FRAMES, progress, True)


upload_led = upload_boot   # 兼容旧名字


LIVE_PKTS = (3 * N_LEDS + 63) // 64     # 15, 驱动 0x434f44 的算法


def live_frame(kb, frame_rgb888):
    """04 35 实时帧 (驱动 fcn.00434ed0 / 固件 0x4c56 + 0x424e)。
    走命令通道, 无需 libusb 数据通道; 不发 04 F0, 不写 flash。
    04 18 -> 04 35(D[8]=15) -> 15 x 64B -> 04 02
    固件收满 15 包后把前 945 字节写进显存, 并保持约 2.5 秒 —— 调用方每秒补发即可常驻。"""
    assert len(frame_rgb888) == FRAME_LEN
    buf = bytearray(LIVE_PKTS * 64)
    buf[:FRAME_LEN] = frame_rgb888
    buf[FRAME_LEN + 1] = 0xAA          # 与驱动一致 (固件不校验)
    buf[FRAME_LEN + 2] = 0x55
    kb._drain(20)
    kb.cmd([0x04, 0x18], timeout_ms=300, retries=1)
    hdr = [0x04, 0x35, 0, 0, 0, 0, 0, 0, LIVE_PKTS, 0]
    r = kb.cmd(hdr, timeout_ms=300, retries=1)
    if not r or r[1] != 0x35 or r[3] != 0x01:
        # 头没被接受时绝不能发数据包: 首字节若恰好是 0x04 会被当成命令执行
        raise IOError(f'04 35 头未确认: {r.hex()[:8] if r else "无应答"}')
    acks = 0
    for i in range(LIVE_PKTS):
        # 每包固件回 04 41 .. 01; retries=1 —— 重发会被当成下一包, 打乱计数
        r = kb.cmd(buf[i * 64:(i + 1) * 64], timeout_ms=300, retries=1)
        if r:
            acks += 1
    kb.cmd([0x04, 0x02], timeout_ms=300, retries=1)
    return acks


# 旧接口名
def upload_static(kb, frame_rgb888, chunks_ack_wait=None):
    return live_frame(kb, frame_rgb888), LIVE_PKTS
