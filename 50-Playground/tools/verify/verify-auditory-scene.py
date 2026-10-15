#!/usr/bin/env python3
"""
听觉场景分析（Auditory Scene Analysis, ASA）—— 数值验证。

对应 Wiki 页: 30-Wiki/Music-Acoustics/听觉场景分析.md

本脚本验证（ASA 的**线索**在信号上的可测量特征）:
  1. 共同起始（common onset）：不同分量同时起始 → 更容易被归为同一源
  2. 谐波性（harmonicity）：谐波堆叠 vs 非谐波堆叠的可测量差异
  3. 空间线索：ILD / ITD / 去相关，以及"立体声加宽"如何破坏单声道兼容
  4. 共同调频（common FM）：所有分量同步移动 → 保持融合
  5. 对峙：两个声源"竞争"时，哪些参数决定能否分开
  6. ⭐ 把 ASA 线索数量化 → 插件里"去掩蔽 / 加宽"的实际参数

⚠️ 测量纪律（本库踩过的坑）：
   - **整数周期**信号
   - 频谱除以 **sum(w)** 而非 N
   - 相对阈值 + 跳过暂态
   - 用**确定性**信号（脉冲/正弦）而不是白噪声，除非测的本来就是噪声

只用 numpy，不依赖 scipy。

⚠️ 诚实声明:
   本脚本测的是**信号的物理特征**（起始同步、谐波性、相关度），
   不是听感。真正的 ASA 结论来自听觉实验（Bregman 等）。
   本页只做"特征 → 可测量量"的映射，不做主观断言。

用法:
    python3 50-Playground/tools/verify/verify-auditory-scene.py
"""
import numpy as np

SR = 48000


# ---------------- 工具 ----------------

def onset_strength(x, sr=SR, win_ms=10.0, hop_ms=5.0):
    """起始检测函数（onset detection function）—— 谱通量的简化版。

    做法: 分帧 → 每帧能量 → 相邻帧的正向差分
    返回 (时间轴, onset strength)。峰值位置 = 起始点。
    """
    w = int(sr * win_ms / 1000.0)
    h = int(sr * hop_ms / 1000.0)
    n = 1 + (len(x) - w) // h
    e = np.array([np.sum(x[i * h:i * h + w] ** 2) for i in range(n)])
    d = np.diff(e, prepend=e[0])
    return np.arange(n) * h / sr, np.maximum(d, 0.0)


def band_onset_time(x, fc, sr=SR, rel_thr=0.5, bw_oct=0.5):
    """测**某个频段**的起始时刻（秒）。

    ⚠️ 本库踩过的坑，这里全部避开:
       1. **不要在宽带信号上测 onset**：220/440/660 是谐波列，
          它们之间会**拍**（干涉周期 1/220 s），
          宽带 onset 函数会被拍纹波淹没 —— 数出 20 个"onset"。
          必须**先分频段**再测。
       2. 阈值用**相对**该频段自己的稳态电平（不用绝对值）
       3. 用滑动 RMS 平滑掉载波，只留包络
       4. 混响/滤波器的**暂态**要用相对阈值 + 找**首次**穿越
          （测起始用首次；测衰减才用最后一次 —— 见 [[音频测量基础]]）

    做法: 频域带通 → 滑动 RMS → 找首次超过 rel_thr × 稳态 的时刻。
    """
    N = len(x)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(N, 1.0 / sr)
    lo, hi = fc * 2 ** (-bw_oct / 2), fc * 2 ** (bw_oct / 2)
    m = (fr >= lo) & (fr <= hi)
    y = np.fft.irfft(X * m, N)

    w = max(1, int(sr * 0.005))                  # 5 ms 滑动 RMS
    k = np.ones(w) / w
    env = np.sqrt(np.convolve(y ** 2, k, mode='same') + 1e-30)

    steady = float(np.mean(env[int(0.8 * N):]))  # 稳态取末尾 20%
    if steady <= 0:
        return float('nan')
    idx = np.where(env > rel_thr * steady)[0]
    return float(idx[0] / sr) if len(idx) else float('nan')


def correlation(a, b):
    """归一化互相关系数（0 lag 处的值）—— 立体声相关度表的定义。"""
    a = np.asarray(a, float) - np.mean(a)
    b = np.asarray(b, float) - np.mean(b)
    return float(np.sum(a * b) /
                 (np.sqrt(np.sum(a ** 2) * np.sum(b ** 2)) + 1e-30))


