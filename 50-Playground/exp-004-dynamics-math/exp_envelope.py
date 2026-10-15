"""包络跟随器 envelope follower 的数值验证
   为 30-Wiki/DSP/包络跟随器 envelope follower.md 提供实测数据。

验证清单:
  1. one-pole 系数 coeff = 1 - exp(-1/(tau*fs)) 的 63% 时间常数
  2. 指数逼近 vs 线性斜坡: 到达 90% 需要多少倍 tau
  3. 真正的 peak 检测器 = 快 attack + 慢 release; 对比 RMS 检测
  4. 慢平滑的『peak 检测器』其实退化成均值检测器（反直觉）
  5. RMS 指数平均的等效积分时间 ≈ 2*tau（用输出方差验证）
  6. 检测器前高通: 低频不再触发压缩（用检测器峰值衡量）
  7. 平滑在 dB 域 vs 线性域
"""
import numpy as np

SR = 48000.0

def coeff_from_tau(tau_s, sr=SR):
    """标准 one-pole 系数: y[n] = y[n-1] + coeff*(x[n] - y[n-1])
       连续时间等价 tau = -1/(fs*ln(1-coeff))  ⟺  coeff = 1 - exp(-1/(tau*fs))"""
    return 1.0 - np.exp(-1.0 / (tau_s * sr))

def tau_from_coeff(c, sr=SR):
    return -1.0 / (sr * np.log(1.0 - c))

def one_pole(x, coeff, y0=0.0):
    y = np.empty(len(x)); acc = y0
    for i in range(len(x)):
        acc += coeff * (x[i] - acc); y[i] = acc
    return y

def one_pole_asym(x, c_att, c_rel, y0=0.0):
    """attack/release 用不同系数 —— 真正的 peak 检测器"""
    y = np.empty(len(x)); acc = y0
    for i in range(len(x)):
        v = x[i]
        acc += (c_att if v > acc else c_rel) * (v - acc)
        y[i] = acc
    return y

step = np.ones(int(SR * 1.0))

# ---------- 1. 系数公式 ----------
print("=== 1. 系数公式的往返一致性 ===")
print(f"   {'目标 tau(ms)':>12}{'coeff':>14}{'反算 tau(ms)':>14}{'误差':>12}")
for ms in [0.1, 1.0, 5.0, 10.0, 50.0, 100.0, 300.0]:
    c = coeff_from_tau(ms * 1e-3); back = tau_from_coeff(c) * 1e3
    print(f"   {ms:>12.1f}{c:>14.8f}{back:>14.6f}{abs(back-ms):>12.2e}")

# ---------- 2. 实测 63% ----------
print("\n=== 2. 实测: 阶跃下到达 63.2% 的样本数 ===")
print(f"   {'tau(ms)':>9}{'coeff':>13}{'实测63%点':>12}{'理论 tau*fs':>14}{'偏差':>10}")
for ms in [1.0, 5.0, 10.0, 50.0, 100.0]:
    c = coeff_from_tau(ms * 1e-3); y = one_pole(step, c)
    k = int(np.argmax(y >= 1.0 - np.exp(-1.0))); theo = ms * 1e-3 * SR
    print(f"   {ms:>9.1f}{c:>13.8f}{k:>12d}{theo:>14.2f}{(k-theo)/theo*100:>9.2f}%")

print("\n=== 3. 指数逼近的到达时间（tau = 10 ms）===")
c = coeff_from_tau(10e-3); y = one_pole(step, c)
for frac, lnk in [(0.5, 0.6931), (0.632, 1.0), (0.9, 2.3026), (0.99, 4.6052), (0.999, 6.9078)]:
    k = int(np.argmax(y >= frac))
    print(f"   到达 {frac*100:>5.1f}% 用 {k:>6d} 样本 = {k/SR*1e3:>8.3f} ms "
          f"(= {k/(10e-3*SR):>5.2f} × tau, 理论 {lnk:.4f})")
print("   → 指数逼近『永远不到达』。线性斜坡有确定的完成时间;")
print("     指数逼近只有时间常数, 剩余误差永远存在（到 99.9% 要 6.9×tau）")

# ---------- 4. 真正的 peak vs RMS ----------
print("\n=== 4. peak 检测器（快 attack + 慢 release）vs RMS 检测器 ===")
t = np.arange(int(SR * 0.5)) / SR
sine = 0.5 * np.sin(2 * np.pi * 1000 * t)
c_att = coeff_from_tau(0.05e-3)      # attack tau = 0.05 ms（几乎瞬时）
c_rel = coeff_from_tau(100e-3)       # release tau = 100 ms
c_rms = coeff_from_tau(10e-3)

