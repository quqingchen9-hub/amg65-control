import pickle, sys, bisect
ins=pickle.load(open('/tmp/amg_dis.pkl','rb'))
addrs=[i[0] for i in ins]
a=int(sys.argv[1],16); n=int(sys.argv[2]) if len(sys.argv)>2 else 80
k=bisect.bisect_left(addrs,a)
for x in ins[k:k+n]: print('%08x  %-6s %s'%x)
