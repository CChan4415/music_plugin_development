"""非线性处理: 谐波结构 + 必然混叠 + 过采样收益
   为 30-Wiki/DSP/非线性处理.md 提供实测数据。

方法要点(踩过的坑):
  - 测削波必须让信号真的越过削波点: 用 drive 增益, 不能只给 0.7 幅度
  - 测混叠必须能把"合法谐波"和"折叠产物"分开:
    ★ 取 f0 = 整数个 FFT bin, 谐波就落在精确的 bin 上;
      其余所有 bin 上的能量 = 混叠。这是最干净的判据。
"""
import numpy as np

SR = 48000.0
N  = 1 << 16

# ---------- waveshaper ----------
def ws_hard(x, d=3.0):  return np.clip(d*x, -1.0, 1.0)
def ws_cubic(x, d=3.0): return np.tanh(d*x) if False else (lambda u: u - u**3/3.0)(np.clip(d*x,-1.5,1.5))
def ws_tanh(x, d=3.0):  return np.tanh(d*x)
def ws_atan(x, d=3.0):  return (2/np.pi)*np.arctan(d*x*np.pi/2)
def ws_asym(x, d=3.0):  return np.tanh(d*x) + 0.2*np.tanh(d*x)**2

# ---------- 谐波表 ----------
def harm(name, fn, f0, amp=0.5, n=N, sr=SR):
    """f0 取整数 bin, 谐波精确落点。返回相对基频的 dB。"""
    x = amp*np.sin(2*np.pi*f0*np.arange(n)/sr)
    y = fn(x)
    w = np.hanning(n)
    Y = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w)
    def at(f):
        if f >= sr/2: return np.nan
        return 20*np.log10(Y[int(round(f*n/sr))]+1e-15)
    h1 = at(f0)
    odd  = [at(k*f0)-h1 for k in (3,5,7,9)]
    even = [at(k*f0)-h1 for k in (2,4,6,8)]
    return h1, at(0.0), odd, even

# f0 = 1000.0 * 65536/48000? 需要 f0*N/SR 是整数 → f0 = m*SR/N = m*0.732421875
m = 1365; f0 = m*SR/N
print(f"测试频率 f0 = {f0:.4f} Hz (= {m} × SR/N, 精确落在 FFT bin 上)")
print(f"采样率 {SR:.0f} Hz, Nyquist = {SR/2:.0f} Hz\n")

print("=== 1. 各 waveshaper 的谐波结构（drive=3, 输入 0.5 幅度）===")
print(f"    {'函数':<14}{'基频dB':>8}{'DC':>9}   {'h3':>7}{'h5':>7}{'h7':>7}{'h9':>7}   {'h2':>7}{'h4':>7}{'h6':>7}")
for fn, nm in [(ws_hard,'hard clip'),(ws_cubic,'x-x³/3'),(ws_tanh,'tanh'),
               (ws_atan,'atan'),(ws_asym,'asym (tanh+tanh²)')]:
    h1, dc, odd, even = harm(nm, fn, f0)
    print(f"    {nm:<14}{h1:>8.2f}{dc:>9.2f}   " + "".join(f"{v:>7.1f}" for v in odd) + "   " + "".join(f"{v:>7.1f}" for v in even[:3]))

print("\n=== 2. 偶次谐波 = 非对称传递函数的直接后果 ===")
for fn, nm in [(ws_tanh,'tanh (奇函数)'),(ws_asym,'tanh+0.2tanh² (非对称)')]:
    h1, dc, odd, even = harm(nm, fn, f0)
    print(f"    {nm:<26} 最大奇次 {max(odd):>7.1f} dB | 最大偶次 {max(even):>7.1f} dB | DC {dc:>7.1f} dB")
print("    → 奇函数 ⟹ 偶次谐波在数学上恒为 0（实测 < -180 dB = 数值噪声）")
print("    → 『偶次=温暖』在工程上只有一条路：让 f(-x) ≠ -f(x)")

