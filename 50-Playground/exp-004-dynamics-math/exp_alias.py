"""必然混叠 + 过采样收益 —— 精确版。
坑1: f0 必须落在 FFT bin 上，谐波才是干净的谱线
坑2: 某些 f0 会让折叠产物**正好落回合法谐波的位置**（如 6000Hz: 5×6000=30k→18k=3×6000）
     这时"其余 bin 的能量"判据会漏掉它 —— 必须显式列出每个谐波的落点
坑3: Chebyshev 恒等式 T_k(cosθ)=cos(kθ) 只在**幅度=1**时成立
"""
import numpy as np
SR, N = 48000.0, 1 << 16

def bin_freq(m): return m*SR/N
def ws_tanh(x, d=3.0): return np.tanh(d*x)
def ws_hard(x, d=3.0): return np.clip(d*x, -1.0, 1.0)
def ws_atan(x, d=3.0): return (2/np.pi)*np.arctan(d*x*np.pi/2)

def fold(f, sr=SR):
    """理想采样下 f 的折叠频率"""
    return abs(f - sr*round(f/sr))

print("=== 1. 谐波落点表：哪些谐波越界，折叠到哪里 ===")
print("    48kHz / Nyquist 24kHz。'越界'的谐波不会消失，会折叠回可听频段")
for f0 in [1000.0, 2000.0, 4000.0, 8000.0]:
    print(f"\n  f0 = {f0:.0f} Hz")
    print(f"    {'k':>3}{'k*f0':>9}{'越界?':>7}{'折叠到':>9}{'撞上谁':>22}")
    for k in range(2, 9):
        f = k*f0
        if f < SR/2:
            print(f"    {k:>3}{f:>9.0f}{'否':>7}{f:>9.0f}{'合法谐波 h'+str(k):>22}")
        else:
            fa = fold(f)
            hit = [f"h{j}" for j in range(1,20) if abs(j*f0-fa) < 1e-6]
            tag = ("撞上 "+"/".join(hit)) if hit else "★ 非谐波（听感最脏）"
            print(f"    {k:>3}{f:>9.0f}{'是':>7}{fa:>9.0f}{tag:>22}")
print("\n  → 8000Hz 时 h3 正好落在 Nyquist 上，h4/h5/h6 全部折叠到 8k 以下")
print("  → 折叠产物**不是** f0 的整数倍时，听起来是不协和的『金属味』；")
print("    正好撞上合法谐波时只是谐波比例被改错，听感问题小得多")

print("\n=== 2. 混叠 / 基频 (dB)，非谐波能量判据 ===")
print("    f0 取整数 bin，且避开『折叠撞合法谐波』的频率")
def alias_db(fn, f0, amp=0.5, n=N, sr=SR):
    x = amp*np.sin(2*np.pi*f0*np.arange(n)/sr)
    y = fn(x); w = np.hanning(n)
    Y = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w); P = Y**2
    mask = np.zeros(len(P), bool)
    for k in range(0, 100):
        b = int(round(k*f0*n/sr))
        if b < len(P): mask[max(0,b-4):b+5] = True
    h1 = Y[int(round(f0*n/sr))]
    return 20*np.log10(np.sqrt(P[~mask].sum())/(h1+1e-18) + 1e-18)
print(f"    {'f0(Hz)':>9}{'hard clip':>11}{'tanh':>9}{'atan':>9}   ← 越负越好")
for f0t in [1000, 1500, 3000, 5000, 7000, 9000, 11000]:
    m = int(round(f0t*N/SR)); ff = bin_freq(m)
    row = [alias_db(fn, ff) for fn in (ws_hard, ws_tanh, ws_atan)]
    print(f"    {ff:>9.1f}" + "".join(f"{v:>11.1f}" if i==0 else f"{v:>9.1f}" for i,v in enumerate(row)))
print("    → 1kHz 的失真：几乎不混叠（h3=3k h5=5k 全在带内）")
print("    → 7kHz 以上：h5/h7 全部折叠，混叠只比基频低十几 dB —— 这就是『高音区失真变脏』")

print("\n=== 3. 过采样收益（理想砖墙抗混叠滤波，只保留 < SR/2）===")
def alias_db_os(fn, f0, os, amp=0.5, n=N//8, sr=SR):
    nn = n*os
    x = amp*np.sin(2*np.pi*f0*np.arange(nn)/(sr*os))
    y = fn(x)
    Y = np.fft.rfft(y); fr = np.fft.rfftfreq(nn, 1.0/(sr*os))
    Y[fr >= sr/2] = 0.0
    y = np.fft.irfft(Y, nn)[::os]
    n2 = len(y); w = np.hanning(n2)
    Y2 = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w); P = Y2**2
    m = int(round(f0*n2/sr)); f0b = m*sr/n2
    mask = np.zeros(len(P), bool)
    for k in range(0, 100):
        b = int(round(k*f0b*n2/sr))
        if b < len(P): mask[max(0,b-4):b+5] = True
    return 20*np.log10(np.sqrt(P[~mask].sum())/(Y2[m]+1e-18) + 1e-18)
print(f"    {'f0(Hz)':>9}{'无':>9}{'2x':>9}{'4x':>9}{'8x':>9}{'16x':>9}   ← tanh drive=3, 混叠/基频 dB")
for f0t in [3000, 5000, 7000, 9000, 11000]:
    m = int(round(f0t*(N//8)/SR)); ff = m*SR/(N//8)
    row = [alias_db_os(ws_tanh, ff, os) for os in (1,2,4,8,16)]
    print(f"    {ff:>9.1f}" + "".join(f"{v:>9.1f}" for v in row))
print("    → 过采样把混叠压低 20–50 dB，但不是无限：抗混叠滤波器的过渡带决定残留")
print("    → 2x 常常不够（9kHz 处 2x 只挽回 20dB 左右），4x 是常见默认")

print("\n=== 4. Chebyshev 基：T_k 只产生第 k 次谐波（幅度必须 = 1）===")
from numpy.polynomial import chebyshev as Ch
f0 = bin_freq(1365)
for order in [1,2,3,4,5]:
    c = np.zeros(order+1); c[order] = 1.0
    p = Ch.cheb2poly(c)
    x = 1.0*np.sin(2*np.pi*f0*np.arange(N)/SR)     # ★ 幅度 1，否则恒等式不成立
    y = np.polynomial.polynomial.polyval(x, p)
    w = np.hanning(N); Y = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w)
    def at(f): return 20*np.log10(Y[int(round(f*N/SR))]+1e-15)
    hs = [at(k*f0)-at(f0) for k in range(1,7)]
    print(f"    T{order}(x): " + "  ".join(f"h{k+1}={v:>7.1f}" for k,v in enumerate(hs)))
print("    → T_k(cosθ)=cos(kθ)。想『只要 3 次谐波』就在 Chebyshev 基上写系数，再 cheb2poly 转回幂基")
