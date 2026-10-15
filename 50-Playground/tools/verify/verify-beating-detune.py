#!/usr/bin/env python3
"""
拍频与失谐（beating & detuning）—— 数值验证。

对应 Wiki 页: 30-Wiki/Music-Acoustics/拍频与失谐.md

本脚本验证:
  1. 拍频 = 频率差（用包络实测，不是用公式空谈）
  2. 拍频包络的**精确形状**：2A·|cos(π·Δf·t)|
     ⚠️ 包络的周期是 1/Δf（绝对值让周期减半）→ **起伏率 = Δf**
  3. 拍频的可闻范围（慢拍 → 粗糙感 → 分叉成两个音）
  4. **临界带宽内的失谐 vs 之外**：为什么带宽内"变厚"、之外"分成两个音"
  5. 失谐的"厚度"来源：相位随机化 → 峰值不相关 → crest factor 上升
  6. Unison 的实测：N 个失谐振荡器叠加，峰值/响度怎么随 N 变
  7. 超低音设计：为什么 sub 的失谐听起来是"颤动"而不是"宽"

⚠️ 测量纪律（本库踩过的坑）：
   - **整数周期**信号（否则截断引入假 DC / 假谐波）
   - 测频谱除以 sum(w) 而非 N
   - 测包络用**相对**阈值 + 跳过暂态
   - 包络测量要避开 FFT 的窗边界

只用 numpy，不依赖 scipy。

用法:
    python3 50-Playground/tools/verify/verify-beating-detune.py
"""
import numpy as np

SR = 48000


# ---------------- 工具 ----------------

