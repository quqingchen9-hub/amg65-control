import sqlite3, sys
from PIL import Image
db=sqlite3.connect('/tmp/amg_db/l.db')
def render(table, layer, cols, nframes=8, step=None, scale=8):
    fr=[r[0] for r in db.execute(f'select distinct frameIndex from {table} where layer_id=? order by frameIndex',(layer,))]
    step=step or max(1,len(fr)//nframes)
    pick=fr[::step][:nframes]
    nleds=db.execute(f'select max(led_index)+1 from {table} where layer_id=?',(layer,)).fetchone()[0]
    rows=(nleds+cols-1)//cols
    img=Image.new('RGB',(cols*scale,(rows*scale+4)*len(pick)),(40,40,40))
    for k,f in enumerate(pick):
        for li,rgb in db.execute(f'select led_index,rgb_value from {table} where layer_id=? and frameIndex=?',(layer,f)):
            r,g,b=rgb&0xff,(rgb>>8)&0xff,(rgb>>16)&0xff
            x,y=li%cols,li//cols
            for dx in range(scale-1):
                for dy in range(scale-1):
                    img.putpixel((x*scale+dx,k*(rows*scale+4)+y*scale+dy),(r,g,b))
    return img
table,layer,cols,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
render(table,layer,cols).save(out)