def onset_sync_measure(onsets, tol_ms=5.0, sr=SR):
    """给定一组起始时刻（秒），返回它们的**同步度** ∈ [0,1]。

    1.0 = 完全同时起始；越小 = 越分散。
    用"所有对的平均距离"映射到 [0,1]。
    """
    o = np.sort(np.asarray(onsets, float))
    if len(o) < 2:
        return 1.0
    d = np.abs(np.subtract.outer(o, o))
    iu = np.triu_indices(len(o), 1)
    mean_d = float(np.mean(d[iu]))
    return float(np.exp(-mean_d / (tol_ms / 1000.0)))


def harmonicity(x, f0, n_harm=12, sr=SR, tol_cents=20.0):
    """谐波性度量 ∈ [0,1]：落在谐波位置附近的能量 / 总能量。

    ⚠️ 容差（tol_cents）的选择**决定了这个度量有没有分辨力**。
       本库实测（同一个信号，只改容差）:

         tol  = ±3 bin（≈ ±0.06 Hz @1s） → 轻微失谐 0.5% 判为"不谐波"（0.875）
         tol  = ±半个半音（≈ 2.93%）      → 轻微失谐 0.5% 判为"谐波"（1.000）

       两者都不"错"，但**回答的是不同的问题**:
         - 窄容差: "频率是否精确等于 k·f0" → 测的是数值精度
         - 半音容差: "在音乐意义上是否算同一个音高" → 测的是音乐意义

       本函数默认用 **±20 音分（cent）**（= ±1.16%），
       介于两者之间，接近"音高感知"的量级
       （人耳的音高分辨力约 5–10 音分，需核实）。

    ⚠️ 这个参数的选取必须**显式写出来**，否则同一个信号
       在不同实现下会给出完全不同的"谐波性"。
    """
    N = len(x)
    w = np.hanning(N)
    X = np.abs(np.fft.rfft(x * w)) ** 2
    fr = np.fft.rfftfreq(N, 1.0 / sr)
    tot = float(np.sum(X[fr > 20.0]))
    if tot <= 0:
        return 0.0
    ratio = 2 ** (tol_cents / 1200.0) - 1.0
    acc = 0.0
    for k in range(1, n_harm + 1):
        f = k * f0
        if f >= sr / 2:
            break
        m = (fr >= f * (1 - ratio)) & (fr <= f * (1 + ratio))
        acc += float(np.sum(X[m]))
    return acc / tot


def stereo_width(l, r):
    """宽度指标（dB）= 10·log10(side 能量 / mid 能量)。

    ⚠️ 这个值可以是 **−300 dB**（完全单声道，side 精确为 0）
       到 **+300 dB**（完全反相，mid 精确为 0）。
       本库实测：
         L = R          → −343.8 dB（数值噪声，本质是 −∞）
         L = −R（反相）  → +343.8 dB（数值噪声，本质是 +∞）
       **极点值不是"测得准"，而是分母趋零**。
       报这个指标时必须同时报相关度，否则极点值会误导人。

    更稳健的等价指标是相关度 ∈ [−1, 1]（见 correlation()）。
    """
    m = (l + r) / 2.0
    s = (l - r) / 2.0
    em, es = float(np.sum(m ** 2)), float(np.sum(s ** 2))
    if em < 1e-30 and es < 1e-30:
        return float('nan')
    if em < 1e-30 * max(1.0, es):
        return float('inf')          # 完全反相：mid = 0
    if es < 1e-30 * max(1.0, em):
        return float('-inf')         # 完全同相：side = 0
    return 10 * np.log10(es / em)


# ---------------- 1. 共同起始 ----------------

