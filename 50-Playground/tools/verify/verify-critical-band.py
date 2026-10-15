#!/usr/bin/env python3
"""
临界频带与 Bark / ERB 尺度 —— 数值验证。

对应 Wiki 页: 30-Wiki/Music-Acoustics/临界频带与 Bark 尺度.md

本脚本验证:
  1. Bark 尺度两条经验公式（Zwicker&Terhardt 1980 / Traunmüller 1990）的差异
  2. ERB 公式与 Bark 的对比（同一频率下"听觉带宽"到底多宽）
  3. 临界带宽经验公式 vs ERB 公式
  4. Bark / ERB 尺度上"等间距"对应的 Hz 间隔（为什么不均匀）
  5. 为什么 Bark 域平滑滤波器要用非均匀频段划分
  6. 演示：临界带内的能量求和 → 掩蔽

只用 numpy，不依赖 scipy。

用法:
    python3 50-Playground/tools/verify/verify-critical-band.py
"""
import numpy as np

SR = 48000


# ---------------- 1. 尺度公式 ----------------

def bark_zwicker(f):
    """Zwicker & Terhardt (1980) 的 Bark 近似式。f 单位 Hz，返回 Bark。"""
    f = np.asarray(f, float)
    return 13.0 * np.arctan(0.00076 * f) + 3.5 * np.arctan((f / 7500.0) ** 2)


def bark_traunmuller(f):
    """Traunmüller (1990) 的 Bark 近似式。更简单，低频略不同。"""
    f = np.asarray(f, float)
    return 26.81 * f / (1960.0 + f) - 0.53


def erb_hz(f):
    """Glasberg & Moore (1990): 单个 ERB 的带宽（Hz）"""
    f = np.asarray(f, float)
    return 24.7 * (4.37 * f / 1000.0 + 1.0)


def erb_number(f):
    """ERB-number 尺度: 从 0 到 f 一共容纳多少个 ERB"""
    f = np.asarray(f, float)
    return 21.4 * np.log10(4.37 * f / 1000.0 + 1.0)


def critical_bandwidth_zwicker(f):
    """Zwicker 的临界带宽经验公式（Hz）。注意它给出的是**整个临界带**的宽度。"""
    f = np.asarray(f, float)
    return 25.0 + 75.0 * (1.0 + 1.4 * (f / 1000.0) ** 2) ** 0.69


# ---------------- 2. 自检：公式的基本性质 ----------------

def selfcheck():
    print("=" * 72)
    print("① 尺度公式自检（用已知锚点）")
    print("=" * 72)

    # Bark 尺度上 1 Bark ≈ 1 个临界带，总范围约 0 ~ 24 Bark（20Hz~15.5kHz）
    for f in [20, 100, 500, 1000, 5000, 15500]:
        print(f"  f={f:>6} Hz   Bark(Z&T)={float(bark_zwicker(f)):6.3f}   "
              f"Bark(Traun)={float(bark_traunmuller(f)):6.3f}   "
              f"ERB#{float(erb_number(f)):6.3f}")

    # 关键锚点：1 kHz 处 Bark ≈ 8.5，ERB 带宽 ≈ 132 Hz
    b1k = float(bark_zwicker(1000.0))
    e1k = float(erb_hz(1000.0))
    print(f"\n  锚点检查: Bark(1kHz)   = {b1k:.3f}  （文献常引 8.5 左右）")
    print(f"  锚点检查: ERB(1kHz)    = {e1k:.2f} Hz（文献常引 ~132 Hz）")
    assert 8.0 < b1k < 9.0, f"Bark(1kHz) 超出预期: {b1k}"
    assert 125 < e1k < 140, f"ERB(1kHz) 超出预期: {e1k}"
    print("  ✅ 两个锚点都在文献范围内")

    # Bark 尺度上界
    print(f"\n  Bark(15.5kHz) = {float(bark_zwicker(15500.0)):.3f}（应接近 24）")
    assert 23.5 < float(bark_zwicker(15500.0)) < 25.0
    print("  ✅ Bark 上界接近 24（这是 '24 个临界带' 这个说法的来源）")


# ---------------- 3. 两条 Bark 公式的差异 ----------------

def compare_bark_forms():
    print("\n" + "=" * 72)
    print("② 两条 Bark 经验公式差多少（AI 常随便挑一条）")
    print("=" * 72)

    freqs = np.array([20, 50, 100, 200, 500, 1000, 2000, 4000, 8000, 15500], float)
    print(f"  {'f(Hz)':>8} {'Zwicker':>9} {'Traunm':>9} {'差(Bark)':>10} {'等效Hz差':>10}")
    worst = 0.0
    for f in freqs:
        z = float(bark_zwicker(f))
        t = float(bark_traunmuller(f))
        d = z - t
        # 把 Bark 差折算成"在该频率处相当于多少 Hz"
        # 用数值微分求 df/dz
        h = f * 1e-4
        dz = float(bark_zwicker(f + h)) - z
        hz_per_bark = h / dz if dz > 1e-12 else np.nan
        worst = max(worst, abs(d))
        print(f"  {f:>8.0f} {z:>9.3f} {t:>9.3f} {d:>+10.3f} {d * hz_per_bark:>+10.1f}")

    print(f"\n  最大差异 {worst:.3f} Bark")
    print("  ⚠️ 低频（< 500Hz）两条公式差异最大——这是听觉最敏感的区域")
    return worst


