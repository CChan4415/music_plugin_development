#!/usr/bin/env python3
"""
响度感知与 LUFS —— 数值验证（ITU-R BS.1770 的完整算法）。

对应 Wiki 页: 30-Wiki/Music-Acoustics/响度感知与 LUFS.md

本脚本验证:
  1. K 加权 + 分块均方 → momentary / short-term LUFS
  2. **门限（gating）**：绝对门限 −70 LUFS + 相对门限 −10 LU
  3. 门限的威力：加一段静音，看 integrated LUFS 怎么变
  4. LRA（loudness range）的计算逻辑
  5. True Peak 的过采样检测（4× 线性插值 vs 采样峰值）
  6. 实测：不同 crest factor 信号的 LUFS vs peak vs RMS

⚠️ 本脚本的测量纪律（本库踩过的坑）：
   - 用**整数周期**信号
   - 频谱归一化用 sum(w)，不是 N
   - 时域测量**跳过暂态**
   - 门限用**相对**阈值

只用 numpy，不依赖 scipy。

用法:
    python3 50-Playground/tools/verify/verify-lufs-gating.py
"""
import numpy as np

SR = 48000

# ---------------- K 加权系数（BS.1770-4, 48 kHz）----------------
K_B1 = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
K_A1 = np.array([1.0, -1.69065929318241, 0.73248077421585])
K_B2 = np.array([1.0, -2.0, 1.0])
K_A2 = np.array([1.0, -1.99004745483398, 0.99007225036621])


def biquad(b, a, x):
    """直接 I 型双二阶。状态在每个声道内独立。"""
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for n in range(len(x)):
        v = b[0] * x[n] + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1 = x1, x[n]
        y2, y1 = y1, v
        y[n] = v
    return y


def k_weight(x):
    return biquad(K_B2, K_A2, biquad(K_B1, K_A1, x))


def block_loudness(y, ms=400, hop=None):
    """按 BS.1770 的**分块均方**计算块响度（未加门限）。

    返回 (块起点索引数组, 每块的 mean-square 数组)。

    ⚠️ BS.1770-4 的定义:
       - momentary  = 400 ms 窗，**无重叠**
       - short-term = 3 s 窗，至少 1 s 重叠（常用 1 s 步进）
       实现里普遍用"滑动窗 + 固定步进"，本函数用无重叠 400ms。
    """
    n = int(SR * ms / 1000.0)
    if hop is None:
        hop = n
    starts = np.arange(0, len(y) - n + 1, hop)
    z = np.array([np.mean(y[s:s + n] ** 2) for s in starts])
    return starts, z


def integrate(z_blocks, abs_gate=-70.0, rel_gate_lu=-10.0, verbose=False):
    """BS.1770 的两级门限 integrated loudness。

    第 1 级: 丢掉块响度 < −70 LUFS 的块（绝对门限）
    第 2 级: 用剩下的块算平均响度 Γ，再丢掉 < Γ − 10 LU 的块（相对门限）
    最后对**剩下的块求均方平均**（不是对 dB 平均！）
    """
    # 绝对门限：z 是 mean-square，转成 LUFS 比较
    with np.errstate(divide='ignore'):
        lv = -0.691 + 10 * np.log10(np.maximum(z_blocks, 1e-30))

    keep1 = lv > abs_gate
    if not np.any(keep1):
        return -np.inf, keep1, np.zeros_like(keep1, bool)
    gamma = -0.691 + 10 * np.log10(np.mean(z_blocks[keep1]))

    keep2 = keep1 & (lv > gamma + rel_gate_lu)
    if not np.any(keep2):
        return -np.inf, keep1, keep2
    integrated = -0.691 + 10 * np.log10(np.mean(z_blocks[keep2]))

    if verbose:
        print(f"     绝对门限后保留 {keep1.sum()}/{len(z_blocks)} 块")
        print(f"     Γ（相对门限基准）= {gamma:.3f} LUFS，"
              f"阈值 = {gamma + rel_gate_lu:.3f} LUFS")
        print(f"     相对门限后保留 {keep2.sum()}/{len(z_blocks)} 块")
    return integrated, keep1, keep2