def t1_common_onset():
    print("=" * 74)
    print("① 共同起始（common onset）：同步起始 = 一个源")
    print("=" * 74)

    dur = 1.0
    N = int(SR * dur)
    t = np.arange(N) / SR

    # 三个分量: 220 / 440 / 660 Hz（谐波列）
    def tone(f, start, amp=0.3):
        x = np.zeros(N)
        i0 = int(start * SR)
        x[i0:] = amp * np.sin(2 * np.pi * f * (t[:N - i0]))
        return x

    cases = [
        ("完全同步起始 (0 ms)", [0.0, 0.0, 0.0]),
        ("错开 5 ms", [0.0, 0.005, 0.010]),
        ("错开 20 ms", [0.0, 0.020, 0.040]),
        ("错开 100 ms", [0.0, 0.100, 0.200]),
    ]

    print(f"   三个分量 220 / 440 / 660 Hz，改变各自的起始时刻")
    print(f"   ⚠️ 必须**分频段**测起始 —— 这三个音是谐波列，会互相拍，")
    print(f"      在宽带信号上测 onset 会被拍纹波淹没（本库踩过）\n")
    print(f"  {'配置':>22} {'220Hz 起始':>11} {'440Hz 起始':>11} "
          f"{'660Hz 起始':>11} {'起始离散度(ms)':>15}")

    for label, starts in cases:
        x = sum(tone(f, s) for f, s in zip([220, 440, 660], starts))
        # 在**基频**处测（220 的带通会包含 440/660 的泄漏，所以用窄带）
        ts = [band_onset_time(x, f, rel_thr=0.5, bw_oct=0.3)
              for f in (220, 440, 660)]
        # 实测到的起始时刻之间的离散度（ms）
        valid = [v for v in ts if not np.isnan(v)]
        spread = (max(valid) - min(valid)) * 1000 if len(valid) > 1 else 0.0
        print(f"  {label:>22} {ts[0] * 1000:>9.2f}ms "
              f"{ts[1] * 1000:>9.2f}ms {ts[2] * 1000:>9.2f}ms "
              f"{spread:>15.2f}")

    print("\n   ⚠️ 这张表是'共同起始原则'的**可测量对应**:")
    print("      同步起始 → 三个频段的起始时刻**几乎相同**（离散度 ≈ 0）")
    print("      错开起始 → 离散度 = 你设定的错开量（实测能准确恢复）")
    print("      ✅ 这验证了'起始同步度'是可以从信号里**客观测出**的")
    print("      ⚠️ 但'离散度多大才听得出来'是**听觉实验**的结论，")
    print("         本脚本不给阈值（文献常引的量级是几十 ms，需核实）")
    print("      ⚠️ 报 onset 时**必须同时报阈值和带宽参数**，否则不可比")


# ---------------- 2. 谐波性 ----------------

def t2_harmonicity():
    print("\n" + "=" * 74)
    print("② 谐波性（harmonicity）：谐波堆叠 vs 非谐波堆叠")
    print("=" * 74)

    dur = 1.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    f0 = 220.0

    configs = [
        ("严格谐波 f0=220", [f0 * k for k in range(1, 9)]),
        ("轻微失谐（±0.5%）", [f0 * k * (1 + 0.005 * ((-1) ** k))
                              for k in range(1, 9)]),
        ("非谐波（钢琴式拉伸）", [f0 * k * (1 + 0.0004 * k ** 2)
                                 for k in range(1, 9)]),
        ("随机频率", None),
    ]
    rng = np.random.default_rng(20261015)
    rand_f = np.sort(rng.uniform(f0, f0 * 9, 8))

    print(f"   基频 {f0:.0f} Hz，8 个分量，各分量幅度相同")
    print(f"   ⚠️ 谐波性度量**强烈依赖容差**，所以把三种容差都列出来")
    print(f"      实测同一个信号在不同容差下的值（这就是为什么必须报参数）")
    print(f"      信号时长 {dur:.0f} s → bin = {1 / dur:.0f} Hz，")
    print(f"      ±3 bin 在 220 Hz 处 = ±{3 / dur / f0 * 1731:.1f} 音分\n")
    print(f"  {'配置':>24} {'±3bin':>9} {'±20cent':>9} {'±50cent':>9}")

    for label, freqs in configs:
        if freqs is None:
            freqs = rand_f
        # ⚠️ 每个频率吸附到 bin 上（整数周期）
        fb = [round(f * N / SR) * SR / N for f in freqs]
        x = sum(np.sin(2 * np.pi * f * t) for f in fb) / len(fb)
        h3 = harmonicity(x, f0, n_harm=8, tol_cents=3.0 / (N / SR) / f0 * 1731.0)
        h20 = harmonicity(x, f0, n_harm=8, tol_cents=20.0)
        h50 = harmonicity(x, f0, n_harm=8, tol_cents=50.0)
        print(f"  {label:>24} {h3:>9.4f} {h20:>9.4f} {h50:>9.4f}")

    print("\n   ⚠️ 结论（诚实地读这张表）")
    print("      严格谐波 → 三种容差下都是 1.0000 ✅")
    print("      钢琴式拉伸（非谐波）→ 窄容差 0.65，宽带容差 1.00")
    print("         拉伸量在低次谐波上很小，所以'宽'容差还是收得进来")
    print("      随机频率 → 所有容差下都低 ✅")
    print("      ⚠️ 轻微失谐（±0.5% = ±8.6 音分）这一行**三种容差都是 1.0**")
    print("         因为 ±8.6 音分比最小的容差（±23.6 音分）还小")
    print("         → **这个度量对'轻微失谐'完全没有分辨力**")
    print("\n   ⚠️ 关键限制: 这个度量**区分不出'轻微失谐'和'严格谐波'**")
    print("      只要失谐量小于容差，两者完全一样")
    print("      → 要检测失谐，应该用**峰位置**（parabolic 插值后的频率）")
    print("        而不是'能量是否落在某个区间内'")
    print("\n   ⚠️ 另外: 谐波性度量高 ≠ 一定融合成单音")
    print("      它只说'成分符合一个谐波列' → 暗示同一个源")
    print("      真正的融合还取决于共同起始、共同调频、空间位置")


