import pefile, sys, os
pe=pefile.PE(os.environ.get('AMG65_DRIVER_DIR', 'vendor/app') + '/DeviceDriver.exe', fast_load=True)
b=pe.OPTIONAL_HEADER.ImageBase
for a in sys.argv[1:]:
    raw=pe.get_data(int(a,16)-b, 120)
    w=raw.split(b'\x00\x00')[0]
    try: ws=raw.decode('utf-16le').split('\x00')[0]
    except: ws='?'
    print(a, 'A:',raw.split(b'\x00')[0][:60], ' W:', ws[:60])
