"""半带滤波器验证

详见 30-Wiki/DSP/半带滤波器.md
实测（96kHz, Kaiser β=6.0, 1<<16 FFT）:
  11 抽头: 阻带 -11.6 dB
  21 抽头: 阻带 -20.3 dB
  31 抽头: 阻带 -34.5 dB
  51 抽头: 阻带 -66.6 dB
  101 抽头: 阻带 -71.2 dB
  所有抽头数下 fs/4 处均为 -6.02 dB（定义性特征）
"""
import numpy as np

def design_halfband(n_taps=31, beta=6.0):
    assert n_taps % 2 == 1
    M = (n_taps-1)//2; n = np.arange(n_taps); off = n - M
    h = np.zeros(n_taps); h[M] = 0.5
    for i in range(n_taps):
        if off[i] == 0 or off[i] % 2 == 0: continue
        h[i] = np.sin(np.pi*off[i]/2) / (np.pi*off[i])
    return h * np.kaiser(n_taps, beta)

def verify_halfband(h, fs=96000.0, nfft=1<<16):
    h = np.asarray(h, float); N = len(h); M = (N-1)//2
    off = np.arange(N) - M
    even = (off % 2 == 0) & (off != 0)
    zeros_ok = bool(np.all(np.abs(h[even]) < 1e-12))
    dc = float(np.sum(h))
    H = np.abs(np.fft.rfft(h, nfft)); f = np.fft.rfftfreq(nfft, 1/fs)
    at_q = H[np.argmin(np.abs(f - fs/4))] / H[0]
    db_q = 20*np.log10(at_q + 1e-20)
    print(f"  一半系数为 0: {'✅' if zeros_ok else '❌'}")
    print(f"  直流增益: {dc:.6f}  {'✅' if abs(dc-1)<0.01 else '❌'}")
    print(f"  fs/4 处: {db_q:.2f} dB  {'✅' if abs(db_q+6.02)<0.1 else '❌'}")
    return zeros_ok and abs(dc-1) < 0.01 and abs(db_q+6.02) < 0.1

if __name__ == '__main__':
    print("31 抽头:"); assert verify_halfband(design_halfband(31))
    print("✅ 全部通过")
    print("\n抽头数 vs 阻带:")
    fs=96000.0; f=np.fft.rfftfreq(1<<16,1/fs)
    for nt in [11,21,31,51,101]:
        H=np.abs(np.fft.rfft(design_halfband(nt),1<<16)); db=20*np.log10(H+1e-20)
        print(f"  {nt:>4} 抽头: {db[f>fs/4*1.2].max():>6.1f} dB")