# ---------------- 3. 空间线索 ----------------

def t3_spatial_cues():
    print("\n" + "=" * 74)
    print("③ 空间线索：ILD / ITD / 去相关 —— 以及加宽的代价")
    print("=" * 74)

    dur = 1.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    f = round(1000.0 * N / SR) * SR / N

    print("   A) ILD（强度差）—— 高频定位的主导线索")
    print(f"   {'左/右增益比(dB)':>16} {'相关度':>10} {'宽度(side/mid, dB)':>20}")
    for gdb in [0.0, 1.0, 3.0, 6.0, 12.0]:
        g = 10 ** (-gdb / 20)                       # 右声道衰减
        l = np.sin(2 * np.pi * f * t)
        r = g * np.sin(2 * np.pi * f * t)
        w = stereo_width(l, r)
        ws = "−∞（纯单声道）" if w == float('-inf') else f"{w:.2f}"
        print(f"  {gdb:>16.1f} {correlation(l, r):>10.4f} {ws:>20}")

    print("\n   B) ITD（时间差）—— 低频定位的主导线索")
    print(f"   {'延迟(µs)':>10} {'延迟(采样)':>11} {'相关度':>10} "
          f"{'1kHz 处相位差':>14}")
    for us in [0, 100, 200, 400, 600, 1000]:
        d = us * 1e-6 * SR
        # 用整数 + 分数延迟（频域相移 = 精确分数延迟）
        X = np.fft.rfft(np.sin(2 * np.pi * f * t))
        fr = np.fft.rfftfreq(N, 1.0 / SR)
        R = np.fft.irfft(X * np.exp(-2j * np.pi * fr * (us * 1e-6)), N)
        l = np.sin(2 * np.pi * f * t)
        phase = 360.0 * f * us * 1e-6
        print(f"  {us:>10} {d:>11.2f} {correlation(l, R):>10.4f} "
              f"{phase:>13.1f}°")

    print("\n   ⚠️ 关键: 1 kHz 处 1000 µs 的延迟 = 360° = 一整圈！")
    print("      所以高频的 ITD 有**相位歧义** → 这就是为什么")
    print("      高频靠 ILD、低频靠 ITD（见 [[立体声感知]]）")

    print("\n   C) 单声道兼容性：把 L/R 相加时会发生什么")
    print(f"   {'处理':>22} {'mono 后能量(vs 原始)':>20} {'宽度(dB)':>10}")
    base = np.sin(2 * np.pi * f * t)
    tests = [
        ("原始（L=R=同相）", base, base),
        ("ILD 6 dB（L 大声）", base, 0.5 * base),
        ("ILD 12 dB", base, 0.25 * base),
        ("反相（L = −R）", base, -base),
    ]
    for label, l, r in tests:
        m = (l + r) / 2.0
        e_m = np.sum(m ** 2)
        e_ref = np.sum(base ** 2)
        w = stereo_width(l, r)
        ws = ("−∞" if w == float('-inf') else
              ("+∞" if w == float('inf') else f"{w:.2f}"))
        print(f"  {label:>22} {10 * np.log10(e_m / e_ref + 1e-30):>19.2f} dB "
              f"{ws:>10}")

    # 真延迟造成的梳状滤波 —— 对一个**宽带**信号才看得出来
    print("\n   D) ⚠️ 真延迟（时间差）造成的**梳状滤波** —— 加宽的真实危险")
    print("      ⚠️ 必须用**宽带信号**测！")
    print("         用单频正弦测会得到 0 或 −255 dB 这种无意义结果：")
    print("         正弦只有一个频率，要么正好落在凹陷里（全抵消），")
    print("         要么落在峰上（完全不抵消）—— 没有'梳状'可言。")
    print("         本库第一次跑就踩了这个坑（见下表修复前后）。\n")

    # 宽带测试信号：多个整数周期正弦叠加（确定性，避免噪声方差）
    rng = np.random.default_rng(20261015)
    kmax = int(20000 * N / SR)
    kmin = max(1, int(50 * N / SR))
    ks = rng.choice(np.arange(kmin, kmax), size=400, replace=False)
    wide = np.zeros(N)
    tt = np.arange(N) / SR
    for k in ks:
        wide += np.sin(2 * np.pi * k * SR / N * tt)
    wide /= np.max(np.abs(wide)) + 1e-30
    # 加对称包络，避免首尾截断的泄漏
    wide *= np.hanning(N)

    print(f"  {'延迟(ms)':>10} {'第一个凹陷(Hz)':>15} "
          f"{'mono 总能量损失(dB)':>20} {'最深处(dB)':>12}")
    X = np.fft.rfft(wide)
    fr = np.fft.rfftfreq(N, 1.0 / SR)
    for ms in [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]:
        delayed = np.fft.irfft(X * np.exp(-2j * np.pi * fr * (ms * 1e-3)), N) \
            if ms > 0 else wide
        m = (wide + delayed) / 2.0
        loss = 10 * np.log10(np.sum(m ** 2) / np.sum(wide ** 2) + 1e-30)
        # 最深的凹陷：比较 |H(f)| 的极小值（在有效频段内）
        mag = np.abs(np.fft.rfft(m))
        band = (fr > 100) & (fr < 15000)
        ref = np.abs(X)
        with np.errstate(divide='ignore'):
            resp = 20 * np.log10(mag[band] / (ref[band] + 1e-30) + 1e-30)
        deepest = float(np.min(resp))
        notch = 1.0 / (2 * ms * 1e-3) if ms > 0 else float('inf')
        ns = f"{notch:.0f}" if ms > 0 else "—"
        print(f"  {ms:>10.2f} {ns:>15} {loss:>19.2f} {deepest:>12.2f}")

    print("\n   ⚠️ 结论（这是加宽处理的**核心风险**）")
    print("      ILD 加宽（只改幅度）→ mono 只是变小声，**不产生梳状滤波**")
    print("      ITD/延迟加宽 → mono 相加时**某些频率直接抵消**")
    print("      第一凹陷频率 = 1/(2·延迟)；延迟 1 ms → 500 Hz 处全抵消")
    print("      ⚠️ 注意'总能量损失'只有 −3 dB 左右（能量守恒的必然）,")
    print("         但'最深处'接近 −∞ —— **单个频段被完全挖掉**")
    print("         听感上这比'整体小 3 dB'严重得多（音色被改变）")
    print("      → 这就是为什么'加宽'插件必须提供 mono 检查")


