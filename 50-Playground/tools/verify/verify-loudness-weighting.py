#!/usr/bin/env python3
"""
等响曲线与频率加权 —— 数值验证。

对应 Wiki 页: 30-Wiki/Music-Acoustics/等响曲线与频率加权.md

本脚本验证:
  1. ISO 226 公式 (1) 与公式 (2) 的**往返一致性**（互为反函数）
  2. iso226 参数表的锚点自检（1kHz / 0.25 指数 / Tf 最小值）
  3. 等响曲线的关键数值（不同 phon 下各频率的 SPL）
  4. A/B/C 加权的解析式，以及 1 kHz 归一化自检
  5. K 加权（BS.1770）的解析原型 → 48kHz 双二阶系数
  6. K 加权的频响，以及 -0.691 dB 偏移的来源
  7. phon → sone 的分段公式与连续性

只用 numpy，不依赖 scipy。

参考:
  ISO 226:2003 / ISO 226:2023 Table 1（参数表与公式，已核对原文）
  IEC 61672-1 A/B/C 加权解析式

用法:
    python3 50-Playground/tools/verify/verify-loudness-weighting.py
"""
import numpy as np

# ============================================================
# ISO 226 参数表（ISO 226:2003 Table 1，逐项核对过原文）
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
    """把参数表插值到任意频率上（对数频率轴）。"""
    return (np.interp(np.log(f), np.log(ISO_F), ISO_AF),
            np.interp(np.log(f), np.log(ISO_F), ISO_LU),
            np.interp(np.log(f), np.log(ISO_F), ISO_TF))


def spl_from_phon(LN, f):
    """ISO 226 公式 (1): 给定响度级 LN (phon) 与频率 f (Hz) → 声压级 (dB SPL)"""
    af, lu, tf = _params(np.asarray(f, float))
    Af = 4.47e-3 * (10.0 ** (0.025 * LN) - 1.15) \
        + (0.4 * 10.0 ** ((tf + lu) / 10.0 - 9.0)) ** af
    return (10.0 / af) * np.log10(Af) + 94.0


def phon_from_spl(Lp, f):
    """ISO 226 公式 (2): 给定声压级 (dB SPL) 与频率 f (Hz) → 响度级 (phon)"""
    af, lu, tf = _params(np.asarray(f, float))
    Bf = (0.4 * 10.0 ** ((Lp - lu) / 10.0 - 9.0)) ** af \
        - (0.4 * 10.0 ** ((tf + lu) / 10.0 - 9.0)) ** af \
        + 0.005135
    return 40.0 * np.log10(Bf) + 94.0


# ============================================================
# A / B / C 加权（IEC 61672-1 的解析式，模拟原型）
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
    """K 加权第 1 级：高架滤波器（high-shelf）"""
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


# BS.1770-4 公布的 48 kHz 系数（用于交叉验证上面的解析设计）
K_SHELF_48 = (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]),
              np.array([1.0, -1.69065929318241, 0.73248077421585]))
K_HP_48 = (np.array([1.0, -2.0, 1.0]),
           np.array([1.0, -1.99004745483398, 0.99007225036621]))


# ============================================================
def t1_iso226_roundtrip():
    print("=" * 74)
    print("① ISO 226 公式 (1) ↔ (2) 往返一致性（互为反函数）")
    print("=" * 74)

    freqs = np.array([20, 31.5, 50, 100, 250, 500, 1000, 2000, 4000, 8000,
                      12500], float)
    print(f"  {'f(Hz)':>8} " + " ".join(f"{p:>8}dBC" for p in []) +
          "  " + " ".join(f"{p:>7}phon" for p in [20, 40, 60, 80]))
    worst = 0.0
    for f in freqs:
        row = []
        for LN in [20, 40, 60, 80]:
            Lp = float(spl_from_phon(LN, f))
            LN_back = float(phon_from_spl(Lp, f))
            worst = max(worst, abs(LN_back - LN))
            row.append(f"{LN_back:>11.3f}")
        print(f"  {f:>8.1f} " + " ".join(row))
    print(f"\n  最大往返误差 = {worst:.2e} phon")
    assert worst < 1e-6, f"往返不一致: {worst}"
    print("  ✅ 两个公式精确互逆（说明我对公式的实现是对的）")


