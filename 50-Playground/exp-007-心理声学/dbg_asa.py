import numpy as np
SR=48000
def onset_strength(x, sr=SR, win_ms=10.0, hop_ms=5.0):
    w=int(sr*win_ms/1000); h=int(sr*hop_ms/1000)
    n=1+(len(x)-w)//h
    e=np.array([np.sum(x[i*h:i*h+w]**2) for i in range(n)])
    d=np.diff(e,prepend=e[0]); return np.arange(n)*h/sr, np.maximum(d,0.0)

N=int(SR*1.0); t=np.arange(N)/SR
def tone(f,start,amp=0.3):
    x=np.zeros(N); i0=int(start*SR); x[i0:]=amp*np.sin(2*np.pi*f*(t[:N-i0])); return x

for label,starts in [("sync",[0,0,0]),("20ms",[0,0.02,0.04]),("100ms",[0,0.1,0.2])]:
    x=sum(tone(f,s) for f,s in zip([220,440,660],starts))
    ot,ov=onset_strength(x)
    print(f"\n=== {label} ===  len(ov)={len(ov)} max={ov.max():.3e}")
    thr=0.2*ov.max()
    print("  frames above 0.2*max:", np.sum(ov>thr), " at times:", np.round(ot[ov>thr][:25],3))
