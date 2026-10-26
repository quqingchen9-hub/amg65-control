#!/usr/bin/env python3
"""Probe the AMG65 config interface (Sonix 0x0c45:0x800a, usage ff68/61)."""
import hid, time, sys

VID, PID = 0x0c45, 0x800a

devs = hid.enumerate(VID, PID)
for d in devs:
    print('iface:', hex(d['usage_page']), hex(d['usage']), 'path', d['path'])

def open_target():
    for d in devs:
        if d['usage_page'] == 0xff68 and d['usage'] == 0x61:
            h = hid.device(); h.open_path(d['path']); h.set_nonblocking(False)
            return h, d
    print('target not found'); sys.exit(1)

h, info = open_target()
print('opened:', h.get_manufacturer_string(), '/', h.get_product_string())
print('serial:', h.get_serial_number_string())

def drain(ms=300, label=''):
    t0 = time.time(); got = []
    while (time.time()-t0)*1000 < ms:
        r = h.read(512, timeout_ms=30)
        if r: got.append(bytes(r))
    for g in got: print(f'  {label} recv {len(g)}B: {g[:80].hex()}')
    return got

drain(200, 'flush')

# --- test 1: ping command, 65-byte payload with report ID 0 prefix
def send(name, buf):
    try:
        n = h.write(bytes(buf))
        print(f'send {name}: write={n} {bytes(buf)[:16].hex()}')
    except Exception as e:
        print(f'send {name}: EXC {e}')
        return False
    got = drain(400, name)
    if not got: print(f'  {name}: no response')
    return got

# ping from fcn.00468940: payload[0]=0,[1]=2, checksum(payload[0..35])@32 = 2
p65 = bytearray(65)
p65[1] = 2
p65[32] = 2
send('65B rid=0 ping', [0] + p65)          # buf[0]=0 → hidapi strips → raw 65B write
send('66B rid=0 ping', [0] + p65)          # same
b = bytearray(p65); 
send('65B no-prefix', p65)                  # buf[0]=0x00 → also stripped? p65[0]=0 → same
p65b = bytearray(65); p65b[0] = 0xB5
send('65B rid=B5 ping', p65b)
h.close()