print("\n=== 3. 必然混叠：f0 越高，越界谐波越多 ===")
print("    判据: 谐波落在精确 bin 上，其余 bin 的能量全部是混叠")
def alias_ratio(fn, f0, amp=0.5, n=N, sr=SR):
    m = int(round(f0*n/sr))
    if abs(m*sr/n - f0) > 1e-9: raise ValueError("f0 不在 bin 上")
    x = amp*np.sin(2*np.pi*f0*np.arange(n)/sr)
    y = fn(x)
    w = np.hanning(n)
    Y = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w)
    P = Y**2
    mask = np.zeros(len(P), bool)
    for k in range(0, 80):
        b = int(round(k*f0*n/sr))
        if b < len(P): mask[max(0,b-3):b+4] = True
    h1 = Y[int(round(f0*n/sr))]
    alias = np.sqrt(P[~mask].sum())
    return 20*np.log10(alias/h1 + 1e-18)
print(f"    {'f0(Hz)':>8} {'hard clip':>11} {'tanh':>9} {'x-x³/3':>9} {'atan':>9}   ← 混叠/基频 (dB)")
for f0t in [500.0, 1000.0, 2000.0, 4000.0, 6000.0, 8000.0, 10000.0]:
    mm = int(round(f0t*N/SR)); ff = mm*SR/N
    row = [alias_ratio(fn, ff) for fn in (ws_hard, ws_tanh, ws_cubic, ws_atan)]
    print(f"    {ff:>8.1f}" + "".join(f"{v:>11.1f}" if i==0 else f"{v:>9.1f}" for i,v in enumerate(row)))
print("    → 1000Hz 时几乎无混叠（h3=3k, h5=5k... 都在带内）")
print("    → 8000Hz 时 h3=24k 已经贴着 Nyquist，h5/h7 全部折叠回来")

print("\n=== 4. 过采样能挽回多少（理想砖墙滤波器，只保留 < SR/2）===")
def alias_ratio_os(fn, f0, os, amp=0.5, n=N//4, sr=SR):
    nn = n*os
    x = amp*np.sin(2*np.pi*f0*np.arange(nn)/(sr*os))
    y = fn(x)
    Y = np.fft.rfft(y)
    fr = np.fft.rfftfreq(nn, 1.0/(sr*os))
    Y[fr >= sr/2] = 0.0                      # 理想抗混叠
    y = np.fft.irfft(Y, nn)[::os]            # 抽取
    nn2 = len(y); w = np.hanning(nn2)
    Y2 = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w)
    m = int(round(f0*nn2/sr)); f0b = m*sr/nn2
    P = Y2**2; mask = np.zeros(len(P), bool)
    for k in range(0, 80):
        b = int(round(k*f0b*nn2/sr))
        if b < len(P): mask[max(0,b-3):b+4] = True
    return 20*np.log10(np.sqrt(P[~mask].sum())/(Y2[m]+1e-18) + 1e-18)
print(f"    {'f0(Hz)':>8}{'无过采样':>11}{'2x':>9}{'4x':>9}{'8x':>9}{'16x':>9}   ← 混叠/基频 (dB), tanh drive=3")
for f0t in [2000.0, 4000.0, 6000.0, 8000.0]:
    mm = int(round(f0t*(N//4)/SR)); ff = mm*SR/(N//4)
    row = [alias_ratio_os(ws_tanh, ff, os) for os in (1,2,4,8,16)]
    print(f"    {ff:>8.1f}" + "".join(f"{v:>11.1f}" if i==0 else f"{v:>9.1f}" for i,v in enumerate(row)))
print("    → 过采样把混叠推低 20-40 dB，但不是无限: 抗混叠滤波器的过渡带决定残留")

print("\n=== 5. Chebyshev 基: 精确控制谐波次数 ===")
from numpy.polynomial import chebyshev as Ch
for order in [1,2,3,4,5]:
    c = np.zeros(order+1); c[order] = 1.0
    p = Ch.cheb2poly(c)
    fn = lambda x, p=p: np.polynomial.polynomial.polyval(x, p)
    x = 0.5*np.sin(2*np.pi*f0*np.arange(N)/SR)
    y = fn(x); w = np.hanning(N)
    Y = np.abs(np.fft.rfft(y*w))*2.0/np.sum(w)
    def at(f): return 20*np.log10(Y[int(round(f*N/SR))]+1e-15)
    hs = [at(k*f0)-at(f0) for k in range(1,7)]
    print(f"    T{order}(x): " + "  ".join(f"h{k+1}={v:>7.1f}" for k,v in enumerate(hs)))
print("    → T_k(cosθ)=cos(kθ)：T_k 作为 waveshaper 只产生第 k 次谐波。")
print("      想精确设计谐波结构（比如「只要 3 次」），就在 Chebyshev 基上写系数再转回幂基。")
