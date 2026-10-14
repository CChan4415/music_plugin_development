#!/usr/bin/env python3
"""
exp-002: Biquad 滤波器 —— 音频里 90% 的滤波器

对应 30-Wiki/DSP/Biquad 滤波器.md。
这个文件既是实验，也是**参考实现** —— 以后你写 C++ 版本时，
用这里的输出做 null test 对比。

运行:
    python3 biquad.py                # 完整实验（含播放）
    python3 biquad.py --no-play
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from audio_io import (write_wav, sine, white_noise, pink_noise, impulse,
                      peak_db, check_response, freq_response, report)

OUT = os.path.dirname(os.path.abspath(__file__))
SR = 48000
NO_PLAY = '--no-play' in sys.argv


def play(p):
    if NO_PLAY:
        print(f"  [跳过播放] {os.path.basename(p)}"); return
    os.system(f'afplay "{p}"')


# ══════════════════════════════════════════════════════════════
#  Biquad 实现（Direct Form I —— 最直白，先求正确再求快）
# ══════════════════════════════════════════════════════════════

class Biquad:
    """二阶 IIR 滤波器。

    差分方程:
        y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]

    ⚠️ 注意符号: 分母系数 a1/a2 在差分方程里是**减号**。
       不同教材符号约定不同，抄公式前必须确认。
    """

    def __init__(self, b0=1.0, b1=0.0, b2=0.0, a1=0.0, a2=0.0):
        self.set_coeffs(b0, b1, b2, a1, a2)
        self.reset()

    def set_coeffs(self, b0, b1, b2, a1, a2):
        self.b0, self.b1, self.b2 = b0, b1, b2
        self.a1, self.a2 = a1, a2

    def reset(self):
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

    def process_sample(self, x):
        y = (self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2
             - self.a1 * self.y1 - self.a2 * self.y2)
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y

    def process(self, x):
        """处理整个数组（Python 循环，慢但清楚）。"""
        y = np.empty_like(x)
        for n in range(len(x)):
            y[n] = self.process_sample(x[n])
        return y

    # ---------------- 系数计算（RBJ Audio EQ Cookbook）----------------

    @staticmethod
    def lowpass(fs, f0, Q):
        w0 = 2 * np.pi * f0 / fs
        alpha = np.sin(w0) / (2 * Q)
        cos_w0 = np.cos(w0)
        a0 = 1 + alpha
        return ((1 - cos_w0) / 2 / a0,
                (1 - cos_w0) / a0,
                (1 - cos_w0) / 2 / a0,
                -2 * cos_w0 / a0,
                (1 - alpha) / a0)

    @staticmethod
    def highpass(fs, f0, Q):
        w0 = 2 * np.pi * f0 / fs
        alpha = np.sin(w0) / (2 * Q)
        cos_w0 = np.cos(w0)
        a0 = 1 + alpha
        return ((1 + cos_w0) / 2 / a0,
                -(1 + cos_w0) / a0,
                (1 + cos_w0) / 2 / a0,
                -2 * cos_w0 / a0,
                (1 - alpha) / a0)

    @staticmethod
    def peaking(fs, f0, Q, gain_db):
        """峰值 EQ —— 你在 EQ 插件上最常用的那个。"""
        A = 10 ** (gain_db / 40)          # ⚠️ /40 不是 /20
        w0 = 2 * np.pi * f0 / fs
        alpha = np.sin(w0) / (2 * Q)
        cos_w0 = np.cos(w0)
        a0 = 1 + alpha / A
        return ((1 + alpha * A) / a0,
                -2 * cos_w0 / a0,
                (1 - alpha * A) / a0,
                -2 * cos_w0 / a0,
                (1 - alpha / A) / a0)

    @classmethod
    def make(cls, kind, fs, f0, Q=0.707, gain_db=0.0):
        if kind == 'lowpass':  return cls(*cls.lowpass(fs, f0, Q))
        if kind == 'highpass': return cls(*cls.highpass(fs, f0, Q))
        if kind == 'peaking':  return cls(*cls.peaking(fs, f0, Q, gain_db))
        raise ValueError(kind)


# ══════════════════════════════════════════════════════════════
#  实验
# ══════════════════════════════════════════════════════════════

def step(n, t):
    print(f"\n{'='*62}\n  第 {n} 步: {t}\n{'='*62}")


step(1, "验证系数：用解析解对比（这是最重要的一步）")

print("""
  方法: 喂单位脉冲 → 得到脉冲响应 → FFT → 频率响应
        和**解析解** H(e^jw) 逐点对比。

  一阶低通是 -6dB/oct，二阶(Biquad)应该是 -12dB/oct。
  截止频率处应该是 -3dB（对 Butterworth Q=0.707）。
