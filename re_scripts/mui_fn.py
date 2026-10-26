import pefile, capstone, os, sys
pe=pefile.PE(os.environ.get('AMG65_DRIVER_DIR', 'vendor/app') + '/mui.dll')
b=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
exp={e.name.decode():e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
name=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 200
rva=[v for k,v in exp.items() if name in k][0]
code=pe.get_data(rva, n*8)
c=0
for i in md.disasm(code, b+rva):
    print('%08x  %-6s %s'%(i.address,i.mnemonic,i.op_str)); c+=1
    if c>=n or i.mnemonic=='ret': break
