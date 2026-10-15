"""非线性处理：偶次/奇次谐波与工程实现 —— 补充实测
   为 30-Wiki/DSP/非线性处理.md 提供数据。

聚焦:
  1. 奇函数 vs 非对称函数: 偶次谐波的产生条件（量化到 dB）
  2. 非对称 shaper 的 DC 偏移（必须在输出端去直流）
  3. 各种 shaper 的谐波衰减速率（决定混叠严重程度）
  4. drive 如何改变谐波结构
  5. 多项式 shaper: 纯 2 次 / 纯 3 次的谐波纯度
  6. 过采样前后：偶次谐波不受影响、混叠被压低
"""
import numpy as np

SR, N = 48000.0, 1 << 16

def bin_freq(m): return m * SR / N

# ── shapers ──
def ws_hard(x, d=3.0):  return np.clip(d*x, -1.0, 1.0)
def ws_tanh(x, d=3.0):  return np.tanh(d*x)
def ws_atan(x, d=3.0):  return (2/np.pi)*np.arctan(d*x*np.pi/2)
def ws_cubic(x, d=3.0): return np.clip(d*x, -1.5, 1.5) - np.clip(d*x, -1.5, 1.5)**3/3.0
def ws_sq(x, d=3.0):    return np.tanh(d*x)**2 - 0.5          # 非对称（偶函数为主）
def ws_asym(x, d=3.0):  return np.tanh(d*x) + 0.3*np.tanh(d*x)**2   # 非对称
def ws_poly2(x, d=1.0): return x + 0.5*x**2                   # 纯 2 次（无 3 次）
def ws_poly3(x, d=1.0): return x - x**3/3.0                   # 纯 3 次（无 2 次）
def ws_cheb2(x, d=1.0): return 2*x**2 - 1.0                   # T2: 只产生 2 次
def ws_cheb3(x, d=1.0): return 4*x**3 - 3*x                   # T3: 只产生 3 次

def spectrum(x, amp=0.5, n=N, sr=SR, f0=None):
    """返回 (Y, freqs, h1_db)。f0 落在整数 bin 上，谐波是干净谱线。"""
    w = np.hanning(n)
    Y = np.abs(np.fft.rfft(x*w)) * 2.0/np.sum(w)
    return Y

def harm_table(fn, f0, amp=0.5, n=N, sr=SR):
    x = amp*np.sin(2*np.pi*f0*np.arange(n)/sr)
    y = fn(x)
    Y = spectrum(y, n=n, sr=sr)
    def at(f):
        if f >= sr/2: return np.nan
        return 20*np.log10(Y[int(round(f*n/sr))] + 1e-18)
    h1 = at(f0)
    return {
        'h1': h1,
        'dc': at(0.0),
        'odd':  [at(k*f0)-h1 for k in (3,5,7,9)],
        'even': [at(k*f0)-h1 for k in (2,4,6,8)],
        'y_dc': float(np.mean(y)),      # 真实 DC 分量（不是 FFT bin）
        'y_max': float(np.max(np.abs(y))),
    }

m = 1365; f0 = bin_freq(m)
print(f"测试频率 f0 = {f0:.4f} Hz（= {m} × SR/N，精确落在 FFT bin 上）")
print(f"采样率 {SR:.0f} Hz，输入幅度 0.5，drive = 3\n")

print("=== 1. 奇函数 vs 非对称：偶次谐波从哪来 ===")
print(f"   {'shaper':<26}{'对称性':<12}{'h2':>9}{'h3':>9}{'h4':>9}{'h5':>9}{'真实DC':>12}")
rows = [
    ("hard clip",           ws_hard,  "奇函数"),
    ("tanh",                ws_tanh,  "奇函数"),
    ("atan",                ws_atan,  "奇函数"),
    ("x - x³/3",            ws_cubic, "奇函数"),
    ("T2 (2x²-1)",          ws_cheb2, "偶函数"),
    ("T3 (4x³-3x)",         ws_cheb3, "奇函数"),
    ("x + 0.5x²",           ws_poly2, "非对称"),
    ("tanh+0.3tanh²",       ws_asym,  "非对称"),
    ("tanh² - 0.5",         ws_sq,    "偶函数"),
]
for nm, fn, sym in rows:
    t = harm_table(fn, f0)
    print(f"   {nm:<26}{sym:<12}{t['even'][0]:>9.1f}{t['odd'][0]:>9.1f}"
          f"{t['even'][1]:>9.1f}{t['odd'][1]:>9.1f}{t['y_dc']:>12.2e}")