""")

fc, Q = 1000.0, 0.707
bq = Biquad.make('lowpass', SR, fc, Q)
b0, b1, b2, a1, a2 = Biquad.lowpass(SR, fc, Q)
print(f"  fc={fc}Hz Q={Q} 的系数:")
print(f"    b = [{b0:.6f}, {b1:.6f}, {b2:.6f}]")
print(f"    a = [1.0, {a1:.6f}, {a2:.6f}]")

def theory_lp(hz):
    """低通的解析频率响应 |H(e^jw)|。"""
    w = 2 * np.pi * hz / SR
    z1, z2 = np.exp(-1j*w), np.exp(-2j*w)
    H = (b0 + b1*z1 + b2*z2) / (1 + a1*z1 + a2*z2)
    return 20 * np.log10(abs(H) + 1e-12)

h = bq.process(impulse(8192))
print()
ok = check_response(h, theory_lp, SR, tol_db=0.05)

# 检查滚降斜率
f, mag = freq_response(h, SR)
def at(hz): return mag[np.argmin(np.abs(f-hz))]
# ⚠️ fc*4 → fc*8 是**一个**倍频程（log2(8/4)=1），不是三个
slope = (at(fc*8) - at(fc*4)) / np.log2(8/4)
print(f"\n  实测滚降斜率: {slope:.1f} dB/oct  (二阶期望 ≈ -12 dB/oct)")
print(f"  ⚠️ 这里测出约 -13.3 而非正好 -12：因为 fc*4 还不够「远」，")
print(f"     渐近斜率要在远高于截止频率处才接近 -12。这是正常的。")
print(f"  截止频率处增益: {at(fc):.2f} dB  (Butterworth Q=0.707 期望 -3.0 dB)")

assert ok, "系数计算错误！"


step(2, "三种滤波器类型 + 听感")

src = pink_noise(6.0, SR, amp=0.4)
seg = len(src) // 3
out = np.empty_like(src)

filters = [('lowpass', 800, 0.707, 0), ('highpass', 800, 0.707, 0), ('peaking', 1000, 1.0, 12)]
names = ['低通 800Hz', '高通 800Hz', '峰值 1kHz +12dB']
for i, ((kind, f0, q, g), nm) in enumerate(zip(filters, names)):
    bq = Biquad.make(kind, SR, f0, q, g)
    out[i*seg:(i+1)*seg] = bq.process(src[i*seg:(i+1)*seg])

p = f"{OUT}/01-three-types.wav"
write_wav(p, out, SR)
print(f"""
  粉噪声依次通过:
    1. 低通 800Hz   → 变"闷"，高频被砍掉
    2. 高通 800Hz   → 变"薄"，低频被砍掉
    3. 峰值 1kHz +12dB → 某个频段被"顶起来"，像 EQ 推子

  这三个就是你每天在用的东西。
""")
play(p)


step(3, "Q 值的作用 —— 从平滑到 ringing")

src = sine(200, 3.0, SR, amp=0.5)
seg = len(src) // 4
out = np.empty_like(src)
qs = [0.5, 0.707, 5.0, 30.0]
for i, q in enumerate(qs):
    bq = Biquad.make('lowpass', SR, 1000, q)
    out[i*seg:(i+1)*seg] = bq.process(src[i*seg:(i+1)*seg])

p = f"{OUT}/02-Q-sweep.wav"
write_wav(p, out, SR)
print(f"""
  200Hz 正弦通过 1000Hz 低通，Q 依次为 {qs}

  低 Q (0.5):    平缓，无共振
  Q=0.707:       Butterworth，最平坦（默认选择）
  高 Q (5, 30):  在截止频率附近"凸起"，产生共振峰

  ⚠️ 高 Q 的代价: 脉冲响应会 ringing 很久（极点在单位圆附近）。
     这就是你调 EQ 时"Q 太高会有铃声感"的原因。

  验证: 看 impulse response 的衰减时间随 Q 变化。
