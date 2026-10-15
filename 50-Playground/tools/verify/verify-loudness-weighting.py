#!/usr/bin/env python3
"""
等响曲线与频率加权 —— 数值验证。

对应 Wiki 页: 30-Wiki/Music-Acoustics/等响曲线与频率加权.md

本脚本验证:
  1. ISO 226 公式 (1) 与公式 (2) 的**往返一致性**（互为反函数）
  2. ISO 226 参数表的锚点自检（1kHz / αf / LU / Tf）
  3. 等响曲线的关键数值（不同 phon 下各频率的 SPL）
  4. A/B/C 加权的解析式，以及 1 kHz 归一化自检
  5. K 加权（BS.1770）的解析原型 → 48kHz 双二阶系数
  6. K 加权的频响，以及 -0.691 dB 偏移的来源
  7. phon → sone 的分段公式与连续性

只用 numpy，不依赖 scipy。

参考:
  ISO 226:2003 Table 1 + 公式 (1)(2)（已逐字核对原文 PDF）
  IEC 61672-1 A/B/C 加权解析式
  ITU-R BS.1770-4 K 加权系数

用法:
    python3 50-Playground/tools/verify/verify-loudness-weighting.py
"""
import numpy as np

# ============================================================
# ISO 226:2003 参数表（Table 1，逐项核对过原文）
# ============================================================
ISO_F = np.array([20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400,
                  500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000,
                  6300, 8000, 10000, 12500], float)
ISO_AF = np.array([0.532, 0.506, 0.480, 0.455, 0.432, 0.409, 0.387, 0.367, 0.349,
                   0.330, 0.315, 0.301, 0.288, 0.276, 0.267, 0.259, 0.253, 0.250,
                   0.246, 0.244, 0.243, 0.243, 0.243, 0.242, 0.242, 0.245, 0.254,
                   0.271, 0.301])
ISO_LU = np.array([-31.6, -27.2, -23.0, -19.1, -15.9, -13.0, -10.3, -8.1, -6.2,
                   -4.5, -3.1, -2.0, -1.1, -0.4, 0.0, 0.3, 0.5, 0.0, -2.7, -4.1,
                   -1.0, 1.7, 2.5, 1.2, -2.1, -7.1, -11.2, -10.7, -3.1])
ISO_TF = np.array([78.5, 68.7, 59.5, 51.1, 44.0, 37.5, 31.5, 26.5, 22.1, 17.9,
                   14.4, 11.4, 8.6, 6.2, 4.4, 3.0, 2.2, 2.4, 3.5, 1.7, -1.3, -4.2,
                   -6.0, -5.4, -1.5, 6.0, 12.6, 13.9, 12.3])


def _params(f):
    """把参数表插值到任意频率（对数频率轴）。"""
    lf = np.log(np.asarray(f, float))
    return (np.interp(lf, np.log(ISO_F), ISO_AF),
            np.interp(lf, np.log(ISO_F), ISO_LU),
            np.interp(lf, np.log(ISO_F), ISO_TF))


def spl_from_phon(LN, f):
    """ISO 226:2003 公式 (1)

        Lp = (10/af)·lg(Af) − LU + 94     [dB SPL]
        Af = 4.47e-3·(10^(0.025·LN) − 1.15) + (0.4·10^((Tf+LU)/10 − 9))^af
    """
    af, lu, tf = _params(f)
    Af = (4.47e-3 * (10.0 ** (0.025 * LN) - 1.15)
          + (0.4 * 10.0 ** ((tf + lu) / 10.0 - 9.0)) ** af)
    return (10.0 / af) * np.log10(Af) - lu + 94.0


def phon_from_spl(Lp, f):
    """ISO 226:2003 公式 (2)

        LN = 40·lg(Bf) + 94     [phon]
        Bf = (0.4·10^((Lp+LU)/10 − 9))^af − (0.4·10^((Tf+LU)/10 − 9))^af + 0.005135

    ⚠️ 注意是 (Lp + LU)，不是 (Lp − LU)。
       这一点极易写错（原文档的公式排版在 PDF 里会错位）。
       下面的往返测试会抓到它。
    """
    af, lu, tf = _params(f)
    Bf = ((0.4 * 10.0 ** ((Lp + lu) / 10.0 - 9.0)) ** af
          - (0.4 * 10.0 ** ((tf + lu) / 10.0 - 9.0)) ** af
          + 0.005135)
    return 40.0 * np.log10(np.maximum(Bf, 1e-30)) + 94.0


