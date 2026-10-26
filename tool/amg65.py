#!/usr/bin/env python3
"""
LEOBOG AMG65 点阵屏 / 配置工具（macOS 版）
协议逆向自官方 Windows 驱动 LEOBOG AMG65 Driver 1.0.3.3 (DeviceDriver.exe, 索艾方案)

传输层（实测确认）:
  - 命令通道: USB interface 2, HID usage page 0xFF68 / usage 0x61
    64 字节无 report-ID 的输入/输出报告 (hidapi 可直接开关)
    写: [0x00] + 64字节负载 (负载[0]=命令类别, [1]=子命令, [31]=可选校验和)
    读: 64 字节, [0..2]=回显, [3]=状态 (0x01=成功, 0xFF=忙/重试)
  - 数据通道: USB interface 3, HID usage page 0xFF67 / usage 0x61
    4096 字节输出报告 + 64 字节 feature 报告; 中断 OUT 端点 0x06 (64B 包)
    (macOS 不给该接口挂 HID 驱动 —— 它只有 OUT 端点, 所以必须用 libusb)

屏幕: 240x135 RGB565, 最多 130 帧
上传序列: 04 18 (开始) → 04 72 [亮度@2] [块数16@8..9] → n×4096B 块(每块ACK) → 04 02 (提交)
数据缓冲: [0]=帧数, [1..帧数]=每帧延时(max(1,延时ms/2)), 补0到256, 然后每帧 240*135*2 字节 RGB565
"""
import hid
import time

VID, PID = 0x0C45, 0x800A
SCREEN_W, SCREEN_H = 240, 135
FRAME_BYTES = SCREEN_W * SCREEN_H * 2   # 64800
HDR_SIZE = 256
MAX_FRAMES = 130
BLOCK = 4096

CMD_CAT = 0x04
CMD_BEGIN = 0x18
CMD_DATA_HDR = 0x72
CMD_COMMIT = 0x02


