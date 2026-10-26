#!/usr/bin/env python3
"""Probe AMG65 (VID 0x276d PID 0x2234) vendor interface for the config channel."""
import hid, time, sys

VID, PID = 0x276d, 0x2234

def open_vendor():
    paths = [d for d in hid.enumerate(VID, PID) if d['usage_page'] == 0xffb5]
    if not paths:
        print("no ffb5 interface found"); sys.exit(1)
    d = paths[0]
    print("opening", d['path'], "usage", hex(d['usage_page']), hex(d['usage']), "if", d['interface_number'])
    h = hid.device()
    h.open_path(d['path'])
    h.set_nonblocking(False)
    return h

def drain(h, ms=300, label=""):
    t0 = time.time()
    got = []
    while (time.time() - t0) * 1000 < ms:
        r = h.read(64, timeout_ms=50)
        if r:
            got.append(bytes(r))
    for g in got:
        print(f"  {label} recv: {g.hex()}")
    return got

h = open_vendor()
print("vendor opened. manufacturer=", h.get_manufacturer_string(), "product=", h.get_product_string())

# flush pending input
drain(h, 200, "flush")

def ping8():
    # ping command from fcn.00468940: data[0]=0 (cmd cat), data[1]=2, checksum@32=2 — truncated to 7 data bytes
    return bytes([0xB5, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00])

def ping65(rid=0xB5):
    buf = bytearray(65)
    buf[0] = rid
    buf[2] = 2   # [1]=2 if buf[0] is report id; [0]=2 if 65B mode with [0]=0... try both below
    return bytes(buf)

tests = [
    ("8B report B5 + [0,2,0...]", lambda: bytes([0xB5, 0x00, 0x02, 0, 0, 0, 0, 0])),
    ("8B report B5 + [2,0...]",   lambda: bytes([0xB5, 0x02, 0x00, 0, 0, 0, 0, 0])),
    ("65B rid=B5",                lambda: ping65(0xB5)),
    ("65B rid=0",                 lambda: ping65(0x00)),
]
for name, fn in tests:
    data = fn()
    try:
        n = h.write(data)
        print(f"send {name}: write()={n} data[:12]={data[:12].hex()}")
    except Exception as e:
        print(f"send {name}: EXC {e}")
        continue
    got = drain(h, 400, name)
    if not got:
        print(f"  {name}: no response")
print("--- feature report test ---")
try:
    buf = bytearray(64); buf[0] = 0xB5
    data = h.get_feature_report(0xB5, 64)
    print("get_feature_report(0xB5,64):", bytes(data).hex())
except Exception as e:
    print("feature exc:", e)
h.close()
