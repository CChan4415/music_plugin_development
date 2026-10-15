import numpy as np, sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'tools'))
from audio_io import impulse, db, decay_time

SR = 48000
NFFT = 1 << 20

# ---- 两种梳状 ----
def comb_ff(x, D, g):
    """前馈 FIR: y[n] = x[n] + g*x[n-D]"""
    y = np.zeros(len(x)); y[D:] += g*x[:-D]; y += x; return y

def comb_fb(x, D, g):
    """反馈 IIR: y[n] = x[n] + g*y[n-D]"""
    y = np.zeros(len(x)); buf = np.zeros(D); idx = 0
    for n in range(len(x)):
        out = buf[idx]
        buf[idx] = x[n] + g*out
        y[n] = out
        idx = (idx+1) % D
    return y

def Hfb(f, D, g):
    w = 2*np.pi*np.asarray(f)/SR
    return 1.0/np.abs(1 - g*np.exp(-1j*w*D))

def Hff(f, D, g):
    w = 2*np.pi*np.asarray(f)/SR
    return np.abs(1 + g*np.exp(-1j*w*D))

D = 480; g = 0.85
print("="*70); print(f"梳状滤波器 D={D} samples @ {SR}Hz = {D/SR*1000:.3f} ms, g={g}")
print(f"峰值间隔理论 = fs/D = {SR/D:.4f} Hz")
print("="*70)

# 1) 前馈梳状：脉冲响应 + 长 FFT
h = comb_ff(impulse(4096), D, g)
H = np.fft.rfft(h, NFFT); f = np.fft.rfftfreq(NFFT, 1/SR)
mag = np.abs(H)
print("\n[前馈 FIR 梳状] 峰值/谷值（实测 vs 解析）")
print(f"{'频率Hz':>9} {'实测dB':>9} {'解析dB':>9} {'偏差':>9}")
for k in range(0, 6):
    fpk = k*SR/D
    if fpk >= SR/2: break
    i = np.argmin(np.abs(f-fpk))
    print(f"{fpk:>9.2f} {db(mag[i]):>9.4f} {db(Hff(fpk,D,g)):>9.4f} {db(mag[i])-db(Hff(fpk,D,g)):>+9.5f}")
for k in range(0, 6):
    fn = (k+0.5)*SR/D
    if fn >= SR/2: break
    i = np.argmin(np.abs(f-fn))
    print(f"{fn:>9.2f} {db(mag[i]):>9.4f} {db(Hff(fn,D,g)):>9.4f} {db(mag[i])-db(Hff(fn,D,g)):>+9.5f}")
print(f"  峰值增益 1+g = {1+g:.4f} = {db(1+g):.4f} dB ; 谷值 |1-g| = {abs(1-g):.4f} = {db(abs(1-g)):.4f} dB")

# 2) 反馈梳状：直流增益 1/(1-g)
print("\n[反馈 IIR 梳状]")
g2 = 0.85
h2 = comb_fb(impulse(1<<18), D, g2)
dc_meas = h2.sum()
print(f"  直流增益 实测 {dc_meas:.6f} / 解析 1/(1-g) = {1/(1-g2):.6f}  偏差 {dc_meas-1/(1-g2):+.2e}")
H2 = np.fft.rfft(h2, NFFT)
mag2 = np.abs(H2)
print(f"{'频率Hz':>9} {'实测dB':>10} {'解析dB':>10} {'偏差':>10}")
for k in range(0,5):
    fpk = k*SR/D
    i = np.argmin(np.abs(f-fpk)); th = 1/(1-g2)
    print(f"{fpk:>9.2f} {db(mag2[i]):>10.4f} {db(th):>10.4f} {db(mag2[i])-db(th):>+10.5f}")
for k in range(0,5):
    fn = (k+0.5)*SR/D
    i = np.argmin(np.abs(f-fn)); th = 1/(1+g2)
    print(f"{fn:>9.2f} {db(mag2[i]):>10.4f} {db(th):>10.4f} {db(mag2[i])-db(th):>+10.5f}")

# 3) ⚠️ 测量陷阱：FFT 太短
print("\n[测量陷阱] 同一个脉冲响应，不同 FFT 长度下测直流增益:")
for nf in [4096, 8192, 16384, 32768, 65536, 262144]:
    m = np.abs(np.fft.rfft(h2[:nf], nf))[0]
    print(f"   nfft={nf:>7}: |H(0)| = {m:8.4f}   (真值 {1/(1-g2):.4f}, 误差 {m-1/(1-g2):+.4f})")