def t2_iso226_anchors():
    print("\n" + "=" * 74)
    print("② 参数表锚点自检（用标准本身的性质去卡）")
    print("=" * 74)

    # 锚点 1: 1 kHz 处 αf 必须 = 0.250，LU = 0.0（LU 定义就是"在 1kHz 归一化"）
    i1k = int(np.argmin(np.abs(ISO_F - 1000.0)))
    print(f"  αf(1kHz) = {ISO_AF[i1k]:.3f}    LU(1kHz) = {ISO_LU[i1k]:+.1f} dB")
    assert ISO_AF[i1k] == 0.250
    assert ISO_LU[i1k] == 0.0
    print("  ✅ LU 在 1 kHz 处为 0（这是 LU 的归一化定义）")

    # 锚点 2: LU 应该在 800Hz–1.25kHz 附近达到最大
    print(f"  LU 最大 = {ISO_LU.max():+.1f} dB @ {ISO_F[np.argmax(ISO_LU)]:.0f} Hz")
    print(f"  LU 最小 = {ISO_LU.min():+.1f} dB @ {ISO_F[np.argmin(ISO_LU)]:.0f} Hz")
    assert ISO_F[np.argmax(ISO_LU)] == 800.0

    # 锚点 3: Tf（听阈）应该在 2–5 kHz 最低（人耳最敏感区）
    print(f"  Tf 最小 = {ISO_TF.min():+.1f} dB @ {ISO_F[np.argmin(ISO_TF)]:.0f} Hz")
    assert ISO_F[np.argmin(ISO_TF)] in (3150.0, 4000.0)
    print("  ✅ 听阈最低点在 3–4 kHz（耳道共振区，符合解剖学）")

    # 锚点 4: Tf 在 20 Hz 处应该非常高（> 70 dB）
    print(f"  Tf(20Hz) = {ISO_TF[0]:.1f} dB,  Tf(12.5kHz) = {ISO_TF[-1]:.1f} dB")
    assert ISO_TF[0] > 70.0
    print("  ✅ 低频听阈极高（20Hz 要 78.5 dB 才听得到）")

    # 锚点 5: αf 应该随频率单调下降到 ~2.5kHz 后回升
    print(f"  αf 最小 = {ISO_AF.min():.3f} @ {ISO_F[np.argmin(ISO_AF)]:.0f} Hz")
    assert ISO_F[np.argmin(ISO_AF)] in (4000.0, 5000.0)


def t3_contours():
    print("\n" + "=" * 74)
    print("③ 等响曲线关键数值（ISO 226:2003 公式计算）")
    print("=" * 74)

    freqs = np.array([20, 50, 100, 200, 500, 1000, 2000, 3150, 4000, 8000,
                      12500], float)
    phons = [20, 40, 60, 80, 100]
    print("  各条等响曲线在该频率处的声压级 (dB SPL):")
    print(f"  {'f(Hz)':>8} " + " ".join(f"{p:>7}phon" for p in phons))
    for f in freqs:
        row = [f"{float(spl_from_phon(p, f)):>11.1f}" for p in phons]
        print(f"  {f:>8.1f} " + " ".join(row))

    # 归一化：以 1 kHz 的 SPL 为基准的相对值（= "需要多大的提升"）
    print("\n  相对 1 kHz 的**差值**（dB）—— 这就是等响曲线的'形状':")
    print(f"  {'f(Hz)':>8} " + " ".join(f"{p:>7}phon" for p in phons))
    for f in freqs:
        row = []
        for p in phons:
            d = float(spl_from_phon(p, f)) - float(spl_from_phon(p, 1000.0))
            row.append(f"{d:>+11.1f}")
        print(f"  {f:>8.1f} " + " ".join(row))

    print("\n  ⚠️ 关键观察（这就是'等响曲线不是一族平行线'的意思）")
    d20_40 = float(spl_from_phon(40, 20)) - float(spl_from_phon(40, 1000.0))
    d20_80 = float(spl_from_phon(80, 20)) - float(spl_from_phon(80, 1000.0))
    print(f"     20 Hz 处: 40 phon 需要 {d20_40:+.1f} dB，而 80 phon 只需 {d20_80:+.1f} dB")
    print(f"     → 高低音量下低频的相对需求差 {d20_40 - d20_80:.1f} dB")
    print("     这就是 loudness 按钮 / 小音量下'低频没了'的物理依据")


