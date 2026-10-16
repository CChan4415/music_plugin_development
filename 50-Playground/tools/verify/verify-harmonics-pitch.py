import numpy as np
print("=== 谐波与泛音列 + 音高感知：实测 ===\n")
SR = 48000.0

# ① 谐波列 vs 非谐波：为什么后者听起来"不准"/"金属感"
def make_tone(f0, ratios, amps, dur=1.0, sr=SR):
    t = np.arange(int(sr*dur))/sr
    return sum(a*np.sin(2*np.pi*f0*r*t) for r, a in zip(ratios, amps))/sum(amps)

print("① 谐波性对音高感知的影响")
print("   实验：同一组频率间隔，谐波 vs 非谐波")
f0 = 220.0
harm_ratios = [1, 2, 3, 4, 5, 6]
inharm_ratios = [1, 2.1, 3.3, 4.6, 5.9, 7.3]   # 拉伸（钢琴式）
amps = [1.0, 0.5, 0.33, 0.25, 0.2, 0.17]
for name, ratios in [("严格谐波", harm_ratios), ("非谐波（拉伸）", inharm_ratios)]:
    x = make_tone(f0, ratios, amps)
    # 自相关测周期
    xc = x - x.mean()
    ac = np.correlate(xc, xc, mode='full')[len(xc)-1:]
    lo, hi = int(SR/1000), int(SR/100)
    lag = lo + np.argmax(ac[lo:hi])
    print(f"   {name:<16} 自相关周期对应 {SR/lag:>7.1f} Hz（f0={f0}）")

print("""
✅ 结论：严格谐波 → 自相关在 1/f0 处有明显峰 → 大脑判为单一音高
   非谐波 → 周期性被破坏 → 音高感变弱/变成"金属声"
""")

# ② 缺失基频（missing fundamental）
print("② 缺失基频实验：去掉 f0，只剩 2f0/3f0/4f0")
for label, ratios in [("含 f0", [1,2,3,4,5]), ("缺 f0", [2,3,4,5])]:
    x = make_tone(f0, ratios, [1.0]*len(ratios))
    xc = x - x.mean()
    ac = np.correlate(xc, xc, mode='full')[len(xc)-1:]
    lo, hi = int(SR/1000), int(SR/100)
    seg = ac[lo:hi]
    lag = lo + np.argmax(seg)
    print(f"   {label:<8} 自相关峰 → {SR/lag:>7.1f} Hz")

print("""
✅ 缺失基频：即使 220Hz 不存在，自相关周期仍是 1/220
   → 这就是"电话里低音听不到但仍能听出音高"的原理
""")

# ③ 泛音列与音色
print("③ 泛音幅度分布决定音色（同一个 f0）")
t = np.arange(int(SR*0.5))/SR
timbres = {
    "正弦（只有基频）": [1.0, 0, 0, 0, 0, 0],
    "方波（奇次谐波）": [1.0, 0, 1/3, 0, 1/5, 0],
    "锯齿（全部谐波）": [1.0, 1/2, 1/3, 1/4, 1/5, 1/6],
    "三角（奇次平方）": [1.0, 0, 1/9, 0, 1/25, 0],
}
for name, amps in timbres.items():
    x = make_tone(f0, [1,2,3,4,5,6], amps)
    X = np.abs(np.fft.rfft(x*np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1/SR)
    # 数显著谐波数
    thr = X.max()*0.01
    n_harm = sum(1 for k in range(1,7) if X[np.argmin(np.abs(f-f0*k))] > thr)
    print(f"   {name:<18} 显著谐波数 {n_harm}")
print("""
✅ 同一个基频，泛音分布不同 → 音色完全不同（这就是"音色"的定义）
""")
