#!/usr/bin/env python3
"""
音频读写与验证工具 —— 本库所有 DSP 实验的公共基础。

用法:
    from audio_io import *
    write_wav('out.wav', x, 48000)
    x, sr = read_wav('out.wav')
    report('out.wav')

设计原则: 只用 numpy + 标准库 wave，不依赖 scipy/soundfile。
"""
import numpy as np
import wave


# ---------------- 读写 ----------------

def write_wav(path, x, sr=48000, bits=16):
    """把 float 数组 [-1,1] 写成 WAV。

    自动钳制到 [-1,1) —— 超出会环绕成噪声，这是新手最常踩的坑之一。
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[:, None]
    n_ch = x.shape[1]
    clipped = np.sum(np.abs(x) > 1.0)
    if clipped:
        print(f"⚠️  {clipped} 个样本超出 [-1,1]，已钳制（可能是增益算错了）")
    x = np.clip(x, -1.0, 1.0 - 2.0**-15)

    if bits == 16:
        data = (x * 32767).astype(np.int16)
    elif bits == 32:
        data = (x * 2147483647).astype(np.int32)
    else:
        raise ValueError("只支持 16 或 32 bit")

    with wave.open(str(path), 'wb') as f:
        f.setnchannels(n_ch)
        f.setsampwidth(bits // 8)
        f.setframerate(sr)
        f.writeframes(data.tobytes())
    return path


def read_wav(path):
    """读 WAV，返回 (float 数组 [-1,1], 采样率)。

    单声道返回 1-D，多声道返回 (N, ch)。
    """
    with wave.open(str(path), 'rb') as f:
        sr = f.getframerate()
        n_ch = f.getnchannels()
        sw = f.getsampwidth()
        raw = f.readframes(f.getnframes())

    if sw == 2:
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767.0
    elif sw == 4:
        data = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483647.0
    else:
        raise ValueError(f"不支持的位深: {sw*8}bit")

    if n_ch > 1:
        data = data.reshape(-1, n_ch)
    return data, sr


# ---------------- 测量 ----------------

def db(x):
    """线性幅度 → dB。加 1e-12 防止 log(0)。"""
    return 20.0 * np.log10(np.abs(x) + 1e-12)


def peak_db(x):
    return float(db(np.max(np.abs(x))))


def rms_db(x):
    return float(db(np.sqrt(np.mean(np.asarray(x)**2))))


def dominant_freq(x, sr):
    """用 FFT 找主频（Hz）。**测频率用这个，不要用过零计数。**

    过零计数会被量化产生的 0 值样本骗到 —— 见
    20-Notes/2026-10-14 第一次验证：过零计数为什么错了.md
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return float(np.fft.rfftfreq(len(x), 1.0 / sr)[np.argmax(X)])


def spectrum(x, sr, ref_db=0.0):
    """返回 (频率数组, dB 幅度数组)，可直接画图。"""
    x = np.asarray(x, dtype=np.float64).ravel()
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) * 2.0 / len(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    return f, db(X) + ref_db


def null_test(a, b, label="null test"):
    """两个信号相减，报告差异。

    音频开发的**核心验证手段**：把"听起来差不多"变成"数值上一致"。
    < -100 dB 通常说明两个实现等价。
    """
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    n = min(len(a), len(b))
    if len(a) != len(b):
        print(f"⚠️  长度不同 ({len(a)} vs {len(b)})，只比较前 {n} 个样本")
    d = a[:n] - b[:n]
    peak = peak_db(d)
    rel = peak - peak_db(a[:n])
    verdict = "✅ 等价" if rel < -100 else ("🟠 接近" if rel < -60 else "❌ 有差异")
    print(f"{label}: 最大差异 {peak:.1f} dB (相对信号 {rel:.1f} dB)  {verdict}")
    return rel


# ---------------- 测试信号 ----------------

def impulse(n=1024, amp=1.0):
    """单位脉冲 —— 输出即脉冲响应，完全描述一个线性系统。"""
    x = np.zeros(n); x[0] = amp
    return x


def sine(freq, dur, sr=48000, amp=0.5):
    t = np.arange(int(sr * dur)) / sr
    return amp * np.sin(2 * np.pi * freq * t)


def white_noise(dur, sr=48000, amp=0.1, seed=0):
    """白噪声。amp 是**峰值上限**（不是标准差）。

    高斯分布有长尾，直接 amp*randn 会超出 amp 好几倍。
    所以先生成再归一化到 amp —— 这样 amp 的语义和其他函数一致。
    """
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(int(sr * dur))
    return amp * x / np.max(np.abs(x))


def pink_noise(dur, sr=48000, amp=0.1, seed=0):
    """粉噪声 (-3dB/oct)。用频域整形实现，比时域滤波器更准确。"""
    n = int(sr * dur)
    rng = np.random.default_rng(seed)
    X = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1.0 / sr); f[0] = f[1]
    X /= np.sqrt(f)                       # 1/sqrt(f) 幅度 → 功率 1/f
    x = np.fft.irfft(X, n)
    return amp * x / np.max(np.abs(x))