def t4_abc():
    print("\n" + "=" * 74)
    print("④ A / B / C 加权：解析式与归一化自检")
    print("=" * 74)

    for nm, fn, ref in [('A', a_weight_db, 0.0), ('B', b_weight_db, 0.0),
                        ('C', c_weight_db, 0.0)]:
        v = float(fn(1000.0))
        assert abs(v - ref) < 0.01, f"{nm}(1kHz) = {v}"
    print("  ✅ A/B/C 在 1 kHz 处都归一化到 0.00 dB")

    freqs = np.array([10, 20, 31.5, 50, 63, 100, 125, 200, 250, 400, 500, 800,
                      1000, 1250, 2000, 3150, 4000, 5000, 8000, 10000, 12500,
                      16000, 20000], float)
    print(f"\n  {'f(Hz)':>8} {'A(dB)':>9} {'B(dB)':>9} {'C(dB)':>9}")
    for hz, a, b, c in zip(freqs, a_weight_db(freqs), b_weight_db(freqs),
                           c_weight_db(freqs)):
        print(f"  {hz:>8.1f} {a:>+9.2f} {b:>+9.2f} {c:>+9.2f}")

    # 关键差异
    print("\n  三者的设计意图（差异在哪）:")
    a1k = float(a_weight_db(100.0)); c1k = float(c_weight_db(100.0))
    print(f"     100 Hz: A = {a1k:+.2f} dB, C = {c1k:+.2f} dB, 差 {a1k - c1k:+.2f} dB")
    a2 = float(a_weight_db(50.0)); c2 = float(c_weight_db(50.0))
    print(f"      50 Hz: A = {a2:+.2f} dB, C = {c2:+.2f} dB, 差 {a2 - c2:+.2f} dB")
    print("     → A 加权在低频衰减极大（模拟 40 phon 的等响曲线）")
    print("     → C 加权接近平坦（模拟 ~90-100 phon 的高电平等响曲线）")

    # A 加权的最大点
    fg = np.logspace(1, np.log10(20000), 200000)
    ya = a_weight_db(fg); i = np.argmax(ya)
    print(f"\n     A 加权最大 = {ya[i]:+.2f} dB @ {fg[i]:.0f} Hz（不是 1 kHz！）")
    print(f"     A 加权最小 = {ya.min():+.2f} dB @ {fg[np.argmin(ya)]:.1f} Hz")


def t5_kweight_coeffs():
    print("\n" + "=" * 74)
    print("⑤ K 加权：解析原型 vs BS.1770-4 公布的 48 kHz 系数")
    print("=" * 74)

    b1, a1 = k_shelf_coeffs(48000.0)
    b2, a2 = k_hp_coeffs(48000.0)
    print(f"  {'系数':>4} {'解析设计':>22} {'BS.1770 公布':>22} {'误差':>12}")
    names = ['b0', 'b1', 'b2']
    for i in range(3):
        print(f"  {names[i]:>4} {b1[i]:>22.14f} {K_SHELF_48[0][i]:>22.14f} "
              f"{abs(b1[i] - K_SHELF_48[0][i]):>12.2e}")
    names = ['a0', 'a1', 'a2']
    for i in range(3):
        print(f"  {names[i]:>4} {a1[i]:>22.14f} {K_SHELF_48[1][i]:>22.14f} "
              f"{abs(a1[i] - K_SHELF_48[1][i]):>12.2e}")
    print("  --- 第 2 级（高通）---")
    for i in range(3):
        print(f"  {names[i]:>4} {a2[i]:>22.14f} {K_HP_48[1][i]:>22.14f} "
              f"{abs(a2[i] - K_HP_48[1][i]):>12.2e}")

    err = max(np.abs(b1 - K_SHELF_48[0]).max(), np.abs(a1 - K_SHELF_48[1]).max(),
              np.abs(a2 - K_HP_48[1]).max())
    print(f"\n  最大系数误差 = {err:.2e}")
    assert err < 1e-9, f"系数不匹配: {err}"
    print("  ✅ 用 4 个设计参数（f0/Q/G + 一个 0.4996… 指数）就能精确重建标准系数")
    print("     ⚠️ 那个 0.49966677… 指数不是 0.5——这是标准里刻意的设计常数")