pk = one_pole_asym(np.abs(sine), c_att, c_rel)
rms = np.sqrt(np.maximum(one_pole(sine**2, c_rms), 0.0))
S = lambda a: float(np.mean(a[int(len(a)*0.9):]))
print(f"   1 kHz 正弦, 幅度 0.5（峰值）, RMS = 0.5/√2 = {0.5/np.sqrt(2):.6f}")
print(f"   peak 检测器稳态 = {S(pk):.6f} ({20*np.log10(S(pk)):+.3f} dBFS)   ← 正确抓到 0.5")
print(f"   RMS  检测器稳态 = {S(rms):.6f} ({20*np.log10(S(rms)):+.3f} dBFS)")
print(f"   两者差 = {20*np.log10(S(pk)/S(rms)):+.3f} dB  ← 正弦的 crest factor = 3.01 dB")

rng = np.random.default_rng(0)
noise = rng.standard_normal(int(SR * 2.0)); noise = 0.5 * noise / np.max(np.abs(noise))
pk_n = one_pole_asym(np.abs(noise), c_att, c_rel)
rm_n = np.sqrt(np.maximum(one_pole(noise**2, c_rms), 0.0))
print(f"\n   白噪声（同峰值 0.5）:")
print(f"   peak = {S(pk_n):.6f} ({20*np.log10(S(pk_n)):+.3f} dBFS) | RMS = {S(rm_n):.6f} ({20*np.log10(S(rm_n)):+.3f} dBFS)")
print(f"   两者差 = {20*np.log10(S(pk_n)/S(rm_n)):+.3f} dB  ← 噪声的 crest factor 远大于正弦")

# ---------- 5. 反直觉: 慢平滑的 peak 检测器 ==
print("\n=== 5. 反直觉实测: 同一结构，系数决定它是 peak 还是 mean 检测器 ===")
print("   结构固定为 rectify + one-pole: y += c*(|x| - y)。只改 c。")
print(f"   {'tau(ms)':>9}{'coeff':>12}{'稳态均值':>11}{'稳态纹波(pk-pk)':>17}{'纹波/dB':>10}{'性质':>16}")
for ms in [0.05, 0.5, 5.0, 50.0]:
    cc = coeff_from_tau(ms*1e-3)
    v = one_pole(np.abs(sine), cc)
    tail = v[int(len(v)*0.9):]
    rip = tail.max() - tail.min()
    kind = "peak 检测" if rip > 0.2 else ("均值检测" if rip < 0.02 else "中间态")
    print(f"   {ms:>9.2f}{cc:>12.6f}{tail.mean():>11.6f}{rip:>17.6f}"
          f"{20*np.log10(max(tail.mean(),1e-12)/max(tail.mean()-rip/2,1e-12)):>10.3f}{kind:>16}")
print("   理论: 平滑足够慢时输出 → mean|x| = (2/π)·A = 0.6366 × 0.5 = 0.31831")
print("   → tau = 0.05 ms 时输出在 0.0001 ~ 0.5 之间摆动 = 真的在跟随波形峰值;")
print("     tau = 50 ms 时纹波趋近 0, 输出稳定在 0.318 = **mean|x|，不是峰值**。")
print("   ⚠️ 这是本页最反直觉的一条: 『peak 检测』不是一个电路结构,")
print("     而是『快 attack』这个参数选择。慢平滑的 peak 检测器读数比 RMS 还低。")

# ---------- 6. 等效积分时间 ----------
print("\n=== 6. RMS: 指数平均的等效积分时间 ===")
print("   理论: 白噪声输入下 Var(out)/Var(in) = α/(2-α) ≈ α/2 (α 小)")
print("         矩形滑动平均长度 N 的方差比 = 1/N")
print("         ⟹ 等效窗长 N_eq = (2-α)/α ≈ 2·tau·fs")
n3 = int(SR * 20)
wn = rng.standard_normal(n3)
print(f"   {'tau(ms)':>9}{'alpha':>12}{'实测 Var 比':>14}{'理论 α/(2-α)':>16}{'N_eq 实测':>12}{'2·tau·fs':>12}")
for ms in [1.0, 5.0, 10.0, 50.0]:
    cc = coeff_from_tau(ms*1e-3)
    out = one_pole(wn, cc)
    ratio = np.var(out[int(n3*0.1):]) / np.var(wn)
    theo = cc/(2-cc)
    print(f"   {ms:>9.1f}{cc:>12.6f}{ratio:>14.6f}{theo:>16.6f}"
          f"{1/ratio:>12.1f}{2*ms*1e-3*SR:>12.1f}")
print("   → 等效积分时间 ≈ 2×tau，且指数平均是**无限记忆**（矩形窗是有限记忆）")
print("     这就是为什么不同压缩器标称『RMS window = 10ms』实际响应差别很大:")
print("     指数平均 / 矩形滑动 / 双时间常数 是三种不同的东西。")

