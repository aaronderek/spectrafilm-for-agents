import sys, numpy as np
from PIL import Image
im=Image.open(sys.argv[1]); icc=im.info.get('icc_profile')
a=np.asarray(im).astype(np.float32)/255
L=(a@np.array([.2126,.7152,.0722],np.float32))[...,None]
sh=np.clip(1-L/0.5,0,1)**1.5; hi=np.clip((L-0.45)/0.55,0,1)**1.2
a=a+sh*np.array([-0.045,0.01,0.035],np.float32)+hi*np.array([0.045,0.012,-0.04],np.float32)
L2=(a@np.array([.2126,.7152,.0722],np.float32))[...,None]
a=L2+(a-L2)*1.12
a=np.clip(a,0,1)
Image.fromarray((a*255+0.5).astype(np.uint8)).save(sys.argv[2],quality=92,icc_profile=icc)