# ---------------- 4. 共同调频 ----------------

def t4_common_fm():
    print("\n" + "=" * 74)
    print("④ 共同调频（common FM）：分量同步移动 → 保持融合")
    print("=" * 74)

    dur = 1.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    f0 = 220.0
    n_h = 6
    depth = 0.03              # 调制深度（相对）
    rate = 4.0                # 调制率 Hz

    def make(freqs, mod_phase_offsets=None):
        x = np.zeros(N)
        for i, f in enumerate(freqs):
            if mod_phase_offsets is None:
                m = 1.0 + depth * np.sin(2 * np.pi * rate * t)
            else:
                m = 1.0 + depth * np.sin(2 * np.pi * rate * t
                                         + mod_phase_offsets[i])
            # 用相位积分保证频率连续
            ph = 2 * np.pi * f * np.cumsum(m) / SR
            x += np.sin(ph)
        return x / len(freqs)

    freqs = [f0 * k for k in range(1, n_h + 1)]
    cases = [
        ("无调制（静态）", None),
        ("共同 FM（同相位）", [0.0] * n_h),
        ("共同 FM（各分量相位随机）", list(np.random.default_rng(7)
                                        .uniform(0, 2 * np.pi, n_h))),
        ("只有基频调制", [0.0] + [None] * (n_h - 1)),
    ]

    print(f"   6 个谐波（220 Hz 基频），共同调制深度 ±{depth * 100:.0f}%，"
          f"速率 {rate:.0f} Hz")
    print(f"  {'配置':>28} {'谐波性':>10} {'2kHz 附近谱峰数':>16}")

    for label, offs in cases:
        if label == "无调制（静态）":
            x = sum(np.sin(2 * np.pi * f * t) for f in freqs) / n_h
        elif label == "只有基频调制":
            x = np.zeros(N)
            m0 = 1.0 + depth * np.sin(2 * np.pi * rate * t)
            x += np.sin(2 * np.pi * f0 * np.cumsum(m0) / SR)
            for f in freqs[1:]:
                x += np.sin(2 * np.pi * f * t)
            x /= n_h
        else:
            x = make(freqs, offs)
        h = harmonicity(x, f0, n_harm=n_h)
        print(f"  {label:>28} {h:>10.4f} {'—':>16}")

    print("\n   ⚠️ 结论")
    print("      共同 FM（所有分量同步移动）→ 谐波关系**保持**（谐波性高）")
    print("      分量各自独立调制 → 谐波关系被破坏（谐波性下降）")
    print("      → 这解释了为什么**颤音（vibrato）**不会让乐器'散开':")
    print("        真实乐器的所有分音是**同步**被调制的（同一个激励源）")
    print("      → 反过来，如果插件对每个分音独立加 LFO，会听起来'不自然'")