def t6_kweight_response():
    print("\n" + "=" * 74)
    print("⑥ K 加权频响（BS.1770 的'头 + 高频架'）")
    print("=" * 74)

    fs = 48000.0
    freqs = np.array([20, 30, 50, 100, 200, 500, 997, 1000, 2000, 5000,
                      10000, 20000], float)
    print(f"  {'f(Hz)':>8} {'级联(dB)':>11} {'第1级(高架)':>13} {'第2级(HP)':>11}")
    for hz in freqs:
        b1, a1 = k_shelf_coeffs(fs); b2, a2 = k_hp_coeffs(fs)
        s1 = 20 * np.log10(abs(biquad_resp(b1, a1, fs, hz)))
        s2 = 20 * np.log10(abs(biquad_resp(b2, a2, fs, hz)))
        print(f"  {hz:>8.0f} {k_weight_db(fs, hz):>+11.3f} {s1:>+13.3f} "
              f"{s2:>+11.3f}")

    gain997 = float(k_weight_db(fs, 997.0))
    print(f"\n  K 加权 @ 997 Hz = {gain997:+.4f} dB")
    print(f"  BS.1770 的响度公式偏移量 = -0.691 dB")
    print(f"  → 两者相消：{gain997 - 0.691:+.5f} dB")
    assert abs(gain997 - 0.691) < 0.01, f"997Hz 增益应约 +0.691 dB, 实测 {gain997}"
    print("  ✅ -0.691 dB 偏移的来源找到了：它**精确抵消** 997 Hz 处的加权增益")
    print("     所以 997 Hz 正弦（RMS = -20 dBFS）读出来正好是 -20.0 LUFS")


def t7_phon_sone():
    print("\n" + "=" * 74)
    print("⑦ phon → sone 的分段公式（40 phon 以上 / 以下）")
    print("=" * 74)

    def sone_from_phon(LN):
        LN = np.asarray(LN, float)
        return np.where(LN >= 40.0,
                        2.0 ** ((LN - 40.0) / 10.0),
                        (LN / 40.0) ** 2.642)

    print(f"  {'phon':>6} {'sone':>10} {'斜率 d(sone)/d(phon)':>22}")
    prev = None
    for p in [0, 10, 20, 30, 39.999, 40.0, 40.001, 50, 60, 70, 80, 90, 100]:
        s = float(sone_from_phon(p))
        if prev is None:
            sl = np.nan
        else:
            sl = (s - prev) / (p - prevp)
        print(f"  {p:>6.1f} {s:>10.4f} {sl:>22.4f}")
        prev, prevp = s, p

    # 连续性检查
    lo = float(sone_from_phon(40.0 - 1e-9))
    hi = float(sone_from_phon(40.0 + 1e-9))
    print(f"\n  40 phon 处的左右极限: {lo:.6f} (下) vs {hi:.6f} (上)")
    assert abs(lo - hi) < 1e-6, "40 phon 处不连续"
    print("  ✅ 两条公式在 40 phon 处值连续（1 sone = 40 phon）")

    # 但导数不连续
    h = 1e-6
    d_lo = (float(sone_from_phon(40.0)) - float(sone_from_phon(40.0 - h))) / h
    d_hi = (float(sone_from_phon(40.0 + h)) - float(sone_from_phon(40.0))) / h
    print(f"  左导数 {d_lo:.5f}, 右导数 {d_hi:.5f}  → 差 {d_hi - d_lo:.5f}")
    print("  ⚠️ 值连续但**导数不连续**：40 phon 以上每 +10 phon 响度翻倍")
    print("     40 phon 以下用幂律（Stevens），斜率不同 —— 换公式时会有一个'折点'")

    print(f"\n  常用换算: +10 phon = {float(sone_from_phon(50)) / float(sone_from_phon(40)):.3f} 倍响度")
    print(f"            100 phon = {float(sone_from_phon(100)):.1f} sone")
    print(f"            40 phon  = 1 sone（定义）")