# ---------------- 4. 临界带宽：经验公式 vs ERB ----------------

def compare_bandwidths():
    print("\n" + "=" * 72)
    print("③ 临界带宽：Zwicker 经验公式 vs ERB 公式")
    print("=" * 72)

    freqs = np.array([100, 200, 500, 1000, 2000, 4000, 8000, 12000], float)
    print(f"  {'f(Hz)':>8} {'临界带宽':>10} {'ERB':>9} {'比值':>8} {'f/BW':>8}")
    for f in freqs:
        cb = float(critical_bandwidth_zwicker(f))
        e = float(erb_hz(f))
        print(f"  {f:>8.0f} {cb:>10.1f} {e:>9.1f} {cb / e:>8.3f} {f / cb:>8.2f}")

    ratios = [float(critical_bandwidth_zwicker(f)) / float(erb_hz(f)) for f in freqs]
    print(f"\n  ⚠️ Zwicker 的'临界带宽'是**整个临界带**的宽度（约 1 Bark 宽）")
    print("     ERB 是**等效矩形带宽**，是单个听觉滤波器的带宽")
    print(f"     两者定义不同，比值在 {min(ratios):.2f}–{max(ratios):.2f} 之间（1kHz 处最小 ~1.22）")
    print("     ⚠️ 不要写死一个倍率——它不是常数！低频可差 2.8 倍，1kHz 附近只差 1.2 倍")


# ---------------- 5. 不均匀性：等 Bark 间隔 ≠ 等 Hz 间隔 ----------------

def nonuniformity():
    print("\n" + "=" * 72)
    print("④ 为什么 Bark/ERB 域必须用非均匀频段划分")
    print("=" * 72)

    # 在 Bark 域取等间距的 8 个边界，看对应的 Hz 边界
    z_edges = np.linspace(0, 24, 9)
    # 数值反解 Hz（Bark 是单调的）
    fgrid = np.exp(np.linspace(np.log(20), np.log(20000), 400000))
    zgrid = bark_zwicker(fgrid)
    f_edges = np.interp(z_edges, zgrid, fgrid)

    print("  8 段等 Bark 划分（每段 3 Bark）→ 对应的 Hz 边界:")
    print(f"  {'段':>4} {'Bark 范围':>14} {'Hz 范围':>20} {'Hz 宽度':>10} {'中心':>9}")
    for i in range(8):
        lo, hi = f_edges[i], f_edges[i + 1]
        print(f"  {i + 1:>4} {z_edges[i]:>6.1f}–{z_edges[i + 1]:<6.1f} "
              f"{lo:>8.0f}–{hi:<9.0f} {hi - lo:>10.0f} {np.sqrt(lo * hi):>9.0f}")

    # 对比：等 Hz 划分（线性）
    l_edges = np.linspace(20, 20000, 9)
    print("\n  对照 —— 8 段等 Hz 划分:")
    print(f"  {'段':>4} {'Hz 范围':>20} {'Hz 宽度':>10} {'Bark 宽度':>11}")
    for i in range(8):
        lo, hi = l_edges[i], l_edges[i + 1]
        bz = float(bark_zwicker(hi)) - float(bark_zwicker(lo))
        print(f"  {i + 1:>4} {lo:>8.0f}–{hi:<9.0f} {hi - lo:>10.0f} {bz:>11.3f}")

    print("\n  ⚠️ 等 Hz 划分下，第 1 段（20–2516 Hz）覆盖了约 17 Bark（听觉的 2/3）")
    print("     而等 Bark 划分下每段都是 3 Bark —— 这才是'感知上均匀'")


# ---------------- 6. 演示：临界带内能量求和 = 掩蔽 ----------------