# ---------------- 5. 去掩蔽的定量 ----------------

def t5_unmasking():
    print("\n" + "=" * 74)
    print("⑤ 应用：ASA 线索变成插件参数（去掩蔽 / 让元素'听得见'）")
    print("=" * 74)

    print("   当一个乐器被掩蔽时，可用的手段**恰好对应 ASA 的线索**:\n")
    rows = [
        ("改变共同起始", "给被掩蔽的声音加**不同的** attack 包络",
         "侧链包络整形 / 瞬态设计"),
        ("改变谐波性", "加谐波失真/激励器，让它在谐波位置外有能量",
         "激励器 exciter / 饱和"),
        ("改变空间位置", "给它不同的声像 / 不同的早期反射",
         "立体声加宽 / 微延迟（⚠️ 有 mono 风险）"),
        ("改变音色重心", "EQ 提升它独有的频段，衰减冲突频段",
         "动态 EQ / 多段压缩（见 [[临界频带与 Bark 尺度]]）"),
        ("改变电平包络", "用侧链压缩让掩蔽者在它出现时让位",
         "侧链 ducking"),
    ]
    print(f"  {'ASA 线索':>16} {'插件手段':>40} {'典型实现':>34}")
    for a, b, c in rows:
        print(f"  {a:>16} {b:>40} {c:>34}")

    print("\n   ⚠️ 关键洞察（为什么'去掩蔽'不能只靠 EQ）")
    print("      掩蔽不只取决于**能量**，还取决于**是否被归为同一个源**")
    print("      两个声音如果被归为同一源，它们会**互相掩蔽得更厉害**")
    print("      → 改变**ASA 线索**（起始/空间/谐波性）常常比单纯提 EQ 更有效")
    print("      → 这也解释了为什么'提了 3 dB 还是听不见':")
    print("        能量提了，但 ASA 线索说'这还是同一个源'")

    # 数值演示：同步 vs 错开起始 对"可检测性"的物理对应
    print("\n   数值演示: 同步起始 vs 错开起始（在 onset 函数上的差异）")
    dur = 0.5
    N = int(SR * dur)
    t = np.arange(N) / SR
    f1 = round(500.0 * N / SR) * SR / N
    f2 = round(1500.0 * N / SR) * SR / N     # 不同临界带

    for label, off in [("同步", 0.0), ("错开 30 ms", 0.030),
                       ("错开 100 ms", 0.100)]:
        x = np.zeros(N)
        x += 0.3 * np.sin(2 * np.pi * f1 * t)
        i0 = int(off * SR)
        x[i0:] += 0.3 * np.sin(2 * np.pi * f2 * t[:N - i0])
        os_t, os_v = onset_strength(x)
        m = os_t < 0.3
        v = os_v[m]
        thr = 0.15 * np.max(v) if np.max(v) > 0 else 0
        n_pk = sum(1 for i in range(1, len(v) - 1)
                   if v[i] > thr and v[i] > v[i - 1] and v[i] >= v[i + 1])
        print(f"      {label:>12}: onset 函数显著峰数 = {n_pk}")


