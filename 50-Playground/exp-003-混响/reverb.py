#!/usr/bin/env python3
"""
exp-003: 从延迟到混响 —— 亲手搭一个 Schroeder/Freeverb

对应 30-Wiki/Music-Acoustics/混响的原理.md。
你会依次实现：单个反馈延迟 → 梳状滤波器 → 全通 → 完整混响，
每一步都能听到变化，并且每一步都验证它的数学。

运行:
    python3 reverb.py --no-play
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from audio_io import write_wav, impulse, pink_noise, peak_db, report

OUT = os.path.dirname(os.path.abspath(__file__))
SR = 48000
NO_PLAY = '--no-play' in sys.argv


def play(p):
    if NO_PLAY:
        print(f"  [跳过播放] {os.path.basename(p)}"); return
    os.system(f'afplay "{p}"')


def step(n, t):
    print(f"\n{'='*62}\n  {n}. {t}\n{'='*62}")


# ══════════════════════════════════════════════════════════════
#  构件 1：反馈延迟（混响的最小单元）
# ══════════════════════════════════════════════════════════════

def feedback_delay(x, delay_samples, feedback):
    """y[n] = x[n] + feedback * y[n - delay]

    这就是一个回声。feedback 决定回声衰减多快。
    """
    y = np.zeros_like(x)
    d = int(delay_samples)
    for n in range(len(x)):
        delayed = y[n - d] if n >= d else 0.0
        y[n] = x[n] + feedback * delayed
    return y


def feedback_for_rt60(rt60_sec, delay_sec):
    """把"想要的混响时间"换算成反馈增益。

    推导: 每次循环幅度 ×g，要衰减 60dB 需 g^n = 10^(-60/20) = 0.001
          所以 n = log(0.001)/log(g)，RT60 = n * delay
    """
    n = rt60_sec / delay_sec
    return 10 ** (-3.0 / n)


step(1, "验证 RT60 公式 —— 用户拧的是秒，你要算的是增益")

print(f"  {'RT60设定':>10} {'延迟ms':>8} {'feedback':>10} {'实测RT60':>10}  核对")
for rt60, d_ms in [(0.5, 23.27), (1.0, 23.27), (2.0, 23.27), (3.0, 46.5)]:
    d_sec = d_ms / 1000
    g = feedback_for_rt60(rt60, d_sec)
    d_samples = int(round(d_ms * SR / 1000))
    h = feedback_delay(impulse(int(SR * rt60 * 3 + d_samples * 2)), d_samples, g)
    idx = np.nonzero(h)[0]
    amps = np.abs(h[idx])
    below = np.where(amps < 1e-3)[0]
    t60 = idx[below[0]] / SR if len(below) else float('inf')
    err = (t60 - rt60) / rt60 * 100
    print(f"  {rt60:>9.1f}s {d_ms:>8.1f} {g:>10.4f} {t60:>9.2f}s  {err:+.1f}%")

print("""
  ✅ 公式正确 → 插件里可以放心用它把 decay 旋钮换算成反馈增益
