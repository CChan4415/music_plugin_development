import numpy as np
SR=48000
def env_h(x):
    n=len(x); X=np.fft.fft(x); h=np.zeros(n); h[0]=1
    h[1:n//2]=2; h[n//2]=1
    return np.abs(np.fft.ifft(X*h))

N=int(SR*1.0); t=np.arange(N)/SR
def tone(f,start,amp=0.3):
    x=np.zeros(N); i0=int(start*SR)
    if i0<N: x[i0:]=amp*np.sin(2*np.pi*f*(t[:N-i0]))
    return x

# 用"滑动 RMS 包络"（长窗平滑掉拍纹波）+ 上升沿计数
def smooth_env(x, ms=25.0):
    w=int(SR*ms/1000)
    k=np.ones(w)/w
    return np.convolve(np.abs(x), k, mode='same')

for label,starts in [("sync",[0,0,0]),("5ms",[0,0.005,0.010]),("20ms",[0,0.02,0.04]),("100ms",[0,0.1,0.2])]:
    x=sum(tone(f,s) for f,s in zip([220,440,660],starts))
    e=smooth_env(x,25.0)
    # 稳态值取最后 200ms 的均值
    steady=np.mean(e[int(0.8*N):])
    print(f"\n=== {label} === steady={steady:.4f}")
    for frac in [0.1,0.3,0.5,0.7,0.9]:
        idx=np.where(e>frac*steady)[0]
        tt=idx[0]/SR if len(idx) else float('nan')
        print(f"   到达 {frac*100:>3.0f}% 稳态的时刻: {tt*1000:>7.2f} ms")