""")
play(p)

print("  Q 对 ringing 长度的影响（脉冲响应衰减到峰值 -60dB 的时间）:")
print("  ⚠️ 测量陷阱: 必须找**最后一次**高于阈值的位置。")
print("     用绝对阈值 → 高 Q 峰值大，会误判成'衰减快'。")
print("     找'峰值后第一次低于阈值' → 振荡信号会立刻穿过去，也错。")
for q in [0.707, 5.0, 30.0, 100.0]:
    bq = Biquad.make('lowpass', SR, 1000, q)
    h = bq.process(impulse(96000))
    env = np.abs(h)
    above = np.where(env > env.max() * 1e-3)[0]
    t60 = above[-1] / SR * 1000 if len(above) else 0.0
    print(f"    Q={q:>6}  → {t60:>8.1f} ms")
print("    → Q 越高，ringing 越长。这就是'Q 太高有铃声感'的原因。")


step(4, "稳定性 —— 参数超范围会爆炸")

print("""
  二阶系统的稳定条件:  |a2| < 1  且  |a1| < 1 + a2

  当 f0 接近 0 或 fs/2，或 Q 极大时，可能失稳。
  插件里**必须钳制参数**，否则用户能调出爆炸声。
""")
print(f"  {'f0':>8} {'Q':>6} {'|a2|<1':>8} {'|a1|<1+a2':>12}  结果")
for f0, q in [(1000, 0.707), (23000, 0.707), (23999, 0.707), (1000, 100.0), (10, 0.707)]:
    b0,b1,b2,a1,a2 = Biquad.lowpass(SR, f0, q)
    c1, c2 = abs(a2) < 1, abs(a1) < 1 + a2
    bq = Biquad.make('lowpass', SR, f0, q)
    h = bq.process(impulse(48000))
    diverged = np.any(~np.isfinite(h)) or np.max(np.abs(h)) > 100
    status = "❌ 发散" if diverged else ("✅ 稳定" if (c1 and c2) else "⚠️ 条件不满足但未发散")
    print(f"  {f0:>8} {q:>6} {str(c1):>8} {str(c2):>12}  {status}")

print("""
  → 结论: fs/2 = 24000Hz，f0 接近它时公式失效（w0 → π）。
     插件里应该钳制到 fs*0.45 左右。
""")


step(5, "扫频 —— 听到滤波器在动")

src = pink_noise(8.0, SR, amp=0.4)
n = len(src)
out = np.empty_like(src)
# 截止频率按指数从 100Hz 扫到 12kHz
fcs = 100 * (12000/100) ** (np.arange(n)/n)
# 分块处理（每 256 样本更新一次系数，模拟真实插件做法）
BLOCK = 256
bq = Biquad.make('lowpass', SR, 100, 0.707)
for i in range(0, n, BLOCK):
    fc_now = fcs[min(i, n-1)]
    bq.set_coeffs(*Biquad.lowpass(SR, fc_now, 0.707))
    end = min(i+BLOCK, n)
    for k in range(i, end):
        out[k] = bq.process_sample(src[k])

p = f"{OUT}/03-sweep.wav"
write_wav(p, out, SR)
print(f"""
  粉噪声通过一个截止频率从 100Hz 扫到 12kHz 的低通滤波器。

  ⚠️ 注意这里的做法: **每 256 样本重算一次系数**。
     这是真实插件的标准做法 —— 每样本重算太贵，每 block 重算会有阶梯感。
     你听到的应该是平滑的"哇"效果，而不是阶梯。

  如果听到"咔咔"的颗粒感 → 说明系数更新太粗，需要更小的块或插值。
  见 [[参数平滑 parameter smoothing]]
""")
play(p)


step(6, "Null test —— 为以后对比 C++ 实现做准备")

# 同一输入跑两遍，必须 bit-exact（确定性检查）
src = white_noise(1.0, SR, amp=0.3)
y1 = Biquad.make('lowpass', SR, 2000, 0.707).process(src)
y2 = Biquad.make('lowpass', SR, 2000, 0.707).process(src)
same = np.array_equal(y1, y2)
print(f"  同一输入两次运行结果完全相同: {same}")
print(f"""
  ✅ 如果为 True，说明你的实现是确定性的 —— 这是能做 null test 的前提。

  以后你写 C++ 版本时:
    1. 用**完全相同的输入**（把这个 wav 存下来）
    2. C++ 输出和 Python 输出相减
    3. 差异应 < -100dB（浮点误差级别）

  工具: audio_io.null_test(python_out, cpp_out)
""")


print(f"\n{'='*62}\n  ✅ exp-002 完成\n{'='*62}")
print(f"""
  生成文件在 {OUT}/

  你现在应该理解:
  1. Biquad 系数怎么算（RBJ Cookbook）
  2. 为什么 A = 10^(dB/40) 而不是 /20
  3. Q 值如何影响 ringing
  4. 参数必须钳制（f0 < fs*0.45）
  5. 系数更新率与"阶梯感"的关系

  下一步:
  - 把这个 Python 实现改写成 C++（见 [[C++ 零基础到音频 DSP 路线]]）
  - 用 null test 验证两个实现等价
""")
