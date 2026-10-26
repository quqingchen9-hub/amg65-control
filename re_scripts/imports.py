import pefile, sys, os
pe=pefile.PE(os.environ.get('AMG65_DRIVER_DIR', 'vendor/app') + '/DeviceDriver.exe')
want=set(int(x,16) for x in sys.argv[1:])
for d in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in d.imports:
        if imp.address in want or not want:
            print(hex(imp.address), d.dll.decode(), (imp.name or b'#%d'%imp.ordinal).decode())
