import pefile, capstone, pickle, sys, os
P=os.environ.get('AMG65_DRIVER_DIR', 'vendor/app') + '/DeviceDriver.exe'
pe=pefile.PE(P, fast_load=True)
base=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
out=[]
for s in pe.sections:
    if s.Characteristics & 0x20000000:
        data=s.get_data(); va=base+s.VirtualAddress
        off=0
        while off<len(data):
            got=False
            for i in md.disasm(data[off:], va+off):
                out.append((i.address,i.mnemonic,i.op_str)); off=i.address-va+i.size; got=True
            if not got: off+=1
pickle.dump(out, open('/tmp/amg_dis.pkl','wb'))
print(len(out), hex(base))