def true_peak(x, os=4):
    """True Peak —— 用**零填充 FFT** 做精确带限过采样（比线性插值准）。

    BS.1770-4 的附件 2 规定用 4× 过采样 + 低通。
    这里用频域零填充实现"理想"带限插值，是上界估计。

    ⚠️ 实际插件里通常用 polyphase FIR（见 [[采样率转换 resampling]]），
       因为 FFT 在大 buffer 上太贵。
    """
    n = len(x)
    N = n * os
    X = np.fft.rfft(x)
    # 零填充到 os 倍长（保持共轭对称）
    Xz = np.zeros(N // 2 + 1, dtype=complex)
    Xz[:len(X)] = X
    y = np.fft.irfft(Xz, N) * os
    return float(np.max(np.abs(y)))


# ============================================================
def t1_calibration():
    print("=" * 74)
    print("① 校准自检：997 Hz 正弦（RMS = −20 dBFS）必须读出 −20.0 LUFS")
    print("=" * 74)

    N = SR * 5
    f0 = round(997.0 * N / SR) * SR / N       # 整数周期
    t = np.arange(N) / SR
    x = (0.1 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)
    y = k_weight(x)

    starts, z = block_loudness(y[SR:])        # 跳过 1 s 暂态
    integ, k1, k2 = integrate(z, verbose=True)
    print(f"\n   f = {f0:.4f} Hz（落在 bin 上）,  RMS = "
          f"{20 * np.log10(np.sqrt(np.mean(x ** 2))):+.3f} dBFS")
    print(f"   integrated LUFS = {integ:+.3f}")
    assert abs(integ + 20.0) < 0.05, f"校准失败: {integ}"
    print("   ✅ 校准通过（这是 BS.1770 的设计目标：997 Hz / −20 dBFS RMS → −20 LUFS）")
    print("   ⚠️ 如果这里读出来不是 −20，先怀疑自己的 K 加权系数或 −0.691 项")


def t2_gating_power():
    print("\n" + "=" * 74)
    print("② 门限的威力：加一段静音，integrated LUFS 几乎不动")
    print("=" * 74)

    N = SR * 20
    f0 = round(997.0 * N / SR) * SR / N
    t = np.arange(N) / SR
    sig = (0.1 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)

    # 造三种素材：纯信号 / 信号+尾部静音 / 信号+中间静音
    cases = [
        ("纯信号 20 s", sig),
        ("信号 10 s + 静音 10 s", np.concatenate([sig[:10 * SR],
                                                  np.zeros(10 * SR)])),
        ("信号 5 s + 静音 10 s + 信号 5 s",
         np.concatenate([sig[:5 * SR], np.zeros(10 * SR), sig[:5 * SR]])),
        ("信号 2 s + 静音 16 s + 信号 2 s",
         np.concatenate([sig[:2 * SR], np.zeros(16 * SR), sig[:2 * SR]])),
    ]

    print(f"   {'素材':>30} {'含门限':>12} {'无门限':>12} {'差':>9}")
    for label, x in cases:
        y = k_weight(x)
        _, z = block_loudness(y)
        gated, _, _ = integrate(z)
        ungated = -0.691 + 10 * np.log10(np.mean(z) + 1e-30)
        print(f"   {label:>30} {gated:>12.3f} {ungated:>12.3f} "
              f"{gated - ungated:>+9.3f}")

    print("\n   ⚠️ 无门限时，静音把均值往下拉（静音也有 −∞ 的贡献）")
    print("      有门限时，静音块被丢掉 → 读数保持稳定 ✅")
    print("      这就是为什么必须**先门限再平均**：")
    print("      节目里的静音段不该影响'这个节目有多响'的判断")


def t3_absolute_vs_relative():
    print("\n" + "=" * 74)
    print("③ 绝对门限 vs 相对门限：各自在挡什么")
    print("=" * 74)

    N = SR * 20
    f0 = round(997.0 * N / SR) * SR / N
    t = np.arange(N) / SR
    loud = (0.3 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)     # 响的段
    quiet = (0.003 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)  # 很轻的段

    x = np.concatenate([loud[:10 * SR], quiet[:10 * SR]])
    y = k_weight(x)
    _, z = block_loudness(y)
    lv = -0.691 + 10 * np.log10(np.maximum(z, 1e-30))

    gated, k1, k2 = integrate(z, verbose=True)
    ungated = -0.691 + 10 * np.log10(np.mean(z) + 1e-30)

    print(f"\n   前 10 s（响）块响度 ≈ {lv[0]:.2f} LUFS")
    print(f"   后 10 s（轻）块响度 ≈ {lv[-1]:.2f} LUFS")
    print(f"\n   integrated（带门限）  = {gated:+.3f} LUFS")
    print(f"   无门限               = {ungated:+.3f} LUFS")
    print(f"   差                   = {gated - ungated:+.3f} dB")
    print("\n   ⚠️ 相对门限（Γ − 10 LU）把'明显更轻的段'整个丢掉")
    print("      所以 integrated LUFS 描述的是**主要段落**的响度，不是全片平均")

    # 单独验证绝对门限
    print("\n   单独看绝对门限（−70 LUFS）:")
    very_quiet = (0.00003 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)
    lv_q = -0.691 + 10 * np.log10(np.mean(k_weight(very_quiet) ** 2) + 1e-30)
    print(f"      幅度 3e-5 的正弦 → {lv_q:.2f} LUFS "
          f"→ {'被绝对门限挡掉' if lv_q < -70 else '保留'}")
    very_quiet2 = (0.0003 * np.sqrt(2.0)) * np.sin(2 * np.pi * f0 * t)
    lv_q2 = -0.691 + 10 * np.log10(np.mean(k_weight(very_quiet2) ** 2) + 1e-30)
    print(f"      幅度 3e-4 的正弦 → {lv_q2:.2f} LUFS "
          f"→ {'被绝对门限挡掉' if lv_q2 < -70 else '保留'}")
    print("      → −70 LUFS 大约是 16 bit 系统里 1 LSB 附近的电平")


def t4_crest_factor():
    print("\n" + "=" * 74)
    print("④ peak / RMS / LUFS 三种指标对同一素材的不同回答")
    print("=" * 74)

    N = SR * 4
    rng = np.random.default_rng(20261015)
    t = np.arange(N) / SR
    f0 = round(997.0 * N / SR) * SR / N

    def mk_sine():
        return (0.1) * np.sin(2 * np.pi * f0 * t)

    def mk_square():
        # 整数周期方波（用相位判断，避免 Gibbs）
        ph = (f0 * t) % 1.0
        return 0.1 * np.where(ph < 0.5, 1.0, -1.0)

    def mk_noise():
        x = rng.standard_normal(N)
        return 0.1 * x / np.max(np.abs(x))

    def mk_pulse():
        x = np.zeros(N)
        x[::SR // 4] = 0.1        # 每秒 4 个脉冲
        return x

    print(f"   {'信号':>16} {'peak(dBFS)':>12} {'RMS(dBFS)':>11} "
          f"{'LUFS':>9} {'crest':>8}")
    for label, x in [('正弦 997Hz', mk_sine()), ('方波 997Hz', mk_square()),
                     ('白噪声', mk_noise()), ('脉冲串 4/s', mk_pulse())]:
        pk = 20 * np.log10(np.max(np.abs(x)) + 1e-30)
        rm = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-30)
        y = k_weight(x)
        _, z = block_loudness(y[int(0.5 * SR):])
        lu, _, _ = integrate(z)
        print(f"   {label:>16} {pk:>12.2f} {rm:>11.2f} {lu:>9.2f} "
              f"{pk - rm:>8.2f}")

    print("\n   ⚠️ 关键观察")
    print("      - 所有信号的**峰值**都接近 −20 dBFS（除了脉冲串）")

    # 把每个信号归一化到相同 LUFS，看峰值差多少
    print("\n   归一化到同一 LUFS（−20）后，所需的峰值电平:")
    print(f"   {'信号':>16} {'LUFS 归零所需增益':>20} {'归一化后峰值':>14}")
    for label, x in [('正弦 997Hz', mk_sine()), ('方波 997Hz', mk_square()),
                     ('白噪声', mk_noise()), ('脉冲串 4/s', mk_pulse())]:
        y = k_weight(x)
        _, z = block_loudness(y[int(0.5 * SR):])
        lu, _, _ = integrate(z)
        gain = -20.0 - lu
        xa = x * 10 ** (gain / 20)
        pk = 20 * np.log10(np.max(np.abs(xa)) + 1e-30)
        print(f"   {label:>16} {gain:>+20.2f} {pk:>14.2f}")
    print("\n   ⚠️ 同样的 LUFS，峰值可以差 **十几 dB**")
    print("      → 这就是'响度标准化之后还要看 true peak 限幅'的原因")


def t5_true_peak():
    print("\n" + "=" * 74)
    print("⑤ True Peak：采样峰值会低估真实峰值")
    print("=" * 74)

    # 关键构造：让信号峰值落在**两个采样点之间**
    # 取 f = SR/4 且相位偏移 45° → 采样点正好在过零点两侧，峰值全被错过
    N = SR // 2
    t = np.arange(N) / SR
    # 用 f0 = SR/4，采到的序列是 ±A/√2 交替（峰值在采样点之间）
    f0 = SR / 4.0
    x = 0.9 * np.sin(2 * np.pi * f0 * t + np.pi / 4)
    print(f"   f = {f0:.0f} Hz（= SR/4），相位 45° 偏移")
    print(f"   采样峰值   = {20 * np.log10(np.max(np.abs(x))):+.3f} dBFS "
          f"（{np.max(np.abs(x)):.4f}）")
    tp4 = true_peak(x, 4)
    tp16 = true_peak(x, 16)
    print(f"   True Peak (4×)  = {20 * np.log10(tp4):+.3f} dBFS （{tp4:.4f}）")
    print(f"   True Peak (16×) = {20 * np.log10(tp16):+.3f} dBFS （{tp16:.4f}）")
    print(f"   理论真值 = {20 * np.log10(0.9):+.3f} dBFS （0.9000，因为相位只影响位置）")
    print(f"\n   低估量: 采样峰值比真值低 "
          f"{20 * np.log10(0.9) - 20 * np.log10(np.max(np.abs(x))):.3f} dB")
    # ⚠️ 这个例子里比率正好是 √2（3.01 dB）—— 因为 SR/4 + 45° 相位
    #    让采样点落在 ±A/√2 上。不是通用值，别当成常数。
    ratio = tp16 / np.max(np.abs(x))
    print(f"   True Peak / 采样峰值 = {ratio:.4f} （≈ √2 = {np.sqrt(2):.4f}）")
    assert abs(ratio - np.sqrt(2)) < 0.01, f"本构造下比率应为 √2, 实测 {ratio}"
    print("   ✅ 采样峰值低估了真实峰值（这就是 inter-sample peak 问题）")
    print("   ⚠️ 3.01 dB 这个低估量是**本构造特有**的（SR/4 + 45° 相位）")
    print("      真实素材的低估量取决于相位分布，通常 0.5–3 dB，极端可更多")
    print(f"   ⚠️ 4× 已经很接近 16×（差 "
          f"{20 * np.log10(tp16) - 20 * np.log10(tp4):.3f} dB）—— 但**不是**上界")
    print("      理论上连续信号的峰值可以任意接近，4× 只是工程折中")

    print("\n   一个实际例子：轻微削波的正弦（常见于过度限幅的母带）")
    N2 = SR
    t2 = np.arange(N2) / SR
    f2 = round(997.0 * N2 / SR) * SR / N2
    for amp in [0.8, 1.0, 1.2]:
        s = np.clip(amp * np.sin(2 * np.pi * f2 * t2), -1.0, 1.0)
        sp = 20 * np.log10(np.max(np.abs(s)))
        tp = 20 * np.log10(true_peak(s, 4))
        print(f"      驱动 {amp:.1f}× → 采样峰值 {sp:+.4f} dBFS, "
              f"true peak {tp:+.4f} dBFS")
    print("      → 削平后采样峰值卡在 0 dBFS，但 true peak 仍可能超过 0")


def t6_lra():
    print("\n" + "=" * 74)
    print("⑥ LRA（loudness range）：用短期响度的分位数")
    print("=" * 74)

    N = SR * 30
    f0 = round(997.0 * N / SR) * SR / N
    t = np.arange(N) / SR
    # 三段不同电平，模拟"主歌/副歌"动态
    levels = [0.05, 0.20, 0.35]          # 幅度
    seg = N // 3
    x = np.concatenate([levels[i] * np.sqrt(2.0) *
                        np.sin(2 * np.pi * f0 * t[:seg]) for i in range(3)])

    y = k_weight(x)
    # 短期：3 s 窗，1 s 步进（BS.1770-4 的 LRA 用 3 s）
    starts, z3 = block_loudness(y, ms=3000, hop=SR)
    lv = -0.691 + 10 * np.log10(np.maximum(z3, 1e-30))

    # LRA 用绝对门限 −70 LUFS + 相对门限 −20 LU
    keep1 = lv > -70.0
    gamma = -0.691 + 10 * np.log10(np.mean(z3[keep1]))
    keep2 = keep1 & (lv > gamma - 20.0)
    lv_k = np.sort(lv[keep2])
    # EBU Tech 3342: LRA = P95 − P10
    p10 = np.percentile(lv_k, 10)
    p95 = np.percentile(lv_k, 95)
    lra = p95 - p10

    print(f"   三段幅度: {levels} → 理论电平差 "
          f"{20 * np.log10(levels[2] / levels[0]):.2f} dB")
    for i, sl in enumerate([slice(0, 10), slice(10, 20), slice(20, None)]):
        print(f"      第 {i + 1} 段平均短期响度 ≈ {np.mean(lv[sl]):.2f} LUFS")
    print(f"\n   Γ（相对门限基准）= {gamma:.3f} LUFS, 阈值 = {gamma - 20:.3f} LUFS")
    print(f"   保留 {keep2.sum()}/{len(lv)} 个短期块")
    print(f"   P10 = {p10:.3f} LUFS,  P95 = {p95:.3f} LUFS")
    print(f"   LRA = P95 − P10 = {lra:.2f} LU")
    print("\n   ⚠️ LRA 描述的是'响度分布有多宽'（动态范围），不是峰均比")
    print("      用 P10/P95 而非 min/max —— 避免一两个极端块把结果带偏")
    print("      ⚠️ LRA 的相对门限是 **−20 LU**，和 integrated 的 **−10 LU** 不同")
    assert 8 < lra < 32, f"LRA 超出合理范围: {lra}"


if __name__ == '__main__':
    t1_calibration()
    t2_gating_power()
    t3_absolute_vs_relative()
    t4_crest_factor()
    t5_true_peak()
    t6_lra()
    print("\n" + "=" * 74)
    print("✅ verify-lufs-gating.py 全部通过")
    print("=" * 74)