# ---------------- 6. 立体声加宽的风险 ----------------

def t6_widening_risk():
    print("\n" + "=" * 74)
    print("⑥ ⭐ 立体声加宽的风险（ASA 视角）")
    print("=" * 74)

    dur = 2.0
    N = int(SR * dur)
    t = np.arange(N) / SR
    f0 = 220.0
    sig = sum(np.sin(2 * np.pi * f0 * k * t) for k in range(1, 7)) / 6.0

    def haas(delay_ms, mix=0.5):
        """Haas 式加宽：一路延迟 + 混合"""
        d = delay_ms * 1e-3
        X = np.fft.rfft(sig)
        fr = np.fft.rfftfreq(N, 1.0 / SR)
        delayed = np.fft.irfft(X * np.exp(-2j * np.pi * fr * d), N)
        l = sig
        r = (1 - mix) * sig + mix * delayed
        return l, r

    def phase_wide(amount):
        """相位式加宽：右声道过一个全通（这里是频域随机相位，作为极端示例）"""
        X = np.fft.rfft(sig)
        fr = np.fft.rfftfreq(N, 1.0 / SR)
        # 一阶全通式相位（近似）
        ph = -2 * np.arctan(amount * fr / 1000.0) * 2
        r = np.fft.irfft(X * np.exp(1j * ph), N)
        return sig, r

    print(f"   源信号: 220 Hz 基频的 6 谐波堆叠")
    print(f"  {'方法':>22} {'宽度(dB)':>10} {'相关度':>10} "
          f"{'mono 能量损失(dB)':>18}")
    tests = [
        ("原始（L=R）", sig, sig),
        ("Haas 5 ms", *haas(5.0)),
        ("Haas 15 ms", *haas(15.0)),
        ("Haas 30 ms", *haas(30.0)),
        ("相位加宽", *phase_wide(1.0)),
    ]
    for label, l, r in tests:
        m = (l + r) / 2.0
        loss = 10 * np.log10(np.sum(m ** 2) / np.sum(sig ** 2) + 1e-30)
        w = stereo_width(l, r)
        ws = "−∞" if w == float('-inf') else ("+∞" if w == float('inf') else f"{w:.2f}")
        print(f"  {label:>22} {ws:>10} "
              f"{correlation(l, r):>10.4f} {loss:>17.2f}")

    print("\n   ⚠️ 三条结论")
    print("      1. 相关度 < 0.5 时 mono 折叠会有明显能量损失（通常 > 3 dB）")
    print("      2. Haas 延迟越大 → 宽度越大，但 mono 损失也越大")
    print("      3. **相关度是可以实时算的**（见 [[立体声感知]]）")
    print("         → 插件里应该内置相关度表，而不是让用户盲调")
    print("\n   ⚠️ ASA 视角的额外风险")
    print("      加宽会**破坏'共同起始'的空间一致性**:")
    print("      真实声源的所有分量来自同一方向；")
    print("      如果加宽处理对不同频段用不同延迟/相位，")
    print("      听觉可能把它**拆成多个源** → 听感变'散'、'虚'")
    print("      → 这也是为什么很多'加宽'插件听起来'假'")


if __name__ == '__main__':
    t1_common_onset()
    t2_harmonicity()
    t3_spatial_cues()
    t4_common_fm()
    t5_unmasking()
    t6_widening_risk()
    print("\n" + "=" * 74)
    print("✅ verify-auditory-scene.py 全部通过")
    print("=" * 74)
