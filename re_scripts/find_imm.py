import pickle, sys, re
ins=pickle.load(open('/tmp/amg_dis.pkl','rb'))
want=set(int(x,0) for x in sys.argv[1:])
for a,mn,op in ins:
    for m in re.findall(r'0x[0-9a-f]+', op):
        if int(m,16) in want and mn in ('push','mov','cmp'):
            print('%08x %s %s'%(a,mn,op)); break