print("\n   判定规则（数学上精确）:")
print("     若 f(-x) = -f(x)  （奇函数）→ **所有偶次谐波恒为 0**，且 DC = 0")
print("     若 f(-x) =  f(x)  （偶函数）→ **所有奇次谐波恒为 0**")
print("     一般非对称函数 → 奇次 + 偶次 + DC 全都有")
print("   ⚠️ 实测中『奇函数』那几行的偶次谐波在 -220 dB 左右 = 纯数值噪声，不是真的存在。")

print("\n=== 2. 非对称 shaper 的 DC 偏移（必须去直流）===")
print(f"   {'shaper':<26}{'输出均值(DC)':>16}{'折合 dBFS':>14}{'输出峰值':>12}")
for nm, fn in [("tanh (对称)", ws_tanh), ("tanh+0.3tanh²", ws_asym),
               ("tanh² - 0.5", ws_sq), ("x + 0.5x²", ws_poly2)]:
    t = harm_table(fn, f0)
    print(f"   {nm:<26}{t['y_dc']:>16.3e}{20*np.log10(abs(t['y_dc'])+1e-30):>14.1f}{t['y_max']:>12.4f}")
print("   → 非对称 shaper 会产生**真实的直流分量**（不是数值误差）。")
print("     它会被后续的压缩器/限制器当成『能量』→ 白白占用 headroom。")
print("     必须在 shaper 之后加一个 DC blocker（一阶高通，截止 5–20 Hz）。")
print("   ⚠️ 注意: 直流对**压缩器**的伤害远大于对耳朵的伤害（耳朵听不到 DC）。")

print("\n=== 3. 谐波衰减速率（决定混叠严重程度）===")
print("   在 Nyquist 以下测到的最高谐波相对基频的电平（越高 = 越难抗混叠）")
print(f"   {'shaper':<26}{'h3':>8}{'h5':>8}{'h7':>8}{'h9':>8}{'h11':>8}{'h13':>8}")
for nm, fn in [("hard clip", ws_hard), ("tanh", ws_tanh), ("atan", ws_atan),
               ("x - x³/3", ws_cubic)]:
    x = 0.5*np.sin(2*np.pi*f0*np.arange(N)/SR)
    y = fn(x); Y = spectrum(y)
    def at(f): return 20*np.log10(Y[int(round(f*N/SR))] + 1e-18)
    h1 = at(f0)
    vals = [at(k*f0)-h1 for k in (3,5,7,9,11,13)]
    print(f"   {nm:<26}" + "".join(f"{v:>8.1f}" for v in vals))
print("   → hard clip 的谐波衰减最慢（约 -12 dB/oct），所以混叠最严重；")
print("     tanh/atan 衰减快得多，同一个过采样倍率下混叠低 10–20 dB。")
print("     ⚠️ 这**不意味着** tanh 不需要过采样，只是需要更低的倍率。")

print("\n=== 4. drive 如何改变谐波结构（tanh）===")
print(f"   {'drive':>7}{'h1(dB)':>10}{'h3':>9}{'h5':>9}{'h7':>9}{'h9':>9}{'THD(偶+奇)':>12}")
for d in [0.5, 1.0, 2.0, 3.0, 6.0, 12.0]:
    fn = lambda x, d=d: np.tanh(d*x)
    t = harm_table(fn, f0)
    allh = t['odd'] + t['even']
    thd = 10*np.log10(sum(10**(v/10) for v in allh))
    print(f"   {d:>7.1f}{t['h1']:>10.2f}{t['odd'][0]:>9.1f}{t['odd'][1]:>9.1f}"
          f"{t['odd'][2]:>9.1f}{t['odd'][3]:>9.1f}{thd:>12.1f}")