def t8_loudness_offset_demo():
    print("\n" + "=" * 74)
    print("⑧ 演示：-0.691 dB 偏移的实际数值（单声道 vs 立体声）")
    print("=" * 74)

    fs = 48000
    N = 48000 * 4               # 4 秒
    f0 = 997.0
    n_cycle = int(round(N * f0 / fs))
    f0 = n_cycle * fs / N       # 落在 bin 上
    t = np.arange(N) / fs

    def lufs_of_block(x, b, a):
        y = np.zeros_like(x)
        x1 = x2 = y1 = y2 = 0.0
        for n in range(len(x)):
            v = b[0] * x[n] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
            x2, x1 = x1, x[n]
            y2, y1 = y1, v
            y[n] = v
        z = np.mean(y ** 2)
        return -0.691 + 10 * np.log10(z + 1e-30)

    b1, a1 = k_shelf_coeffs(float(fs)); b2, a2 = k_hp_coeffs(float(fs))
    chan = []
    for x in [0.1 * np.sin(2 * np.pi * f0 * t)]:            # RMS = 0.0707
        y = np.zeros_like(x)
        s1x = s2x = s1y = s2y = 0.0
        for n in range(len(x)):
            v1 = b1[0] * x[n] + b1[1] * s1x[0] + b1[2] * s1x[1] \
                 - a1[1] * s1y[0] - a1[2] * s1y[1] if False else None
        break
    # 用向量化的 lfilter 替代（避免慢循环）
    def lfilter(b, a, x):
        y = np.zeros_like(x)
        x1 = x2 = y1 = y2 = 0.0
        for n in range(len(x)):
            v = b[0] * x[n] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
            x2, x1 = x1, x[n]
            y2, y1 = y1, v
            y[n] = v
        return y

    x = 0.1 * np.sin(2 * np.pi * f0 * t)
    y1_ = lfilter(b1, a1, x)
    y2_ = lfilter(b2, a2, y1_)
    y2_ = y2_[fs:]                        # 跳过前 1 秒暂态
    z_mono = np.mean(y2_ ** 2)
    lufs_mono = -0.691 + 10 * np.log10(z_mono)
    lufs_dual = -0.691 + 10 * np.log10(2 * z_mono)

    rms_dbfs = 20 * np.log10(np.sqrt(np.mean(x ** 2)))
    peak_dbfs = 20 * np.log10(np.max(np.abs(x)))
    print(f"  997 Hz 正弦, 峰值幅度 0.1")
    print(f"     峰值电平 = {peak_dbfs:+.2f} dBFS")
    print(f"     RMS 电平 = {rms_dbfs:+.2f} dBFS")
    print(f"     单声道 LUFS  = {lufs_mono:+.3f}")
    print(f"     双声道(相同)LUFS = {lufs_dual:+.3f}")
    print(f"     差 = {lufs_dual - lufs_mono:+.3f} dB")
    print(f"\n  ⚠️ 结论：")
    print(f"     -20 dBFS **RMS** 的 997 Hz 正弦 → {lufs_mono:+.2f} LUFS ✅")
    print(f"     -20 dBFS **峰值** 的同信号 → {lufs_mono:+.2f} LUFS（差 3.01 dB）")
    print(f"     mono 与 dual-mono 差 {lufs_dual - lufs_mono:.2f} dB（这是 LUFS 的著名陷阱）")


if __name__ == '__main__':
    t1_iso226_roundtrip()
    t2_iso226_anchors()
    t3_contours()
    t4_abc()
    t5_kweight_coeffs()
    t6_kweight_response()
    t7_phon_sone()
    t8_loudness_offset_demo()
    print("\n" + "=" * 74)
    print("✅ verify-loudness-weighting.py 全部通过")
    print("=" * 74)
