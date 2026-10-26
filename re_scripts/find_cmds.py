import pickle, re, collections
ins=pickle.load(open('/tmp/amg_dis.pkl','rb'))
rx=re.compile(r'byte ptr \[(\w+)\s*([+-])\s*(0x[0-9a-f]+|\d+)\], (0x[0-9a-f]+|\d+)$')
def parse(op):
    m=rx.match(op)
    if not m: return None
    d=int(m.group(3),0)*(1 if m.group(2)=='+' else -1)
    return m.group(1), d, int(m.group(4),0)
hits=collections.defaultdict(list)
for k,(a,mn,op) in enumerate(ins):
    if mn!='mov': continue
    p=parse(op)
    if not p or p[2] not in (4,0x0c): continue
    for j in range(k+1,min(k+8,len(ins))):
        q=parse(ins[j][2]) if ins[j][1]=='mov' else None
        if q and q[0]==p[0] and q[1]==p[1]+1:
            hits[(p[2],q[2])].append(hex(a)); break
for key in sorted(hits): print('%02X %02X'%key, len(hits[key]), hits[key][:8])