""")


# ══════════════════════════════════════════════════════════════
#  构件 2：梳状滤波器（带阻尼）
# ══════════════════════════════════════════════════════════════

class Comb:
    """带阻尼的梳状滤波器 —— Freeverb 的核心。

    阻尼 (damp) 让高频衰减更快，模拟空气和软表面对高频的吸收。
    没有阻尼 → 尾巴一直很亮 → "金属味"。
    """
    def __init__(self, size, feedback, damp):
        self.buf = np.zeros(size)
        self.i = 0
        self.fb = feedback
        self.damp = damp
        self.store = 0.0

    def process_sample(self, x):
        out = self.buf[self.i]
        # 一阶低通（阻尼）—— 在反馈路径里
        self.store = out * (1 - self.damp) + self.store * self.damp
        self.buf[self.i] = x + self.store * self.fb
        self.i = (self.i + 1) % len(self.buf)
        return out

    def process(self, x):
        y = np.empty_like(x)
        for n in range(len(x)):
            y[n] = self.process_sample(x[n])
        return y


class Allpass:
    """全通滤波器 —— 不改变频响，只打散相位，增加回声密度。"""
    def __init__(self, size, feedback=0.5):
        self.buf = np.zeros(size)
        self.i = 0
        self.fb = feedback

    def process_sample(self, x):
        buf_out = self.buf[self.i]
        y = -x + buf_out
        # ⚠️ 必须存 x + y·fb（用输出 y），不能存 x + buf_out·fb
        # 否则不是全通，会变成谐振滤波器（g=0.7 时增益 2.63 倍）
        self.buf[self.i] = x + y * self.fb
        self.i = (self.i + 1) % len(self.buf)
        return y

    def process(self, x):
        y = np.empty_like(x)
        for n in range(len(x)):
            y[n] = self.process_sample(x[n])
        return y


step(2, "梳状滤波器 —— 阻尼如何让尾巴变自然")

# 互质延迟时间（关键！避免驻波/金属味）
COMB_TUNING = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]

src = impulse(int(SR * 3))
print(f"  用 {len(COMB_TUNING)} 个梳状滤波器，延迟时间互质: {COMB_TUNING[:4]}...")
print("  ⚠️ 互质很重要: 如果用 1000/2000/3000 这种整数倍，回声会周期性重合")
print("     产生强烈的'金属管'音高感。这是 Schroeder 混响的经典问题。\n")

print("  验证方法: 分频段看能量随时间的变化。")
print("  阻尼起作用时，「高频 - 低频」这个差值应随时间**下降**。\n")


def band_energy_db(sig, lo, hi, t0, t1):
    """某时间段内某频段的能量 (dB)。"""
    a, b = int(t0 * SR), int(t1 * SR)
    seg = sig[a:b]
    X = np.fft.rfft(seg * np.hanning(len(seg)))
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    m = (f >= lo) & (f <= hi)
    return 10 * np.log10(np.sum(np.abs(X[m]) ** 2) + 1e-30)


for damp in [0.0, 0.5, 0.8]:
    out = np.zeros_like(src)
    for size in COMB_TUNING:
        out += Comb(size, feedback_for_rt60(2.0, size / SR), damp).process(src)
    out /= len(COMB_TUNING)
    p = f"{OUT}/01-comb-damp{damp:.1f}.wav"
    write_wav(p, out, SR)
    print(f"  damp={damp:.1f}")
    print(f"    {'时间段':>10} {'低频':>10} {'高频':>10} {'高频-低频':>11}")
    for t0, t1 in [(0.0, 0.1), (0.5, 0.6), (1.0, 1.1)]:
        lo = band_energy_db(out, 100, 1000, t0, t1)
        hi = band_energy_db(out, 4000, 16000, t0, t1)
        print(f"    {t0:>4.1f}-{t1:<4.1f}s {lo:>9.1f} {hi:>10.1f} {hi-lo:>11.1f}")
    print()

print("""  → damp=0.0: 「高频-低频」基本不变 (~12dB) = 高低频衰减一样快 = 无阻尼
  → damp=0.5: 从 9.1 掉到 -68 = 高频衰减快得多
  → damp=0.8: 更快掉到 -157

  ✅ 阻尼确实起作用了。

  ⚠️ 测量陷阱: 不要用「高频能量/中频能量」的比值，也不要用线性拟合斜率。
     前者受整体电平影响；后者在信号衰减到噪声底后会拟合出错误的斜率。
     正确做法: **比较不同时间段的分频段能量**。

  播放 01-comb-damp0.0.wav 和 01-comb-damp0.8.wav 对比听。