# ============================================================
# A / B / C 加权（IEC 61672-1 解析式）
# ============================================================
def a_weight_db(f):
    f = np.asarray(f, float); f2 = f * f
    return 20 * np.log10((12194.0 ** 2 * f2 ** 2) /
                         ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) *
                                                     (f2 + 737.9 ** 2)) *
                          (f2 + 12194.0 ** 2))) + 2.00


def b_weight_db(f):
    f = np.asarray(f, float); f2 = f * f
    return 20 * np.log10((12194.0 ** 2 * f2 * f) /
                         ((f2 + 20.6 ** 2) * np.sqrt(f2 + 158.5 ** 2) *
                          (f2 + 12194.0 ** 2))) + 0.17


def c_weight_db(f):
    f = np.asarray(f, float); f2 = f * f
    return 20 * np.log10((12194.0 ** 2 * f2) /
                         ((f2 + 20.6 ** 2) * (f2 + 12194.0 ** 2))) + 0.06


# ============================================================
# K 加权（ITU-R BS.1770 的模拟原型 → 双线性变换）
# ============================================================
def k_shelf_coeffs(fs, f0=1681.974450955533, G=3.999843853973347,
                   Q=0.7071752369554196):
    """K 加权第 1 级：高架滤波器（high-shelf，"头"滤波）"""
    K = np.tan(np.pi * f0 / fs)
    Vh = 10.0 ** (G / 20.0)
    Vb = Vh ** 0.4996667741545416
    a0 = 1.0 + K / Q + K * K
    b = np.array([(Vh + Vb * K / Q + K * K) / a0,
                  2.0 * (K * K - Vh) / a0,
                  (Vh - Vb * K / Q + K * K) / a0])
    a = np.array([1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0])
    return b, a


def k_hp_coeffs(fs, f0=38.13547087602444, Q=0.5003270373238773):
    """K 加权第 2 级：高通"""
    K = np.tan(np.pi * f0 / fs)
    a0 = 1.0 + K / Q + K * K
    b = np.array([1.0, -2.0, 1.0])
    a = np.array([1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0])
    return b, a


def biquad_resp(b, a, fs, f):
    z = np.exp(-2j * np.pi * np.asarray(f, float) / fs)
    return (b[0] + b[1] * z + b[2] * z ** 2) / (a[0] + a[1] * z + a[2] * z ** 2)


def k_weight_db(fs, f):
    b1, a1 = k_shelf_coeffs(fs)
    b2, a2 = k_hp_coeffs(fs)
    H = biquad_resp(b1, a1, fs, f) * biquad_resp(b2, a2, fs, f)
    return 20 * np.log10(np.abs(H))


def lfilter(b, a, x):
    """直接 I 型双二阶（逐采样，和 C++ 实现一致）"""
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for n in range(len(x)):
        v = b[0] * x[n] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1 = x1, x[n]
        y2, y1 = y1, v
        y[n] = v
    return y


# BS.1770-4 公布的 48 kHz 系数（用于交叉验证解析设计）
K_SHELF_48_B = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
K_SHELF_48_A = np.array([1.0, -1.69065929318241, 0.73248077421585])
K_HP_48_B = np.array([1.0, -2.0, 1.0])
K_HP_48_A = np.array([1.0, -1.99004745483398, 0.99007225036621])


# ============================================================
def t1_iso226_roundtrip():
    print("=" * 74)
    print("① ISO 226 公式 (1) ↔ (2) 往返一致性（互为反函数）")
    print("=" * 74)

    # 用表上的精确频点（不做插值）避免引入插值误差
    print(f"  {'f(Hz)':>8} " + " ".join(f"{p:>4}→反算" for p in [20, 40, 60, 80]))
    worst = 0.0
    for f in ISO_F:
        row = []
        for LN in [20, 40, 60, 80]:
            Lp = float(spl_from_phon(LN, f))
            LN_back = float(phon_from_spl(Lp, f))
            worst = max(worst, abs(LN_back - LN))
            row.append(f"{LN_back:>9.4f}")
        print(f"  {f:>8.1f} " + " ".join(row))
    print(f"\n  最大往返误差 = {worst:.4f} phon")
    print("  ⚠️ 不是 0 —— 公式 (2) 是标准刻意给的**近似式**（带 +0.005135 补偿项）")
    assert worst < 0.08, f"往返误差过大: {worst}"
    print("  ✅ 误差 < 0.08 phon（远小于 JND ≈ 1 phon），两个公式可视为互逆")


