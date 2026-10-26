#!/usr/bin/env python3
"""长条屏常驻验证 (先停掉 panel/server.py, 避免抢设备)

  python3 strip_test.py anim  [文字]   04 33 -> 槽 6, 传一次, 应一直显示(拔插后也在)
  python3 strip_test.py live  [秒]     04 35 实时时钟, 每秒补发; 结束后约 2.5 秒自动退出
  python3 strip_test.py once           04 35 只发一帧, 用来量固件超时(数一下几秒消失)
  python3 strip_test.py boot  [文字]   04 31 开机动画(旧方案), 对照用: 应播一次就回去
"""
import sys, time, datetime
import usb.core, usb.util
from amg65 import AMG65
import strip as S


def with_data(kb, fn):
    dev = usb.core.find(idVendor=0x0C45, idProduct=0x800A)
    try:
        dev.set_configuration()
    except Exception:
        pass
    usb.util.claim_interface(dev, 3)
    kb._usb, kb._claimed = dev, True
    try:
        return fn()
    finally:
        usb.util.release_interface(dev, 3)
        kb._usb, kb._claimed = None, False


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'anim'
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    kb = AMG65(verbose=False)
    try:
        if cmd in ('anim', 'boot'):
            f = S.text_frame(arg or 'HELLO', (0, 255, 200))
            up = S.upload_anim if cmd == 'anim' else S.upload_boot
            r = with_data(kb, lambda: up(kb, [f], delay_ms=100,
                                          progress=lambda i, n: print(f'  块 {i}/{n}')))
            print('04 02 应答:', r.hex()[:8] if r else None)
            print('anim: 应该一直显示 HELLO, 按灯效切换键离开后再切回槽 6 也还在' if cmd == 'anim'
                  else 'boot: 播一次后应回到原灯效')
        elif cmd == 'live':
            secs = int(arg or 30)
            t_end = time.time() + secs
            n = 0
            while time.time() < t_end:
                t0 = time.time()
                now = datetime.datetime.now()
                acks = S.live_frame(kb, S.clock_frame(n % 2 == 0, (255, 160, 0)))
                print(f'{now:%H:%M:%S}  ack {acks}/{S.LIVE_PKTS}  {time.time()-t0:.2f}s')
                n += 1
                time.sleep(max(0, 1.0 - (time.time() - t0)))
            print('停止补发 -> 约 2.5 秒后固件退出实时模式(切到槽 7)')
        elif cmd == 'once':
            acks = S.live_frame(kb, S.text_frame('88888', (255, 0, 0)))
            t0 = time.time()
            print(f'ack {acks}/{S.LIVE_PKTS}; 数一下多久消失 (Ctrl+C 结束)')
            while True:
                time.sleep(0.5)
                print(f'  {time.time()-t0:.1f}s', end='\r', flush=True)
        else:
            print(__doc__)
    finally:
        kb.close()


if __name__ == '__main__':
    main()
