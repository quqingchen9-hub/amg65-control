import pickle
ins=pickle.load(open('/tmp/amg_dis.pkl','rb'))
for k,(a,mn,op) in enumerate(ins):
    if 'call' in mn and '0x586a40' in op:
        for j in range(k-1,max(k-4,0),-1):
            if '0x52' in ins[j][2] and 'ecx' in ins[j][2]:
                print('%08x %s   <- %08x'%(a, ins[j][2], ins[j][0])); break