def log_sweep(f1, f2, dur, sr=48000, amp=0.5):
    """对数扫频 —— 测频率响应的标准信号。"""
    n = int(sr * dur)
    t = np.arange(n) / sr
    k = np.log(f2 / f1)
    phase = 2 * np.pi * f1 * dur / k * (np.exp(t / dur * k) - 1)
    return amp * np.sin(phase)


# ---------------- 报告 ----------------

def report(path):
    """打印一个 WAV 文件的关键指标。每次生成音频后跑一下。"""
    x, sr = read_wav(path)
    mono = x if x.ndim == 1 else x.mean(axis=1)
    print(f"\n── {path} ──")
    print(f"   采样率 {sr} Hz | 时长 {len(mono)/sr:.2f} s | "
          f"声道 {1 if x.ndim==1 else x.shape[1]} | 样本 {len(mono)}")
    print(f"   峰值 {peak_db(mono):.2f} dBFS | RMS {rms_db(mono):.2f} dBFS")
    print(f"   主频 {dominant_freq(mono, sr):.2f} Hz")
    if np.any(np.isnan(mono)):
        print("   ❌ 含 NaN —— DSP 发散了")
    if np.any(np.isinf(mono)):
        print("   ❌ 含 Inf —— DSP 发散了")
    return mono, sr


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            report(p)
    else:
        # 自检：生成正弦并验证
        print("自检中...")
        x = sine(440, 1.0, amp=0.5)
        write_wav('/tmp/_selfcheck.wav', x)
        m, sr = report('/tmp/_selfcheck.wav')
        assert abs(dominant_freq(m, sr) - 440) < 1.0, "主频错误"
        assert abs(peak_db(m) - (-6.02)) < 0.1, "峰值错误"
        print("\n✅ 自检通过（440Hz / -6.02 dBFS）")

def freq_response(h, sr=48000, nfft=65536):
    """从**脉冲响应**精确计算频率响应。

    返回 (频率数组, dB 数组)。

    为什么用脉冲响应而不是扫频/白噪声:
      脉冲响应是确定性的 —— 它**完全描述**一个线性时不变系统。
      白噪声 FFT 有随机起伏(单个 realization 的方差很大)，
      扫频需要做反卷积。脉冲响应最直接、最精确。

    用法:
        h = my_filter(impulse(8192))
        f, mag = freq_response(h, sr)
    """
    H = np.fft.rfft(np.asarray(h, np.float64), nfft)
    return np.fft.rfftfreq(nfft, 1.0 / sr), db(H)