class AMG65:
    def __init__(self, verbose=True):
        self.verbose = verbose
        for d in hid.enumerate(VID, PID):
            if d['usage_page'] == 0xFF68 and d['usage'] == 0x61:
                break
        else:
            raise RuntimeError(
                '未找到 AMG65 配置接口 (0x0C45:0x800A usage FF68/61)\n'
                '请用数据线连接键盘（蓝牙模式下没有此通道）')
        self.h = hid.device()
        self.h.open_path(d['path'])
        self.h.set_nonblocking(False)
        self._usb = None
        self._claimed = False

    # ---------- 命令通道 ----------
    def _drain(self, ms=60):
        t0 = time.time()
        out = []
        while (time.time() - t0) * 1000 < ms:
            r = self.h.read(64, timeout_ms=20)
            if r:
                out.append(bytes(r))
        return out

    def cmd(self, payload, timeout_ms=600, retries=3):
        """发送 64 字节负载, 返回应答(64B)或 None"""
        assert len(payload) <= 64
        p = bytes(payload).ljust(64, b'\x00')
        for _ in range(retries):
            if self.h.write(b'\x00' + p) <= 0:
                raise IOError('命令写入失败')
            t0 = time.time()
            while (time.time() - t0) * 1000 < timeout_ms:
                r = self.h.read(64, timeout_ms=40)
                if r:
                    return bytes(r)
        return None

    def ping(self):
        p = bytearray(64)
        p[0] = 0x02
        p[31] = sum(p[0:31]) & 0xFF
        return self.cmd(p)

    def _open_data_channel(self):
        if self._claimed:
            return
        import usb.core, usb.util
        dev = usb.core.find(idVendor=VID, idProduct=PID)
        if dev is None:
            raise RuntimeError('libusb 找不到键盘')
        try:
            dev.set_configuration()
        except Exception:
            pass
        usb.util.claim_interface(dev, 3)
        self._usb = dev
        self._claimed = True

    def close(self):
        try:
            if self._claimed:
                import usb.util
                usb.util.release_interface(self._usb, 3)
                self._claimed = False
        finally:
            self.h.close()

    # ---------- 帧编码 ----------
    def rgb565_frame(self, pixels):
        """pixels: bytes(240*135*3 RGB) 或 callable(x,y)->(r,g,b) — RGB565 小端（实测确认）"""
        out = bytearray(FRAME_BYTES)
        if callable(pixels):
            i = 0
            for y in range(SCREEN_H):
                for x in range(SCREEN_W):
                    r, g, b = pixels(x, y)
                    v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    out[i] = v & 0xFF
                    out[i + 1] = v >> 8
                    i += 2
        else:
            i = 0
            for px in range(SCREEN_W * SCREEN_H):
                r, g, b = pixels[px * 3:px * 3 + 3]
                v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                out[i] = v & 0xFF
                out[i + 1] = v >> 8
                i += 2
        return bytes(out)

    # ---------- 屏幕上传 ----------
    def _send_block(self, blk, ack_timeout=2.0):
        # 块 ACK 格式: 04 41 <键盘内部块计数> 01 —— 计数在会话异常中断后会残留,
        # 因此只匹配 04 41 ?? 01 (同步发送, 写完后的下一个 ACK 就是本块的)
        dev = self._usb
        for j in range(0, BLOCK, 64):
            dev.write(0x06, blk[j:j + 64])
        t0 = time.time()
        while time.time() - t0 < ack_timeout:
            r = self.h.read(64, timeout_ms=80)
            if r:
                r = bytes(r)
                if r[0] == 0x04 and r[1] == 0x41 and r[3] == 0x01:
                    return True
                if self.verbose:
                    print(f'    忽略非ACK包: {r[:8].hex()}')
        return False

    def upload_screen(self, frames, delays_ms=None, brightness=0):
        """frames: list of RGB565 帧(bytes); delays_ms: 每帧毫秒"""
        n = len(frames)
        if not (1 <= n <= MAX_FRAMES):
            raise ValueError(f'帧数须在 1..{MAX_FRAMES} (当前 {n})')
        if delays_ms is None:
            delays_ms = [40] * n
        buf = bytearray(HDR_SIZE + n * FRAME_BYTES)
        buf[0] = n
        for i, d in enumerate(delays_ms):
            buf[1 + i] = max(1, int(d) // 2) & 0xFF
        for i, f in enumerate(frames):
            if len(f) != FRAME_BYTES:
                raise ValueError(f'第{i}帧长度错误 {len(f)} != {FRAME_BYTES}')
            buf[HDR_SIZE + i * FRAME_BYTES:HDR_SIZE + (i + 1) * FRAME_BYTES] = f
        nblocks = (len(buf) + BLOCK - 1) // BLOCK
        padded = bytes(buf).ljust(nblocks * BLOCK, b'\x00')

        try:
            self._open_data_channel()
            self._drain(200)
            r = self.cmd([CMD_CAT, CMD_BEGIN])
            if self.verbose:
                print(f'  开始: {r.hex()[:8] if r else "无应答"}')
            r = self.cmd([CMD_CAT, CMD_DATA_HDR, brightness & 0xFF,
                          0, 0, 0, 0, 0, nblocks & 0xFF, (nblocks >> 8) & 0xFF])
            if self.verbose:
                print(f'  头部({nblocks}块): {r.hex()[:8] if r else "无应答"}')
            t0 = time.time()
            for i in range(nblocks):
                ok = self._send_block(padded[i * BLOCK:(i + 1) * BLOCK])
                if not ok:
                    if not self._send_block(padded[i * BLOCK:(i + 1) * BLOCK]):
                        raise IOError(f'第 {i} 块上传失败')
                if self.verbose and (i % 16 == 15 or i == nblocks - 1):
                    print(f'  块 {i+1}/{nblocks} ({time.time()-t0:.1f}s)')
            r = self.cmd([CMD_CAT, CMD_COMMIT])
            if self.verbose:
                print(f'  提交: {r.hex()[:8] if r else "无应答"}')
            if not r or r[3] != 1:
                raise IOError('提交未确认')
            return True
        finally:
            self._release_data_channel()

    def _release_data_channel(self):
        if self._claimed:
            try:
                import usb.util
                usb.util.dispose_resources(self._usb)
                usb.util.release_interface(self._usb, 3)
            except Exception:
                pass
            self._claimed = False
            self._usb = None
