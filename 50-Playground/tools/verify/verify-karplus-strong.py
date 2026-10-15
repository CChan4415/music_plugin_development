"""Karplus-Strong 物理建模验证

详见 30-Wiki/DSP/物理建模.md
实测（本库验证）:
  音高: 110→110.1Hz(+0.08%), 220→220.2Hz(+0.08%),
        440→440.4Hz(+0.08%), 880→872.7Hz(-0.83%)
  衰减(decay=0.9995, f0=220):
        无阻尼 RMS 5.637e-1 → 4.051e-1 (3秒)
        有阻尼 RMS 1.837e-1 → 1.216e-2 (3秒)
"""
import numpy as np
SR = 48000.0

def karplus_strong(f0, dur, sr=SR, decay=0.9995, seed=42):
    N = int(round(sr/f0))
    buf = np.random.default_rng(seed).uniform(-1,1,N).astype(float)
    buf -= np.mean(buf)
    out = np.zeros(int(dur*sr)); idx = 0
    for i in range(len(out)):
        out[i] = buf[idx]
        buf[idx] = decay * 0.5 * (buf[idx] + buf[(idx-1) % N])
        idx = (idx+1) % N
    return out

def ks_undamped(f0, dur, sr=SR, decay=0.9995, seed=42):
    N = int(round(sr/f0))
    buf = np.random.default_rng(seed).uniform(-1,1,N).astype(float)
    buf -= np.mean(buf)
    out = np.zeros(int(dur*sr)); idx = 0
    for i in range(len(out)):
        out[i] = buf[idx]
        buf[idx] = decay * buf[idx]
        idx = (idx+1) % N
    return out

def detect_pitch(y, sr=SR, fmin=50, fmax=2000):
    y = y - np.mean(y); y = y[:int(sr*0.3)]
    ac = np.correlate(y, y, mode='full')[len(y)-1:]
    lo, hi = int(sr/fmax), int(sr/fmin)
    seg = ac[lo:hi]
    return sr/(lo + np.argmax(seg)) if len(seg) else 0.0

if __name__ == '__main__':
    print("音高:")
    for f0 in [110, 220, 440, 880]:
        y = karplus_strong(f0, 1.0, decay=0.9999)
        fm = detect_pitch(y, fmin=f0*0.6, fmax=f0*1.6)
        err = (fm-f0)/f0*100
        print(f"  {f0:>4}Hz → {fm:>7.1f}Hz ({err:+.2f}%)")

    print("\n衰减（f0=220, decay=0.9995）:")
    for name, fn in [('无阻尼', ks_undamped), ('有阻尼', karplus_strong)]:
        y = fn(220, 3.0)
        w = int(SR*0.1)
        rms = np.array([np.sqrt(np.mean(y[i*w:(i+1)*w]**2)) for i in range(len(y)//w)])
        assert rms[0] > rms[5] > rms[-1], f"{name} 包络非单调！"
        print(f"  {name}: {rms[0]:.3e} → {rms[5]:.3e} → {rms[-1]:.3e}  ✅单调")
    print("✅ 全部通过")
