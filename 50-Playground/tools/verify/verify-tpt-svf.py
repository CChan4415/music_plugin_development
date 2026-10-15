"""TPT/ZDF SVF 验证

详见 30-Wiki/DSP/虚拟模拟滤波器.md
与 Chamberlin 的对比见 30-Wiki/DSP/状态变量滤波器 SVF.md

实测（48kHz，1<<15 点 FFT）:
  目标 200Hz  → 实测 200.7Hz  (+0.34%)
  目标 1000Hz → 实测 999.0Hz  (-0.10%)
  目标 5000Hz → 实测 4995.1Hz (-0.10%)
  Q=100 时 10 秒后残余 1.871e-110（稳定）
  三输出重构误差 1.110e-16

对比：Chamberlin 用 f=2sin(πfc/fs) 时 Q=0.707 误差 -29.6%
"""
import numpy as np
SR = 48000.0

def tpt_svf(x, fc, Q, sr=SR):
    g = np.tan(np.pi*fc/sr); k = 1.0/Q
    a1 = 1.0/(1.0 + g*(g+k)); a2 = g*a1; a3 = g*a2
    s1 = s2 = 0.0
    lp = np.zeros(len(x)); bp = np.zeros(len(x)); hp = np.zeros(len(x))
    for i, v in enumerate(x):
        v3 = v - s2
        v1 = a1*s1 + a2*v3
        v2 = s2 + a2*s1 + a3*v3
        s1 = 2*v1 - s1
        s2 = 2*v2 - s2
        lp[i], bp[i], hp[i] = v2, v1, v - k*v1 - v2
    return lp, bp, hp

if __name__ == '__main__':
    N = 1 << 15
    print("调谐精度:")
    for fc in [200, 1000, 5000]:
        x = np.zeros(N); x[0] = 1.0
        lp, _, _ = tpt_svf(x, fc, 0.707)
        H = np.abs(np.fft.rfft(lp)); f = np.fft.rfftfreq(N, 1/SR)
        db = 20*np.log10(H + 1e-20)
        i3 = np.argmax(db < db[0] - 3)
        print(f"  {fc:>5}Hz → {f[i3]:>8.1f}Hz  ({(f[i3]-fc)/fc*100:+.2f}%)")
        assert abs((f[i3]-fc)/fc*100) < 2.0

    x = np.zeros(int(SR*10)); x[0] = 1.0
    lp, _, _ = tpt_svf(x, 1000.0, 100.0)
    tail = np.max(np.abs(lp[int(SR*8):]))
    print(f"Q=100 稳定性: 残余 {tail:.3e}  {'✅' if tail < 1e-6 else '❌'}")
    assert tail < 1e-6

    x = np.sin(2*np.pi*1000*np.arange(N)/SR)
    lp, bp, hp = tpt_svf(x, 2000.0, 0.707)
    err = np.max(np.abs((lp + hp + (1/0.707)*bp)[1000:] - x[1000:]))
    print(f"三输出重构: {err:.3e}  {'✅' if err < 1e-8 else '❌'}")
    assert err < 1e-8
    print("✅ 全部通过")