def t2_iso226_anchors():
    print("\n" + "=" * 74)
    print("② 参数表锚点自检（用标准本身的性质去卡）")
    print("=" * 74)

    i1k = int(np.argmin(np.abs(ISO_F - 1000.0)))
    print(f"  αf(1kHz) = {ISO_AF[i1k]:.3f}    LU(1kHz) = {ISO_LU[i1k]:+.1f} dB")
    assert ISO_AF[i1k] == 0.250 and ISO_LU[i1k] == 0.0
    print("  ✅ LU 在 1 kHz 处为 0（LU 的定义就是在 1 kHz 归一化）")

    # 1 kHz 处：SPL 必须 == phon（等响曲线的定义）—— 但只到 ~0.03 dB 精度
    print("  1 kHz 处 SPL 应等于 phon（这是等响曲线的定义）:")
    worst1k = 0.0
    for LN in [20, 40, 60, 80, 100]:
        got = float(spl_from_phon(LN, 1000.0))
        worst1k = max(worst1k, abs(got - LN))
        print(f"    {LN:>3} phon → {got:>8.4f} dB SPL   (偏差 {got - LN:+.4f} dB)")
    assert worst1k < 0.03, f"1kHz 偏差过大: {worst1k}"
    print(f"  ⚠️ 最大偏差 {worst1k:.4f} dB —— **这是标准公式自带的**，不是实现错误")
    print("     来源: 公式 (1) 的**第一项** 4.47e-3·(10^(0.025·LN) − 1.15)")
    print("           在 1 kHz、LN=40 处 = 4.47e-3 × (10 − 1.15) = 0.039557")
    print("           它不是 0，所以 1 kHz 的 SPL 会比 phon 高约 0.01 dB")
    print("     第二项在 1 kHz 处 = "
          f"{(0.4 * 10.0 ** ((2.4 + 0.0) / 10.0 - 9.0)) ** 0.25:.7f}")
    print("           与公式 (2) 的 +0.005135 只差 3e-7 —— 两个公式靠它对齐")

    print(f"  LU 最大 = {ISO_LU.max():+.1f} dB @ {ISO_F[np.argmax(ISO_LU)]:.0f} Hz")
    print(f"  LU 最小 = {ISO_LU.min():+.1f} dB @ {ISO_F[np.argmin(ISO_LU)]:.0f} Hz")

    # ⚠️ 修正（2026-10-15，Lead 复核）：
    #    原断言是 assert ISO_F[argmax(ISO_LU)] == 800.0 —— **错的**。
    #    实际表里 LU 最大值在 **3150 Hz**（+2.5 dB），不是 800 Hz（+0.5 dB）。
    #    800 Hz 只是低频侧的一个**局部**小峰。
    #    LU 的整体形状：低频很低（-31.6 @20Hz）→ 800Hz 小峰 → 1600Hz 凹陷
    #    → **3150 Hz 最高**（人耳最敏感区）→ 高频再次下降。
    assert ISO_F[np.argmax(ISO_LU)] == 3150.0, "LU 的峰值应在 3150 Hz"
    assert ISO_LU[np.argmin(np.abs(ISO_F - 800.0))] == 0.5, "800Hz 处应为 +0.5"
    print("  ✅ LU 峰值在 3.15 kHz（人耳最敏感区），800 Hz 只是局部小峰")

    print(f"  Tf 最小 = {ISO_TF.min():+.1f} dB @ {ISO_F[np.argmin(ISO_TF)]:.0f} Hz")
    assert ISO_F[np.argmin(ISO_TF)] == 3150.0
    print("  ✅ 听阈最低点在 3.15 kHz（耳道共振区，符合解剖学）")
    print(f"  Tf(20Hz) = {ISO_TF[0]:.1f} dB ← 20 Hz 要这么大声才听得到")
    assert ISO_TF[0] > 70.0

    print(f"  αf 最小 = {ISO_AF.min():.3f} @ {ISO_F[np.argmin(ISO_AF)]:.0f} Hz")
    print("  ✅ αf 在 4–5 kHz 最小（= 该处响度增长最快），低频 αf 接近 0.5")


