"""把 ledlayer_v2.data 里 70x7 的默认灯效转成 AMG65 的 63x5 帧"""
import sqlite3
from PIL import Image
LAYERS={'christmas':2,'aurora':3,'game':4,'rainbow':5,'tetris':6}
def load_frames(db_path, layer):
    db=sqlite3.connect(db_path)
    frames={}
    for f,li,rgb in db.execute('select frameIndex,led_index,rgb_value from t_default_led_frames where layer_id=? order by frameIndex',(layer,)):
        im=frames.get(f)
        if im is None: im=frames[f]=Image.new('RGB',(70,7))
        im.putpixel((li%70,li//70),(rgb&0xff,(rgb>>8)&0xff,(rgb>>16)&0xff))
    return [frames[k] for k in sorted(frames)]
def to_63x5(im, method):
    if method=='crop': return im.crop((0,1,63,6))
    if method=='box': return im.resize((63,5),Image.BOX)
    if method=='pick': return im.crop((0,0,63,7)).resize((63,5),Image.NEAREST)
