"""抗混叠振荡器验证 —— 混叠能量测量

详见 30-Wiki/DSP/抗混叠振荡器.md
实测（48kHz, f0=2000Hz, 16384 点）:
  朴素锯齿   -17.6 dB
  PolyBLEP   -67.3 dB  (改善 49.7 dB)
  4x 过采样  -32.4 dB  (改善 14.9 dB)
"""
import numpy as np
SR = 48000

def alias_to_harmonic_db(x, f0, sr=SR, tol_hz=30.0):
    w = np.hanning(len(x)); X = np.abs(np.fft.rfft(x*w))**2
    fr = np.fft.rfftfreq(len(x), 1/sr)
    harm = np.zeros(len(fr), bool); k = 1
    while k*f0 < sr/2:
        harm |= np.abs(fr - k*f0) < tol_hz; k += 1
    total = np.sum(X); h = np.sum(X[harm])
    return 10*np.log10((total-h)/(h+1e-30))

def saw_naive(f0, n, sr=SR):
    ph = (np.arange(n)*f0/sr) % 1.0; return 2*ph-1

def polyblep(t, dt):
    if t < dt: t /= dt; return t+t-t*t-1.0
    if t > 1.0-dt: t = (t-1.0)/dt; return t*t+t+t+1.0
    return 0.0

def saw_polyblep(f0, n, sr=SR):
    dt = f0/sr; out = np.zeros(n); ph = 0.0
    for i in range(n):
        v = 2*ph-1; v -= polyblep(ph, dt); ph += dt
        if ph >= 1.0: ph -= 1.0
        out[i] = v
    return out

def saw_oversampled(f0, n, sr=SR, os=4):
    nn = n*os
    ph = (np.arange(nn)*f0/(sr*os)) % 1.0
    x = 2*ph-1
    X = np.fft.rfft(x); X[int(len(X)/os):] = 0
    return np.fft.irfft(X, nn)[::os]

if __name__ == '__main__':
    f0, N = 2000.0, 16384
    base = alias_to_harmonic_db(saw_naive(f0, N), f0)
    blep = alias_to_harmonic_db(saw_polyblep(f0, N), f0)
    ovs  = alias_to_harmonic_db(saw_oversampled(f0, N), f0)
    print(f"  朴素锯齿      {base:>7.1f} dB")
    print(f"  PolyBLEP      {blep:>7.1f} dB  ({blep-base:+.1f})")
    print(f"  4x 过采样     {ovs:>7.1f} dB  ({ovs-base:+.1f})")
    assert blep < base - 20, "PolyBLEP 未生效（检查修正符号）"
    print("  ✅ PolyBLEP 生效")