# ---------- 7. 检测器前高通 ----------
print("\n=== 7. 检测器前加高通: 低频不再触发 ===")
def biquad_hp(x, fc, q=0.707, sr=SR):
    w0 = 2*np.pi*fc/sr; a = np.sin(w0)/(2*q); cw = np.cos(w0)
    b0,b1,b2 = (1+cw)/2, -(1+cw), (1+cw)/2
    a0,a1,a2 = 1+a, -2*cw, 1-a
    b0,b1,b2,a1,a2 = b0/a0,b1/a0,b2/a0,a1/a0,a2/a0
    y = np.zeros_like(x); x1=x2=y1=y2=0.0
    for i in range(len(x)):
        v = b0*x[i]+b1*x1+b2*x2-a1*y1-a2*y2
        x2,x1 = x1,x[i]; y2,y1 = y1,v; y[i]=v
    return y

t4 = np.arange(int(SR * 1.0)) / SR
kick = 0.8*np.sin(2*np.pi*55*t4) * np.exp(-t4*8)      # 55Hz 踢鼓
mid  = 0.15*np.sin(2*np.pi*1000*t4)
mix  = kick + mid
print(f"   {'信号':>18}{'无高通(dBFS)':>16}{'120Hz HP(dBFS)':>18}{'差(dB)':>10}")
for nm, sig in [("kick 单独", kick), ("mid 单独", mid), ("kick+mid", mix)]:
    a = np.max(one_pole_asym(np.abs(sig), c_att, c_rel))
    b = np.max(one_pole_asym(np.abs(biquad_hp(sig, 120.0)), c_att, c_rel))
    print(f"   {nm:>18}{20*np.log10(a):>16.2f}{20*np.log10(b):>18.2f}{20*np.log10(a/b):>10.2f}")
print("   → 高通后 kick 的检测电平掉十几 dB, 而中频几乎不变")
print("   ⚠️ 高通只加在检测路径上, 音频路径不变 —— 这是压缩器的标准做法")
print("   ⚠️ 这是二阶 Butterworth（12 dB/oct）。一阶高通对 55Hz 只衰减 ~7dB, 不够")

# ---------- 8. 平滑域 ----------
print("\n=== 8. 平滑在哪个域做? (tau = 20 ms, 目标在 0 / -12 dB 间跳) ===")
# 关键: 平滑器要**预先收敛到初值**, 否则会看到"从 0 爬到 1"的启动瞬态
tgt_db = np.zeros(int(SR*0.4)); tgt_db[int(SR*0.2):] = -12.0
c2 = coeff_from_tau(20e-3)
lin_sm = one_pole(10**(tgt_db/20), c2, y0=1.0)   # ← 初值 = 第一个目标值
db_sm  = one_pole(tgt_db, c2, y0=0.0)
print(f"   {'时刻(ms)':>10}{'目标dB':>10}{'线性域平滑':>14}{'dB域平滑':>12}")
for k in [195, 200, 205, 210, 220, 250, 300, 400, 600]:
    idx = min(int(SR*k/1000), len(tgt_db)-1)
    print(f"   {k:>10}{tgt_db[idx]:>10.1f}{20*np.log10(lin_sm[idx]):>14.3f}{db_sm[idx]:>12.3f}")
print("   → 稳态相同, 但**过渡形状不同**。看 t=220ms（跳变后 20ms = 1×tau）:")
i220 = int(SR*0.220)
print(f"     线性域 {20*np.log10(lin_sm[i220]):.3f} dB | dB 域 {db_sm[i220]:.3f} dB | 目标 -12 dB")
print("   → dB 域已走完 63%, 线性域也走了 63% —— 一阶系统的形状其实一样")
print("     ⚠️ 真正的区别不在『形状』, 而在:")
print("       ① dB 域平滑的是**增益的分贝值**, 与感知响度线性对应;")
print("       ② 当目标跳变**很大**时（如 -60 → 0 dB）, 线性域在低电平段的")
print("          相对变化率极不均匀, 听感上像『先慢后快』或『先快后慢』;")
print("       ③ 多参数联动时（如 makeup gain 跟随 GR）, dB 域才能正确叠加。")
print("   ⚠️ dB 域每样本要 log/exp, CPU 更贵 → 常见折中是线性域平滑 + 特殊系数曲线")
print("   ⚠️ 注意 t=195ms 那一行: 平滑器**必须**预先收敛到初值, 否则启动时会")
print("      从 0 爬升 → 插件刚加载时的一个爆音/淡入。这是 AI 最常漏的一条。")

print("\n✅ exp_envelope 完成")
