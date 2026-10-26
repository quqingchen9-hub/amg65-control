import pickle, re, collections, bisect
ins=pickle.load(open('/tmp/amg_dis.pkl','rb'))
rx=re.compile(r'word ptr \[.*\], (0x[0-9a-f]+)$')
hits=collections.defaultdict(list)
for a,mn,op in ins:
    if mn!='mov' or not op.startswith('word'): continue
    m=rx.match(op)
    if not m: continue
    v=int(m.group(1),16)
    if v&0xff in (0x04,0x0c,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b): hits[v].append(a)
for v in sorted(hits, key=lambda v:(v&0xff, v>>8)):
    print('%02X %02X'%(v&0xff, v>>8), len(hits[v]), ' '.join(hex(x) for x in hits[v][:10]))