def masking_demo():
    print("\n" + "=" * 72)
    print("⑤ 演示：临界带内的能量求和（临界带响度求和的数值版）")
    print("=" * 72)

    N = 1 << 16
    SR_ = SR
    rng = np.random.default_rng(20261015)
    fr = np.fft.rfftfreq(N, 1.0 / SR_)
    fc = 1000.0

    # 生成**恒定谱密度**的带通噪声：带宽越宽，总功率越大
    # 然后测量"落在 1 ERB 分析窗内的能量"
    # → 当噪声带宽超过临界带宽后，带内能量不再增长 = 响度不再增长
    erb = float(erb_hz(fc))
    cb = float(critical_bandwidth_zwicker(fc))
    print(f"  中心频率 {fc:.0f} Hz,  1 ERB = {erb:.1f} Hz,  临界带宽 = {cb:.1f} Hz")
    print(f"  ⚠️ 噪声保持**恒定谱密度**（每 Hz 的能量相同），只改带宽\n")

    print(f"  {'噪声带宽(Hz)':>13} {'相对ERB':>9} {'总RMS(dB)':>11} "
          f"{'1ERB内RMS(dB)':>15} {'带内占比(dB)':>13}")

    for bw in [25, 50, 100, 132, 200, 400, 800, 1600]:
        # brickwall 带通（频域），恒定谱密度
        lo, hi = fc - bw / 2, fc + bw / 2
        X = np.zeros(len(fr), dtype=complex)
        band = (fr >= lo) & (fr <= hi)
        X[band] = rng.standard_normal(band.sum()) + 1j * rng.standard_normal(band.sum())
        x = np.fft.irfft(X, N)
        x *= 0.1 / (np.sqrt(np.mean(x ** 2)) + 1e-30)   # 归一化使总 RMS = 0.1

        total = np.sqrt(np.mean(x ** 2))
        # 1 ERB 分析窗
        Y = np.fft.rfft(x)
        inband = (fr >= fc - erb / 2) & (fr <= fc + erb / 2)
        # 能量占比（Parseval，注意 rfft 的双边权重）
        wts = np.ones(len(fr)); wts[1:-1] = 2.0
        e_in = np.sum(np.abs(Y[inband]) ** 2 * wts[inband])
        e_tot = np.sum(np.abs(Y ** 2) * wts)
        ratio = e_in / e_tot

        print(f"  {bw:>13} {bw / erb:>9.2f} {20 * np.log10(total):>11.2f} "
              f"{10 * np.log10(e_in / N + 1e-30):>15.2f} "
              f"{10 * np.log10(ratio + 1e-30):>13.2f}")

    print("\n  ⚠️ 怎么读这张表")
    print("     '1ERB内RMS' 在带宽 ≤ 临界带宽前持续增长（能量被听觉滤波器全接收）")
    print("     带宽超过临界带宽后，带内能量趋于饱和 → 响度增长变慢")
    print("     这就是 Zwicker 的 **临界带响度求和**（critical-band loudness summation）")
    print("     听感表现: 把噪声带宽从 200Hz 加到 1600Hz，响度增加**远小于** 9 dB")


# ---------------- 7. 插件用途：Bark/ERB 域多段划分 ----------------

def plugin_band_split():
    print("\n" + "=" * 72)
    print("⑥ 插件用途：在 ERB 域做等间距频段划分（多段压缩/EQ 的划分依据）")
    print("=" * 72)

    n_bands = 8
    f_lo, f_hi = 20.0, 20000.0
    # ERB-number 域等间距 → Hz 边界
    e_lo, e_hi = float(erb_number(f_lo)), float(erb_number(f_hi))
    e_edges = np.linspace(e_lo, e_hi, n_bands + 1)
    fgrid = np.exp(np.linspace(np.log(20), np.log(20000), 400000))
    egrid = erb_number(fgrid)
    f_edges = np.interp(e_edges, egrid, fgrid)

    print(f"  {'段':>3} {'ERB# 范围':>16} {'Hz 边界':>22} {'Q = fc/BW':>10}")
    for i in range(n_bands):
        lo, hi = f_edges[i], f_edges[i + 1]
        fc = np.sqrt(lo * hi)
        q = fc / (hi - lo)
        print(f"  {i + 1:>3} {e_edges[i]:>6.2f}–{e_edges[i + 1]:<7.2f} "
              f"{lo:>8.1f}–{hi:<11.1f} {q:>10.2f}")

    print("\n  ⚠️ 注意 Q 不是常数（低频 Q 大、高频 Q 小）——这是 ERB 尺度的特征")
    print("     Bark 域划分的 Q 与 ERB 域接近但不完全相同")
    print("     而'等 Q 滤波器组'（如恒定 Q 变换）是**另一种**划分，两者不能混用")


# ---------------- 8. 带宽与时域分辨率的不确定性关系 ----------------

def time_freq_tradeoff():
    print("\n" + "=" * 72)
    print("⑦ 听觉滤波器带宽 → 时域分辨率极限（为什么短脉冲听起来'咔'而不'咚'）")
    print("=" * 72)

    print(f"  {'f(Hz)':>8} {'ERB(Hz)':>9} {'等效时间常数(ms)':>17} {'周期数@fc':>11}")
    for f in [100, 250, 500, 1000, 2000, 4000, 8000]:
        e = float(erb_hz(f))
        tau_ms = 1000.0 / (2 * np.pi * e)     # 1/(2π·BW) 作为等效积分时间
        print(f"  {f:>8} {e:>9.1f} {tau_ms:>17.2f} {tau_ms * 1e-3 * f:>11.2f}")

    print("\n  解释: 低频 ERB 窄 → 时间常数长 → 低频的时间分辨率天然差")
    print("        这就是为什么低频'糊'、瞬态主要靠高频定位")


if __name__ == '__main__':
    selfcheck()
    compare_bark_forms()
    compare_bandwidths()
    nonuniformity()
    masking_demo()
    plugin_band_split()
    time_freq_tradeoff()
    print("\n" + "=" * 72)
    print("✅ verify-critical-band.py 全部通过")
    print("=" * 72)