def t3_contours():
    print("\n" + "=" * 74)
    print("③ 等响曲线关键数值（ISO 226:2003 公式计算，dB SPL）")
    print("=" * 74)

    freqs = np.array([20, 50, 100, 200, 500, 1000, 2000, 3150, 4000, 8000, 12500],
                     float)
    phons = [20, 40, 60, 80, 100]
    print("  绝对声压级（dB SPL）—— 这就是等响曲线本身:")
    print(f"  {'f(Hz)':>8} " + " ".join(f"{p:>8}ph" for p in phons))
    for f in freqs:
        print(f"  {f:>8.0f} " + " ".join(f"{float(spl_from_phon(p, f)):>10.1f}"
                                         for p in phons))

    print("\n  减去 1 kHz 同 phon 的值 → 曲线的'形状'（dB 相对值）:")
    print("  ⚠️ 如果等响曲线是**一族平行线**，这张表每列都应该完全一样")
    print(f"  {'f(Hz)':>8} " + " ".join(f"{p:>8}ph" for p in phons))
    tab = {}
    for f in freqs:
        row = []
        for p in phons:
            d = float(spl_from_phon(p, f)) - float(spl_from_phon(p, 1000.0))
            tab[(f, p)] = d
            row.append(f"{d:>+10.1f}")
        print(f"  {f:>8.0f} " + " ".join(row))

    print("\n  ⚠️ 关键观察：列与列**不相等** → 等响曲线不是平行线")
    for f in [20, 50, 100, 4000, 12500]:
        d40 = tab[(f, 40.0)] if (f, 40.0) in tab else tab[(f, 40)]
        d80 = tab[(f, 80.0)] if (f, 80.0) in tab else tab[(f, 80)]
        print(f"     {f:>6.0f} Hz: 40 phon 需 {d40:+6.1f} dB, 80 phon 需 {d80:+6.1f} dB"
              f"  → 差 {d80 - d40:+5.1f} dB")
    print("     小音量下低频需要**更多**提升 —— 这就是 loudness 按钮的物理依据")


def t4_abc():
    print("\n" + "=" * 74)
    print("④ A / B / C 加权：解析式与归一化自检")
    print("=" * 74)

    for nm, fn in [('A', a_weight_db), ('B', b_weight_db), ('C', c_weight_db)]:
        v = float(fn(1000.0))
        assert abs(v) < 0.01, f"{nm}(1kHz) = {v}"
    print("  ✅ A/B/C 在 1 kHz 处都归一化到 0.00 dB")

    freqs = np.array([10, 20, 31.5, 50, 63, 100, 125, 200, 250, 400, 500, 800,
                      1000, 1250, 2000, 3150, 4000, 5000, 8000, 10000, 12500,
                      16000, 20000], float)
    print(f"\n  {'f(Hz)':>8} {'A(dB)':>9} {'B(dB)':>9} {'C(dB)':>9} {'K(dB)':>9}")
    for hz in freqs:
        print(f"  {hz:>8.1f} {float(a_weight_db(hz)):>+9.2f} "
              f"{float(b_weight_db(hz)):>+9.2f} {float(c_weight_db(hz)):>+9.2f} "
              f"{float(k_weight_db(48000.0, hz)):>+9.2f}")

    fg = np.logspace(1, np.log10(20000), 200000)
    ya = a_weight_db(fg); i = np.argmax(ya)
    print(f"\n  A 加权最大 = {ya[i]:+.2f} dB @ {fg[i]:.0f} Hz（不是 1 kHz！）")
    print(f"  A 加权最小 = {ya.min():+.2f} dB @ {fg[np.argmin(ya)]:.1f} Hz")
    print(f"  50 Hz: A = {float(a_weight_db(50.0)):+.2f}, "
          f"C = {float(c_weight_db(50.0)):+.2f}, "
          f"差 {float(a_weight_db(50.0)) - float(c_weight_db(50.0)):+.2f} dB")
    print("  → A 加权模拟 ~40 phon 等响曲线；C 加权模拟 ~90–100 phon（接近平坦）")


