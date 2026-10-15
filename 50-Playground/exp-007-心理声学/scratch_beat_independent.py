import numpy as np
SR=48000
# 独立方法：直接对**包络**做 FFT，看主频是 Δf 还是 2Δf
# 方法 A: 时域相乘得到精确包络（不用 Hilbert，避免任何实现争议）
#   sin(a)+sin(b) = 2 sin((a+b)/2) cos((a-b)/2)
for f1, df in [(40.0,1.0),(1000.0,8.0),(1000.0,1.0),(1000.0,32.0)]:
    N = SR*8
    f1b = round(f1*N/SR)*SR/N
    f2b = round((f1+df)*N/SR)*SR/N
    t = np.arange(N)/SR
    x = 0.5*np.sin(2*np.pi*f1b*t) + 0.5*np.sin(2*np.pi*f2b*t)
    # 解析包络（闭式，无实现误差）
    env = np.abs(2*0.5*np.cos(np.pi*(f2b-f1b)*t))
    # 对包络做 FFT 找主频
    w = np.hanning(N)
    E = np.abs(np.fft.rfft((env-env.mean())*w))*2/np.sum(w)
    fr = np.fft.rfftfreq(N,1/SR)
    m = fr>0.02
    fpk = fr[m][np.argmax(E[m])]
    # 峰计数（严格局部极大 + 相对阈值）
    thr = env.max()*0.5
    pk = np.sum((env[1:-1]>env[:-2])&(env[1:-1]>=env[2:])&(env[1:-1]>thr))
    dur = N/SR
    print(f"Δf={f2b-f1b:>7.4f} Hz | 包络FFT主频={fpk:>8.4f} Hz | "
          f"峰数/时长={pk/dur:>8.4f} 峰/秒 | Δf={f2b-f1b:.4f} 2Δf={2*(f2b-f1b):.4f}")