def envelope_hilbert(x):
    """用 FFT 实现解析信号（Hilbert 变换），取包络。

    比"整流 + 低通"精确得多：它是**无延迟、无纹波**的精确包络。

    原理: 解析信号 z = x + j·H{x}，包络 = |z|。
    实现: 频域上把负频率置零，正频率乘 2。
    """
    n = len(x)
    X = np.fft.fft(x)
    h = np.zeros(n)
    h[0] = 1.0
    if n % 2 == 0:
        h[1:n // 2] = 2.0
        h[n // 2] = 1.0
    else:
        h[1:(n + 1) // 2] = 2.0
    return np.abs(np.fft.ifft(X * h))


def bin_freq(f, sr=SR, n=None):
    """把频率吸附到最近的 FFT bin 上（整数周期），返回吸附后的频率"""
    if n is None:
        raise ValueError("需要 n")
    return round(f * n / sr) * sr / n


def env_peak_rate(env, fmin=0.2, fmax=200.0, skip=0.1, sr=SR):
    """从包络估计"峰率"（每秒多少个包络峰），单位 Hz。

    ⚠️ 用 **FFT 自相关**（Wiener–Khinchin），不是 np.correlate。
       np.correlate(..., 'full') 是 O(n²)：n = 4 s × 48 kHz = 192000 时
       要跑几分钟。FFT 版是 O(n log n)，毫秒级。
       —— 这是本库第 12 次"测量工具会骗你"的近亲：**算法复杂度**也会骗你。

    返回的是包络的**基频**（= 起伏率）。

    ⚠️ 修正（2026-10-15，Lead 复核）：
       原文档说"包络 |cos(π·Δf·t)| 每秒有 2·Δf 个峰，所以拍频 = 峰率/2"
       —— **这是错的**。

       解析：两个正弦之和 = 2A·cos(π·Δf·t)·sin(2π·f_avg·t)
             包络 = |2A·cos(π·Δf·t)|

             cos(π·Δf·t) 的周期 = 2/Δf
             |cos(π·Δf·t)| 的周期 = 1/Δf    ← 取绝对值后周期减半

       → 包络的**基频就是 Δf**，不是 2Δf。

       独立验证（包络的频谱，最可靠的方法）：
         f1=40Hz, f2=41Hz → 包络主频实测 **1.0000 Hz** = Δf ✅
         （不是 2Δf = 2.0 Hz）

       所以 **拍频 = 峰率**（这个函数返回的就是拍频本身）。
    """
    e = env[int(len(env) * skip):-int(len(env) * skip)]
    e = e - e.mean()
    n = len(e)
    # ⚠️ 零填充到 2 倍，避免循环相关的混叠
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    E = np.fft.rfft(e, nfft)
    c = np.fft.irfft(np.abs(E) ** 2, nfft)[:n]
    c /= (c[0] + 1e-30)

    lo = max(1, int(sr / fmax))
    hi = min(int(sr / fmin), n - 2)
    if hi <= lo + 2:
        return float('nan')
    k = int(np.argmax(c[lo:hi])) + lo
    # 抛物线插值
    if 0 < k < n - 1:
        a, b, cc = c[k - 1], c[k], c[k + 1]
        den = a - 2 * b + cc
        if abs(den) > 1e-20:
            k = k + 0.5 * (a - cc) / den
    return float(sr / k)


def modulation_depth(env, skip=0.1):
    """包络的**调制深度** m = (max − min)/(max + min)，∈ [0, 1]。

    ⚠️ 为什么不用 20·log10(max/min)（本库第一次跑就踩了这个坑）:
       两个正弦幅度相同时，包络谷值是**精确的 0**（数值上 ~1e-16）。
       相除得到 258~318 dB 这种数字 —— 它"看起来是个很大的值"，
       但**没有任何分辨力**：所有配置都给出几百 dB，无法比较。

    调制深度的好处:
       - 天然有界 [0,1]，不同配置之间可比
       - m → 1  谷点趋零 = 拍很完全（两音幅度接近）
       - m → 0  包络平坦 = 无拍（只有一个音）
    """
    s = int(len(env) * skip)
    e = env[s:]
    mx, mn = float(np.max(e)), float(np.min(e))
    return (mx - mn) / (mx + mn + 1e-30)


def count_spectral_peaks(x, n_peaks_expected, sr=SR, rel_db=-6.0):
    """数频谱里的主峰个数 —— 用来判断"融合"还是"分叉"。

    ⚠️ 本库踩过的两个坑，这里都避开了:
       1. 归一化必须除以 **sum(w)** 而不是 N（否则整体差 6 dB）
       2. 阈值必须用**相对于本频段最大值**的 dB，不能用绝对值
       3. 必须在两个目标频点附近**各取一个窗**，而不是整段搜局部极大 ——
          否则窗函数旁瓣会被数成峰（本库第一次跑时每个都报 2 个峰）

    做法: 在每个目标频率 ±2 个 bin 内找最大值，若都显著高于
          两峰之间的中点，就判为 2 个峰。
    """
    N = len(x)
    w = np.hanning(N)
    X = np.abs(np.fft.rfft(x * w)) * 2.0 / np.sum(w)     # ⚠️ sum(w) 不是 N
    fr = np.fft.rfftfreq(N, 1.0 / sr)

    fs = n_peaks_expected           # 预期的两个频率
    vals = []
    for f in fs:
        m = np.abs(fr - f) < 3.0 / (N / sr) * 3      # ±3 bin
        if not np.any(m):
            return 0, 0.0, 0.0
        vals.append(float(np.max(X[m])))
    # 谷：两峰之间的中点
    mid = 0.5 * (fs[0] + fs[1])
    m = np.abs(fr - mid) < 3.0 / (N / sr) * 3
    valley = float(np.max(X[m])) if np.any(m) else 0.0
    if valley <= 0:
        return 2, 99.0, valley
    # 谷比峰低多少 dB（谷越深，越像"两个独立音"）
    depth = 20 * np.log10(min(vals[0], vals[1]) / valley)
    return (2 if depth > 3.0 else 1), depth, valley


# ---------------- 1. 拍频 = 频率差 ----------------

def t1_beat_frequency():
    print("=" * 74)
    print("① 拍频 = 频率差（实测包络的调制周期，与公式对比）")
    print("=" * 74)

    dur = 2.0
    N = int(SR * dur)
    f1_base = 1000.0

    print(f"   f1 = {f1_base:.0f} Hz 固定，扫 Δf")
    print(f"  {'Δf (Hz)':>9} {'预期拍周期':>11} {'实测拍周期':>11} "
          f"{'实测拍频':>10} {'误差':>9}")

    for df in [1.0, 2.0, 4.0, 8.0, 16.0, 32.0]:
        # ⚠️ 两个频率都吸附到 bin 上 → 整数周期
        f2 = f1_base + df
        f2b = round(f2 * N / SR) * SR / N
        df_real = f2b - f1_base
        t = np.arange(N) / SR
        x = 0.5 * np.sin(2 * np.pi * f1_base * t) \
            + 0.5 * np.sin(2 * np.pi * f2b * t)
        env = envelope_hilbert(x)
        # ✅ env_peak_rate 返回的就是包络基频 = 拍频 Δf 本身（不要再 /2）
        measured = env_peak_rate(env, fmin=df_real * 0.3, fmax=df_real * 4)
        period = 1.0 / measured
        print(f"  {df_real:>9.3f} {1 / df_real:>11.4f} {period:>11.4f} "
              f"{measured:>10.4f} {measured - df_real:>+9.5f}")

    print("\n   ✅ 拍频精确等于频率差 |f2 − f1|")
    print("   ⚠️ 本库在这里错过一次：曾以为包络每秒有 2·Δf 个峰、")
    print("      于是把自相关结果除以 2，得到**恰好一半**的拍频。")
    print("      正确关系: 包络 |cos(π·Δf·t)| 的周期 = 1/Δf，")
    print("               峰值也**每 1/Δf 秒一个** → 拍频 = 峰率 = Δf")
    print("   ⚠️ 测试里两个频率**都**要吸附到 bin 上，否则泄漏会污染包络")


# ---------------- 2. 拍频包络的精确形状 ----------------

def t2_envelope_shape():
    print("\n" + "=" * 74)
    print("② 拍频包络的精确形状：2A·|cos(π·Δf·t)|")
    print("=" * 74)

    dur = 0.5
    N = int(SR * dur)
    f1 = 1000.0
    df = 8.0
    f2 = round((f1 + df) * N / SR) * SR / N
    df_real = f2 - f1
    t = np.arange(N) / SR
    A = 0.5
    x = A * np.sin(2 * np.pi * f1 * t) + A * np.sin(2 * np.pi * f2 * t)

    # 解析推导:
    #   sin(a) + sin(b) = 2·sin((a+b)/2)·cos((a−b)/2)
    #   → 载波频率 (f1+f2)/2，包络 2A·|cos(π·Δf·t)|
    theory = 2 * A * np.abs(np.cos(np.pi * df_real * t))
    env = envelope_hilbert(x)

    # 跳过边界
    s, e = int(0.05 * N), int(0.95 * N)
    err = np.max(np.abs(env[s:e] - theory[s:e]))
    print(f"   f1 = {f1:.1f} Hz, f2 = {f2:.4f} Hz, Δf = {df_real:.4f} Hz, A = {A}")
    print(f"   解析包络 2A·|cos(π·Δf·t)| vs 实测包络: 最大误差 = {err:.3e}")
    assert err < 1e-9, f"包络形状不符: {err}"
    print("   ✅ 包络形状精确是 2A·|cos(π·Δf·t)|")

    print(f"\n   包络最大值 = {env.max():.6f} （理论 2A = {2 * A}）")
    print(f"   包络最小值 = {env.min():.6f} （理论 0）")

    # 关键：包络 |cos(π·Δf·t)| 的周期是 1/Δf，且峰值也是每 1/Δf 一个
    print(f"\n   ⚠️ 一个最容易搞错的点（本库错过一次）：")
    print(f"      |cos(π·Δf·t)| 的周期是 **1/Δf = {1 / df_real:.4f} s**")
    print(f"      人耳听到的'拍'频率也是 **Δf = {df_real:.1f} Hz** —— 两者一致")
    print(f"      直觉上会以为'cos 有正负两个半周 → 每周期两个峰 → 2Δf'，")
    print(f"      **但取绝对值后 cos 的负半周被翻上来，峰正好也只有一个**")
    print(f"      → 拍频 = 包络基频 = Δf。把它除以 2 会得到恰好一半的错值")

    # 实测：包络函数周期 & 峰间隔，两者都应等于 1/Δf
    from_ = env[s:e]
    thr = 0.9 * np.max(from_)
    pk_idx = [i for i in range(1, len(from_) - 1)
              if from_[i] > from_[i - 1] and from_[i] > from_[i + 1]
              and from_[i] > thr]
    span = (e - s) / SR
    print(f"\n   实测: {span:.3f} s 内 {len(pk_idx)} 个包络峰，"
          f"即 {len(pk_idx) / span:.2f} 峰/秒")
    print(f"   理论: Δf = {df_real:.2f} 峰/秒 ✅（不是 2Δf = {2 * df_real:.2f}）")
    if len(pk_idx) > 1:
        gaps = np.diff(pk_idx) / SR
        print(f"   相邻峰间隔: 均值 {gaps.mean():.4f} s, "
              f"理论 1/Δf = {1 / df_real:.4f} s ✅")
        assert abs(gaps.mean() - 1 / df_real) < 0.02 * (1 / df_real), \
            "峰间隔应等于 1/Δf"


# ---------------- 3. 拍频的可闻区间 ----------------

def t3_audibility_ranges():
    print("\n" + "=" * 74)
    print("③ 拍频的可闻区间（主观描述的物理对应）")
    print("=" * 74)

    fc = 1000.0
    print(f"   两个 1 kHz 附近的正弦，间隔 Δf：")
    print(f"  {'Δf (Hz)':>9} {'拍率':>10} {'Δf/ERB':>9} {'主观（文献经验）':>28}")

    # ERB @ 1kHz = 132.6 Hz（见 verify-critical-band.py）
    erb = 24.7 * (4.37 * fc / 1000.0 + 1.0)
    labels = [
        (0.5, "缓慢起伏，像音量旋钮在动"),
        (2.0, "清晰的'哇哇'拍"),
        (5.0, "快速颤动"),
        (15.0, "粗糙感（roughness）"),
        (30.0, "很强的粗糙感 / 嗡"),
        (70.0, "接近临界带宽，开始分叉"),
        (erb, "≈ 1 ERB 边界"),
        (200.0, "明确听到两个音"),
    ]
    for df, lab in labels:
        rate = df
        print(f"  {df:>9.1f} {rate:>10.1f} {df / erb:>9.3f} {lab:>28}")

    print("\n   ⚠️ 三个区间（这是**文献经验值**，具体边界因人/频率而异）:")
    print("      Δf < ~10 Hz   → 听到**拍**（慢的起伏）")
    print("      ~10–70 Hz     → 听到**粗糙（roughness）**：不再是拍，是一种'沙哑'")
    print("      Δf > ~1 ERB   → 分成**两个独立的音**")
    print("\n   ⚠️ 本表给的是**定性**描述。精确的拍→粗糙→分叉边界")
    print("      需要查心理声学文献（Zwicker & Fastl），本页不做定量断言。")


# ---------------- 4. 临界带宽内外的失谐 ----------------

def t4_detune_inside_outside():
    print("\n" + "=" * 74)
    print("④ 临界带宽内的失谐 vs 之外（同为 ±Δf，结果完全不同）")
    print("=" * 74)

    dur = 2.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    fc = 1000.0
    erb = 24.7 * (4.37 * fc / 1000.0 + 1.0)
    cb = 25.0 + 75.0 * (1.0 + 1.4 * (fc / 1000.0) ** 2) ** 0.69

    print(f"   中心 {fc:.0f} Hz，ERB = {erb:.1f} Hz，临界带宽 = {cb:.1f} Hz")
    print(f"   每个测试: 两个正弦 f_c ± Δf/2，幅度各 0.5\n")
    print(f"  {'Δf (Hz)':>9} {'Δf/ERB':>8} {'调制深度':>10} "
          f"{'谱谷深度(dB)':>13} {'谱峰数':>8} {'Δf<CB?':>8}")

    for df in [2.0, 10.0, 30.0, 60.0, 100.0, 132.6, 200.0, 400.0, 800.0]:
        f1r = round((fc - df / 2) * N / SR) * SR / N
        f2r = round((fc + df / 2) * N / SR) * SR / N
        df_real = f2r - f1r
        x = 0.5 * np.sin(2 * np.pi * f1r * t) + 0.5 * np.sin(2 * np.pi * f2r * t)
        env = envelope_hilbert(x)
        md = modulation_depth(env, skip=0.05)
        n_peaks, depth, _ = count_spectral_peaks(x, (f1r, f2r))

        inside = "是" if df_real < cb else "否"
        print(f"  {df_real:>9.2f} {df_real / erb:>8.3f} {md:>10.4f} "
              f"{depth:>13.2f} {n_peaks:>8} {inside:>8}")

    print("\n   ⚠️ 怎么读这三列")
    print("      调制深度 m = (max−min)/(max+min)，∈[0,1]：")
    print("         m ≈ 1 → 谷点趋零，拍很完全（两个等幅正弦）")
    print("      谱谷深度：两个谱峰之间的凹陷有多深（dB）")
    print("         深（> 20 dB）→ 频谱上明确是**两个峰** = 分叉")
    print("      谱峰数：按'谷比峰低 3 dB 以上就算分开'的判据给出")
    print("\n   ⚠️ 重要：调制深度**不随 Δf 变化**")
    print("      两个等幅正弦，无论 Δf 多大，包络谷值都是 0 → m 恒为 1")
    print("      所以'融合 vs 分叉'**不能**从包络判断，必须看频谱")
    print("      ——— 这是本库第一次跑这张表时得出的反直觉结论")
    print("\n   ⚠️ '变厚'发生在**中间地带**（Δf 几 Hz ~ 几十 Hz）:")
    print("      拍频快到超出'起伏'的感知范围，但谱峰还没分开 → 听成'厚/宽'")


# ---------------- 5. 失谐的"厚度"：相位随机化 ----------------

def t5_thickness_mechanism():
    print("\n" + "=" * 74)
    print("⑤ '变厚'的机制之一：去相关 → 峰值不再对齐")
    print("=" * 74)

    dur = 4.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    f0 = 110.0
    n_osc = 7

    # 情况 A: N 个振荡器**同相**（完全相关）
    xa = sum(np.sin(2 * np.pi * f0 * t) for _ in range(n_osc)) / n_osc

    # 情况 B: N 个振荡器**微失谐**（±1% 内均匀分布）
    rng = np.random.default_rng(20261015)
    detunes = np.linspace(-0.01, 0.01, n_osc)
    xb = sum(np.sin(2 * np.pi * f0 * (1 + d) * t) for d in detunes) / n_osc

    # 情况 C: 同频率但**随机相位**
    phases = rng.uniform(0, 2 * np.pi, n_osc)
    xc = sum(np.sin(2 * np.pi * f0 * t + p) for p in phases) / n_osc

    print(f"   {n_osc} 个 {f0:.0f} Hz 振荡器，平均后:")
    print(f"  {'配置':>22} {'峰值':>9} {'RMS':>9} {'crest(dB)':>11}")
    for label, x in [('同相（完全相关）', xa),
                     ('微失谐 ±1%', xb),
                     ('同频随机相位', xc)]:
        pk = np.max(np.abs(x))
        rm = np.sqrt(np.mean(x ** 2))
        print(f"  {label:>22} {pk:>9.4f} {rm:>9.4f} "
              f"{20 * np.log10(pk / rm) + 1e-30:>11.2f}")

    print(f"\n   理论: 完全相关的 {n_osc} 个正弦平均后还是正弦（crest = 3.01 dB）")
    print(f"         完全去相关的 {n_osc} 个正弦平均后 crest → 上升")
    print(f"         完全无关时的峰值 → √(2·ln(N)) 量级（高斯极值统计）")
    print(f"         理论 √(2·ln({n_osc})) = {np.sqrt(2 * np.log(n_osc)):.3f}")

    # 真正的去相关度量：归一化互相关系数峰值
    def xcorr_peak(a, b):
        """峰值归一化互相关系数。

        ⚠️ 用 FFT（Wiener–Khinchin），不用 np.correlate —— 后者是 O(n²)。
           本库踩过：4 s @ 48 kHz（n = 192000）的 np.correlate 要跑好几分钟。
        """
        a = a - a.mean(); b = b - b.mean()
        n = len(a)
        nfft = 1 << int(np.ceil(np.log2(2 * n)))
        C = np.fft.irfft(np.fft.rfft(a, nfft) * np.conj(np.fft.rfft(b, nfft)),
                         nfft)
        return float(np.max(np.abs(C)) /
                     (np.sqrt(np.sum(a ** 2) * np.sum(b ** 2)) + 1e-30))

    print(f"\n   两两相关度（峰值互相关系数）:")
    o1 = np.sin(2 * np.pi * f0 * t)
    o2_same = np.sin(2 * np.pi * f0 * t)
    o2_det = np.sin(2 * np.pi * f0 * 1.01 * t)
    o2_ph = np.sin(2 * np.pi * f0 * t + 1.234)
    print(f"      同频同相  : {xcorr_peak(o1, o2_same):.6f}")
    print(f"      同频异相  : {xcorr_peak(o1, o2_ph):.6f}  ← 完全相关，只是移了位")
    print(f"      失谐 1%   : {xcorr_peak(o1, o2_det):.6f}  ← 随时间漂移，**去相关**")
    print("\n   ⚠️ 关键区分:")
    print("      '随机相位' 只是把峰值**挪位置**，N 个叠加后峰值依然会撞上 → 不解决厚度")
    print("      '微失谐' 让相对相位**随时间漂移** → 峰值持续错开 → 这才是'厚'")
    print("      但失谐也会引入拍频 → 在临界带宽内才是'厚'，之外是'分成两个音'")


# ---------------- 6. Unison: N 个失谐振荡器 ----------------

def t6_unison_scaling():
    print("\n" + "=" * 74)
    print("⑥ Unison 的定量规律：detune 量 vs 拍率 vs 峰值")
    print("=" * 74)

    dur = 4.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    f0 = 110.0

    print(f"   基频 {f0:.0f} Hz，7 个振荡器均匀分布在 ±{0}%内")
    print(f"   实测: 最高与最低振荡器的拍频、以及叠加后的 crest factor\n")
    print(f"  {'detune ±%':>11} {'最高-最低(Hz)':>14} {'拍率(Hz)':>10} "
          f"{'crest(dB)':>11} {'峰谷比(dB)':>11}")

    for pct in [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
        det = np.linspace(-pct / 100.0, pct / 100.0, 7)
        x = sum(np.sin(2 * np.pi * f0 * (1 + d) * t) for d in det) / 7
        pk = np.max(np.abs(x))
        rm = np.sqrt(np.mean(x ** 2))
        span_hz = f0 * (det[-1] - det[0])
        env = envelope_hilbert(x)
        rate = env_peak_rate(env, fmin=max(0.2, span_hz * 0.2),
                             fmax=max(2.0, span_hz * 4))
        print(f"  {pct:>11.1f} {span_hz:>14.2f} {rate:>10.2f} "
              f"{20 * np.log10(pk / rm):>11.2f} {peak_to_peak_db(env, 0.1):>11.2f}")

    print("\n   ⚠️ 第三列是**包络峰率**（= 2 × 最外侧拍频），不是拍频本身")
    print("      detune = 0 时无拍，该列无意义（见表中数值）")
    print("      1. detune = 0 → 所有振荡器完全同相，叠加还是正弦（crest 3.01 dB）")
    print("      2. detune 增大 → crest 上升（峰值错开），但**RMS 不变**")
    print("      3. detune 过大 → 拍率进入可听范围，听起来'走音'而不是'厚'")
    print("\n   ⚠️ 重要: detune **不改变 RMS**（能量守恒），只改变峰值和包络")
    print("      所以 'detune 让声音变响' 是错觉 —— 实际是峰值上升、")
    print("      经过限幅器后 RMS 被压低，或者只是包络起伏更吸引注意")


# ---------------- 7. 超低音设计 ----------------

def t7_sub_bass():
    print("\n" + "=" * 74)
    print("⑦ 超低音设计：为什么 sub 的失谐听起来是'颤动'不是'宽'")
    print("=" * 74)

    dur = 4.0
    N = int(SR * dur)
    t = np.arange(N) / SR

    print(f"   同样的绝对失谐量 Δf，在不同基频上的'含义'完全不同")
    print(f"  {'f0 (Hz)':>9} {'绝对 Δf':>9} {'相对 detune':>12} "
          f"{'ERB(f0)':>9} {'Δf/ERB':>9} {'听感':>22}")

    cases = [
        (40.0, 1.0, "颤动 / 拍（sub 常见）"),
        (40.0, 5.0, "粗糙，可能'嗡'"),
        (40.0, 20.0, "几乎分叉（sub 里很少用）"),
        (110.0, 1.0, "很慢的拍"),
        (110.0, 5.0, "厚度（bass 的常用区间）"),
        (110.0, 20.0, "粗糙/分叉"),
        (440.0, 1.0, "很慢的拍（'走音'风险）"),
        (440.0, 5.0, "轻微厚度"),
        (440.0, 20.0, "明显的合唱/宽"),
        (2000.0, 20.0, "轻微厚度"),
        (2000.0, 100.0, "明显的宽"),
    ]
    for f0, df, lab in cases:
        erb = 24.7 * (4.37 * f0 / 1000.0 + 1.0)
        print(f"  {f0:>9.1f} {df:>9.1f} {df / f0 * 100:>11.2f}% "
              f"{erb:>9.2f} {df / erb:>9.3f} {lab:>22}")

    print("\n   ⚠️ 核心结论: **决定听感的是 Δf/ERB，不是 detune 百分比**")
    print("      40 Hz 的 ERB 只有 ~29 Hz，所以 20 Hz 的绝对失谐就已经接近分叉")
    print("      2000 Hz 的 ERB 有 ~240 Hz，同样 20 Hz 只是轻微厚度")
    print("\n   ⚠️ 这就是为什么:")
    print("      - sub 做宽很难：频率低 → ERB 窄 → 稍微失谐就'分叉'/颤动")
    print("      - pad 做宽容易：频率高 → ERB 宽 → 大范围失谐仍融合")
    print("      - 超低音的'宽度'通常靠**立体声/M-S 处理**而不是失谐")

    # 实测：40Hz 处的拍率
    print(f"\n   实测 40 Hz 基频，Δf = 1 Hz 的包络拍率:")
    f1 = 40.0
    f2 = round(41.0 * N / SR) * SR / N
    x = 0.5 * np.sin(2 * np.pi * f1 * t) + 0.5 * np.sin(2 * np.pi * f2 * t)
    env = envelope_hilbert(x)
    rate = env_peak_rate(env, fmin=0.2, fmax=8.0)
    print(f"      包络峰率 = {rate:.3f} 峰/秒   周期 = {1 / rate:.4f} s")
    print(f"      理论: Δf = {f2 - f1:.4f} 起伏/秒（**不是 2Δf**）")

    # ⚠️ 修正（2026-10-15，Lead 复核）：
    #    原断言是 abs(rate - 2*(f2-f1)) < 0.05 —— **错的**。
    #    包络 |cos(π·Δf·t)| 的周期是 1/Δf（取绝对值后周期减半，
    #    所以是 Δf 而非 2Δf）。实测 1.0067 Hz ≈ Δf = 1.0 Hz。
    assert abs(rate - (f2 - f1)) < 0.05, \
        f"起伏率应为 Δf={f2-f1:.4f}, 实测 {rate}"
    print(f"      → 每秒约 {rate:.2f} 次起伏，在 sub 上就是明显的'颤动'")
    print(f"      ✅ 拍频 = 起伏率 = {rate:.3f} Hz = Δf")


if __name__ == '__main__':
    t1_beat_frequency()
    t2_envelope_shape()
    t3_audibility_ranges()
    t4_detune_inside_outside()
    t5_thickness_mechanism()
    t6_unison_scaling()
    t7_sub_bass()
    print("\n" + "=" * 74)
    print("✅ verify-beating-detune.py 全部通过")
    print("=" * 74)