def check_response(h, theory_fn, sr=48000, freqs=None, tol_db=0.1):
    """把实测频响和解析解对比 —— **验证 DSP 正确性的标准做法**。

    h:          脉冲响应 (你的实现的输出)
    theory_fn:  解析函数, 输入频率(Hz) 返回 dB
    freqs:      要检查的频点, 默认自动选一组
    tol_db:     允许的最大偏差

    返回 True/False。

    为什么这比"听起来对"强:
      "听起来对"能骗过你, 0.001dB 的偏差骗不过。
      而且这个测试可以**自动化**, 以后改代码时不会悄悄改坏。
    """
    f, mag = freq_response(h, sr)
    if freqs is None:
        freqs = [100, 250, 500, 1000, 2000, 4000, 8000, 16000]

    def measured(hz):
        return mag[np.argmin(np.abs(f - hz))]

    worst = 0.0
    print(f"   {'频率':>8} {'理论':>10} {'实测':>10} {'偏差':>10}")
    for hz in freqs:
        if hz >= sr / 2:
            continue
        t, m = theory_fn(hz), measured(hz)
        worst = max(worst, abs(m - t))
        flag = "" if abs(m - t) <= tol_db else "  ⚠️"
        print(f"   {hz:>6} Hz {t:>9.2f}dB {m:>9.2f}dB {m-t:>+9.3f}dB{flag}")

    ok = worst <= tol_db
    print(f"   → 最大偏差 {worst:.4f} dB  {'✅ 通过' if ok else f'❌ 超过容差 {tol_db}dB'}")
    return ok

def dominant_freq_autocorr(x, sr=48000, fmin=50, fmax=2000):
    """用**自相关**测基频 —— 低频段比 FFT 准得多。

    为什么需要它:
      FFT 的频率分辨率 = sr/N。对 1 秒 @48kHz，分辨率是 1Hz，
      测 110Hz 时误差可达 1%，而且**低音区**（人耳最敏感的地方）最不准。
      自相关直接测周期，低频分辨率天然更好。

    另一个好处: 自相关找的是**基频**，而 FFT 找的是**最强频点**——
      如果基频比泛音弱（很多真实乐器如此），FFT 会给出错误的"音高"。

    实测对比 (Karplus-Strong, 目标 110Hz):
      FFT:        1099.50 Hz  ❌（因为信号衰减太快，测到了噪声）
      自相关:      109.97 Hz  ✅
    """
    x = np.asarray(x, np.float64).ravel()
    x = x - x.mean()
    x = x[:int(sr * 0.5)]                 # 只取前 0.5 秒（信号最强）
    c = np.correlate(x, x, 'full')[len(x) - 1:]
    c /= (c[0] + 1e-30)
    lo, hi = int(sr / fmax), min(int(sr / fmin), len(c) - 2)
    if hi <= lo:
        return 0.0
    k = int(np.argmax(c[lo:hi])) + lo
    # 抛物线插值，把精度提到亚样本级
    if 0 < k < len(c) - 1:
        a, b, cc = c[k - 1], c[k], c[k + 1]
        denom = a - 2 * b + cc
        if abs(denom) > 1e-20:
            k = k + 0.5 * (a - cc) / denom
    return float(sr / k)


def decay_time(x, sr=48000, threshold_db=-60.0):
    """测量信号衰减到峰值 threshold_db 所需时间（秒）。

    ⚠️ 关键: 必须找**最后一次**高于阈值的位置，不是第一次。
       振荡信号会在峰值后立刻穿过去，用"第一次"会得到荒谬的小值。

    用途: 测混响 RT60、测滤波器 ringing、测 Karplus-Strong 的延音长度。
    """
    x = np.asarray(x, np.float64).ravel()
    env = np.abs(x)
    if env.max() < 1e-30:
        return 0.0
    thr = env.max() * (10 ** (threshold_db / 20.0))
    above = np.where(env > thr)[0]
    return float(above[-1] / sr) if len(above) else 0.0

# ---------------- 窗函数（注意对称 vs 周期性）----------------

def hann_periodic(n):
    """**周期性** Hann 窗 —— 用于重叠相加（OLA），满足 COLA。

    ⚠️ 和 numpy.hanning() 不是同一个东西！
       np.hanning(N) 是对称版（分母 N-1），两端都是 0，**不满足 COLA**。
       本函数分母是 n，满足 w[k] + w[k+n/2] = 1（50% 重叠时）。

    实测:
       np.hanning(1024)         → max|w[k]+w[k+512]-1| = 1.5e-3   ❌
       hann_periodic(1024)      → max|w[k]+w[k+512]-1| = 4.4e-16  ✅

    用途: 粒子合成、STFT、重叠相加。
    滤波器设计请用对称版（np.hanning）。
    """
    return 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(n) / n))