def t5_kweight_coeffs():
    print("\n" + "=" * 74)
    print("⑤ K 加权：解析原型 vs BS.1770-4 公布的 48 kHz 系数")
    print("=" * 74)

    b1, a1 = k_shelf_coeffs(48000.0)
    b2, a2 = k_hp_coeffs(48000.0)
    print("  第 1 级（高架，+4 dB @ 高频，f0 ≈ 1682 Hz）:")
    for nm, got, ref in [('b0', b1[0], K_SHELF_48_B[0]),
                         ('b1', b1[1], K_SHELF_48_B[1]),
                         ('b2', b1[2], K_SHELF_48_B[2]),
                         ('a1', a1[1], K_SHELF_48_A[1]),
                         ('a2', a1[2], K_SHELF_48_A[2])]:
        print(f"    {nm:>3} {got:>22.14f} {ref:>22.14f} {abs(got - ref):>12.2e}")
    print("  第 2 级（高通，f0 ≈ 38.1 Hz）:")
    for nm, got, ref in [('a1', a2[1], K_HP_48_A[1]), ('a2', a2[2], K_HP_48_A[2])]:
        print(f"    {nm:>3} {got:>22.14f} {ref:>22.14f} {abs(got - ref):>12.2e}")

    err = max(np.abs(b1 - K_SHELF_48_B).max(), np.abs(a1 - K_SHELF_48_A).max(),
              np.abs(a2 - K_HP_48_A).max())
    print(f"\n  最大系数误差 = {err:.2e}")
    assert err < 1e-9, f"系数不匹配: {err}"
    print("  ✅ 4 个设计参数（f0/Q/G + 指数 0.49966677…）就能精确重建标准系数")
    print("     ⚠️ 那个 0.4996667741545416 不是 0.5 —— 是标准里的设计常数，别改")


def t6_kweight_response():
    print("\n" + "=" * 74)
    print("⑥ K 加权频响，以及 −0.691 dB 偏移的来源")
    print("=" * 74)

    fs = 48000.0
    b1, a1 = k_shelf_coeffs(fs); b2, a2 = k_hp_coeffs(fs)
    print(f"  {'f(Hz)':>8} {'第1级(高架)':>13} {'第2级(HP)':>11} {'级联':>10}")
    for hz in [20, 30, 50, 100, 200, 500, 997, 1000, 2000, 5000, 10000, 20000]:
        s1 = 20 * np.log10(abs(biquad_resp(b1, a1, fs, hz)))
        s2 = 20 * np.log10(abs(biquad_resp(b2, a2, fs, hz)))
        print(f"  {hz:>8} {s1:>+13.3f} {s2:>+11.3f} {s1 + s2:>+10.3f}")

    gain997 = float(k_weight_db(fs, 997.0))
    print(f"\n  K 加权 @ 997 Hz = {gain997:+.4f} dB")
    print("  BS.1770 响度公式的固定偏移 = −0.691 dB")
    print(f"  → {gain997:+.4f} + (−0.691) = {gain997 - 0.691:+.5f} dB")
    assert abs(gain997 - 0.691) < 0.01
    print("  ✅ −0.691 dB 的来源找到了：它**精确抵消** 997 Hz 处的加权增益")
    print("     所以 997 Hz 正弦（RMS = −20 dBFS）读出来正好是 −20.0 LUFS")
    print("     ⚠️ 这解释了为什么校准信号用 997 Hz 而不是 1000 Hz")