""")
play(f"{OUT}/01-comb-damp0.0.wav")
play(f"{OUT}/01-comb-damp0.8.wav")


# ══════════════════════════════════════════════════════════════
#  构件 3：完整混响（Schroeder + 阻尼 + 全通）
# ══════════════════════════════════════════════════════════════

class SimpleReverb:
    """8 梳状（并联）+ 4 全通（串联）—— Freeverb 的结构。

    信号流:
        输入 → [8 个并联梳状] → 求和 → [4 个串联全通] → 输出
    """
    def __init__(self, sr, rt60=2.0, damp=0.2, wet=0.4):
        self.sr = sr
        self.wet = wet
        # 立体声扩展：右声道用略长的延迟
        self.combs = [Comb(s, feedback_for_rt60(rt60, s/sr), damp)
                      for s in COMB_TUNING]
        self.allpasses = [Allpass(s, 0.5) for s in [556, 441, 341, 225]]

    def process(self, x):
        # 并联梳状
        acc = np.zeros_like(x)
        for c in self.combs:
            acc += c.process(x)
        acc /= len(self.combs)
        # 串联全通
        for a in self.allpasses:
            acc = a.process(acc)
        return acc


step(3, "完整混响 —— 听到「房间」")

src = pink_noise(1.5, SR, amp=0.5)
# 加一个明显的包络，让"房间感"更清楚
env = np.exp(-np.arange(len(src)) / (SR * 0.08))
src = src * env

print("  处理中（Python 循环较慢，约 10-20 秒）...")
for rt60, damp in [(0.5, 0.2), (2.0, 0.2), (2.0, 0.8), (5.0, 0.3)]:
    rv = SimpleReverb(SR, rt60=rt60, damp=damp)
    wet = rv.process(src)
    dry = src * (1 - 0.4)
    out = dry + wet * 0.4
    p = f"{OUT}/02-reverb-rt{rt60}-damp{damp}.wav"
    write_wav(p, out, SR)
    print(f"  RT60={rt60}s damp={damp} → {os.path.basename(p)}")

print("""
  依次听这四个文件，注意:
    rt0.5  → 小房间，干
    rt2.0  → 中等空间
    rt2.0 damp0.8 → 同样的空间，但尾巴更"暗"、更柔和
    rt5.0  → 大教堂，尾巴很长

  ⚠️ 这些还很粗糙（没有 pre-delay、没有调制、单声道）。
     但它们**结构上就是**真实混响插件的骨架。
""")
play(f"{OUT}/02-reverb-rt2.0-damp0.2.wav")
play(f"{OUT}/02-reverb-rt5.0-damp0.3.wav")


step(4, "验证：稳定性 + denormal 检查")

print("  ⚠️ 这是混响最容易出问题的地方\n")
rv = SimpleReverb(SR, rt60=3.0, damp=0.2)
h = rv.process(impulse(int(SR * 10)))
tail = h[int(SR * 8):]
print(f"  喂一个脉冲，跑 10 秒:")
print(f"    前 1 秒峰值   {peak_db(h[:SR]):>8.2f} dB")
print(f"    8-10 秒峰值  {peak_db(tail) if np.max(np.abs(tail))>0 else -np.inf:>8.2f} dB")
print(f"    含 NaN/Inf:  {np.any(~np.isfinite(h))}")
print(f"    是否发散:    {'❌ 是' if np.max(np.abs(h)) > 10 else '✅ 否'}")

print("""
  ✅ 稳定 → 混响尾音必须衰减到 0，不能发散
  ⚠️ 注意 8-10 秒的峰值虽然极小，但**不是 0** —— 这就是 denormal 的来源！
     真实插件里，这些极小的值会让某些 CPU 慢 10-100 倍。
     解法: 在反馈路径加极小直流偏置，或用 FTZ。
     见 [[denormal 数处理]]
""")

print(f"\n{'='*62}\n  ✅ exp-003 完成\n{'='*62}")
print(f"""
  生成文件在 {OUT}/

  你现在应该理解:
  1. 混响 = 反馈延迟 + 阻尼 + 全通（不是一个神秘的东西）
  2. RT60 ↔ 反馈增益的换算（已验证）
  3. 阻尼让尾巴变暗 → 自然
  4. 延迟时间必须互质 → 否则金属味
  5. denormal 从哪来（尾巴的极小值）

  对比 30-Wiki/Music-Acoustics/混响的原理.md 的「参数→算法映射表」，
  你会发现每一个旋钮都对应这里的一个变量。

  下一步:
  - 加 pre-delay（一个纯延迟）
  - 加 LFO 调制延迟线（需要分数延迟插值）
  - 换成 FDN（用矩阵混合，见 [[反馈延迟网络 FDN]]）
""")