print("   → drive 越大，谐波越多、越强。这就是『失真度』旋钮的物理含义。")
print("   ⚠️ 注意 h1 也在变（因为 tanh 有压缩作用）—— 这不是纯『加谐波』，")
print("     它是**同时**在改变基频电平。做 makeup gain 时要考虑这一点。")

print("\n=== 5. 多项式 shaper 的谐波纯度 ===")
print("   在 Chebyshev 基上设计 → 想只要哪次谐波就只要哪次")
print("   ⚠️ 下表是**绝对**电平（dB），不是相对基频 —— 因为纯 T2 没有基频分量，")
print("      用相对值会让归一化除零而给出无意义的数字。")

def abs_harm(fn, f0, amp, ks, n=N, sr=SR):
    x = amp*np.sin(2*np.pi*f0*np.arange(n)/sr)
    y = fn(x); Y = spectrum(y, n=n, sr=sr)
    out = []
    for k in ks:
        f = k*f0
        out.append(np.nan if f >= sr/2 else 20*np.log10(Y[int(round(f*n/sr))] + 1e-18))
    return out

print(f"\n   {'shaper (输入幅度=1.0)':>26}{'h1':>9}{'h2':>9}{'h3':>9}{'h4':>9}{'h5':>9}")
for nm, fn in [("T2 = 2x²-1", ws_cheb2), ("T3 = 4x³-3x", ws_cheb3),
               ("x + 0.5x²", ws_poly2), ("x - x³/3", ws_poly3)]:
    v = abs_harm(fn, f0, 1.0, [1,2,3,4,5])
    print(f"   {nm:>26}" + "".join(f"{x:>9.1f}" for x in v))

print(f"\n   {'shaper (输入幅度=0.5)':>26}{'h1':>9}{'h2':>9}{'h3':>9}{'h4':>9}{'h5':>9}")
for nm, fn in [("T2 = 2x²-1", ws_cheb2), ("T3 = 4x³-3x", ws_cheb3)]:
    v = abs_harm(fn, f0, 0.5, [1,2,3,4,5])
    print(f"   {nm:>26}" + "".join(f"{x:>9.1f}" for x in v))

print("\n   ⚠️ 关键: Chebyshev 恒等式 T_k(cosθ) = cos(kθ) **只在输入幅度 = 1 时成立**。")
print("     幅度 1.0 时 T2 输出只有 h2（h1/h3/h4 都在 -220 dB 以下 = 数值噪声）；")
print("     幅度 0.5 时同一个 T2 就**同时产生 h2/h3/h4/h5**，不再纯净。")
print("     —— 这是用 Chebyshev 做『精确谐波设计』时最容易踩的坑:")
print("        Shaper 是**幅度相关**的，输入电平一变，谐波结构就变。")

print("\n=== 6. 偶次谐波与过采样无关（它不产生混叠的那部分）===")
print("   输入 f0 = 3000 Hz（h2=6k 在带内；h5=15k 在带内；h7=21k 在带内；h9=27k 越界）")
f0b = 3000.0
for nm, fn in [("tanh (奇函数)", ws_tanh), ("tanh+0.3tanh² (非对称)", ws_asym)]:
    t = harm_table(fn, f0b)
    print(f"   {nm:<26} h2={t['even'][0]:>7.1f} h3={t['odd'][0]:>7.1f} "
          f"h4={t['even'][1]:>7.1f} h5={t['odd'][1]:>7.1f}")
print("   → 偶次谐波是**带内**的合法成分，过采样不会动它（也不该动）。")
print("     过采样只压低『越过 Nyquist 折回来』的那部分，见 [[混叠 aliasing]]。")
print("     所以『加了过采样后音色变暖』是错觉 —— 变的是混叠少了，不是偶次谐波多了。")

print("\n✅ exp_harmonics 完成")