def t7_loudness_numeric():
    print("\n" + "=" * 74)
    print("⑦ 端到端数值：997 Hz 正弦的 LUFS（验证 −0.691 与声道求和）")
    print("=" * 74)

    fs = 48000
    N = 48000 * 4
    f0 = round(997.0 * N / fs) * fs / N      # 落在 bin 上
    t = np.arange(N) / fs
    b1, a1 = k_shelf_coeffs(float(fs)); b2, a2 = k_hp_coeffs(float(fs))

    def lufs_of(x):
        y = lfilter(b2, a2, lfilter(b1, a1, x))
        y = y[fs:]                            # 跳过 1 秒暂态
        return -0.691 + 10 * np.log10(float(np.mean(y ** 2)) + 1e-30)

    # ⚠️ 两种"−20 dBFS"约定，结果差 3.01 dB。必须分别测。
    x_peak = 0.1 * np.sin(2 * np.pi * f0 * t)                     # 峰值 = −20 dBFS
    x_rms = (0.1 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)     # RMS  = −20 dBFS

    print(f"  997 Hz 正弦，时长 4 s，跳过前 1 s 暂态\n")
    print(f"  {'约定':>22} {'峰值(dBFS)':>12} {'RMS(dBFS)':>11} {'LUFS':>9}")
    for label, x in [('峰值 = −20 dBFS', x_peak), ('RMS  = −20 dBFS', x_rms)]:
        pk = 20 * np.log10(np.max(np.abs(x)))
        rm = 20 * np.log10(np.sqrt(np.mean(x ** 2)))
        print(f"  {label:>22} {pk:>12.3f} {rm:>11.3f} {lufs_of(x):>9.3f}")

    lp, lr = lufs_of(x_peak), lufs_of(x_rms)
    print("\n  ⚠️ 四个结论:")
    print(f"     1. 峰值 −20 dBFS 的正弦 → {lp:+.2f} LUFS（不是 −20！差 3.01 dB）")
    print(f"     2. RMS  −20 dBFS 的正弦 → {lr:+.2f} LUFS ✅ 这才是标准的校准条件")
    print("        → BS.1770 的校准约定是 **RMS**（用 997 Hz 正弦）")
    print("        → 说'LUFS 等于 RMS'时，指的是 K 加权后的 RMS，不是采样 RMS")
    print(f"     3. 两者差 {lr - lp:+.3f} dB = 正弦的 crest factor 20·lg(√2)")
    assert abs(lr + 20.0) < 0.05, f"RMS 约定应为 -20 LUFS, 实测 {lr}"
    assert abs((lr - lp) - 3.01) < 0.05, f"crest factor 应为 3.01 dB"

    # 声道数陷阱
    lufs_dual = -0.691 + 10 * np.log10(2 * 10 ** ((lr + 0.691) / 10))
    print(f"     4. 同一信号放两条声道 → {lufs_dual:+.3f} LUFS")
    print(f"        差 {lufs_dual - lr:+.3f} dB —— BS.1770 是**全声道能量和**")
    print("        ⚠️ 这是 LUFS 最著名的陷阱：mono 素材 vs dual-mono 素材测出来差 3 dB")
    assert abs((lufs_dual - lr) - 3.01) < 0.02


def t8_phon_sone():
    print("\n" + "=" * 74)
    print("⑧ phon → sone 的分段公式")
    print("=" * 74)

    def sone_from_phon(LN):
        LN = np.asarray(LN, float)
        return np.where(LN >= 40.0, 2.0 ** ((LN - 40.0) / 10.0),
                        (LN / 40.0) ** 2.642)

    print(f"  {'phon':>7} {'sone':>10} {'局部斜率':>10}")
    prev, prevp = None, None
    for p in [10, 20, 30, 39.9, 40.0, 40.1, 50, 60, 70, 80, 90, 100]:
        s = float(sone_from_phon(p))
        sl = np.nan if prev is None else (s - prev) / (p - prevp)
        print(f"  {p:>7.1f} {s:>10.4f} {sl:>10.4f}")
        prev, prevp = s, p

    lo = float(sone_from_phon(40.0 - 1e-9)); hi = float(sone_from_phon(40.0 + 1e-9))
    print(f"\n  40 phon 处左右极限: {lo:.8f} vs {hi:.8f}  差 {abs(hi - lo):.2e}")
    assert abs(lo - hi) < 1e-6
    print("  ✅ 值连续（1 sone ≡ 40 phon 是定义）")

    h = 1e-6
    d_lo = (float(sone_from_phon(40.0)) - float(sone_from_phon(40.0 - h))) / h
    d_hi = (float(sone_from_phon(40.0 + h)) - float(sone_from_phon(40.0))) / h
    print(f"  左导数 {d_lo:.5f}, 右导数 {d_hi:.5f}, 差 {d_hi - d_lo:+.5f}")
    print("  ⚠️ 值连续但**导数不连续** —— 40 phon 是两段经验的接缝")
    print(f"\n  +10 phon 在 40 phon 以上 = {float(sone_from_phon(50)) / 1.0:.2f} 倍响度（翻倍）")
    print(f"  100 phon = {float(sone_from_phon(100)):.1f} sone = 64 倍响度")


if __name__ == '__main__':
    t1_iso226_roundtrip()
    t2_iso226_anchors()
    t3_contours()
    t4_abc()
    t5_kweight_coeffs()
    t6_kweight_response()
    t7_loudness_numeric()
    t8_phon_sone()
    print("\n" + "=" * 74)
    print("✅ verify-loudness-weighting.py 全部通过")
    print("=" * 74)
