import sys, numpy as np, rawpy, tifffile
from scipy import ndimage as nd
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from indigo_dng import encode_prophoto, DESCRIPTION
src,out=sys.argv[1],sys.argv[2]
ev,warm,k,omega,tmin=map(float,sys.argv[3:8])
half=len(sys.argv)>8
x=rawpy.imread(src).postprocess(gamma=(1,1),no_auto_bright=True,output_bps=16,use_camera_wb=True,half_size=half,output_color=rawpy.ColorSpace.ProPhoto).astype(np.float32)/65535
x*=2**ev
H=x.shape[0]; s=4; sm=x[::s,::s]; mn=(sm).min(2)
A=sm[mn>=np.percentile(mn,99.5)].mean(0)
d=np.percentile((sm/A).min(2),3,axis=1)
d=np.maximum.accumulate(d[::-1])[::-1]
d=nd.gaussian_filter1d(d,sigma=len(d)*0.03,mode='nearest')
t=np.clip(1-omega*d,tmin,1)
t=np.interp(np.arange(H)/s,np.arange(len(t)),t).astype(np.float32)[:,None,None]
print('A',A,'t range',t.min(),t.max())
x=np.maximum((x-A*(1-t))/t,0)
x*=np.array([1+warm,1+warm*0.3,1-warm*1.2],np.float32)
Y=x.mean(2,keepdims=True)+1e-6; m=np.median(Y); x=x*((m*(Y/m)**k)/Y)
print('clip',(x.max(2)>1).mean())
tifffile.imwrite(out,encode_prophoto(np.clip(x,0,1)),photometric='rgb',compression='zlib',description=DESCRIPTION)
