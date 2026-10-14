#!/usr/bin/env python3
"""
exp-001: 听到你算出来的声音

对应路线图阶段 1 的第 1-4 项。跑完这个脚本，你会：
  1. 听到自己用 numpy 算出来的正弦波
  2. 听到白噪声 vs 粉噪声的区别
  3. 听到 -6dB 到底是多少
  4. 第一次听到"滤波器在动"

运行:
    python3 demo.py                # 正常（会自动播放）
    python3 demo.py --no-play      # 只生成文件，不播放

需要 numpy。如果没装: pip install numpy
"""
import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from audio_io import (write_wav, read_wav, sine, white_noise, pink_noise,
                      impulse, peak_db, rms_db, dominant_freq, spectrum,
                      freq_response, check_response, report)

OUT = os.path.dirname(os.path.abspath(__file__))
SR = 48000


# 无音频设备时用 --no-play 跳过播放（CI / 远程 / 静音环境）
NO_PLAY = '--no-play' in sys.argv


def play(path):
    """macOS 播放。"""
    if NO_PLAY:
        print(f"  [跳过播放] {os.path.basename(path)}")
        return
    os.system(f'afplay "{path}"')


def step(n, title):
    print(f"\n{'='*60}\n  第 {n} 步: {title}\n{'='*60}")


# ═══════════════════════════════════════════════════════════
step(1, "生成 440Hz 正弦 —— 这一行就是「振荡器」")

x = sine(440, 2.0, sr=SR, amp=0.5)
p = f"{OUT}/01-sine440.wav"
write_wav(p, x, SR)
report(p)

print("""
  你刚写的: x = sin(2*pi*f*t)
  这就是加法合成的全部基础。
  你以前在合成器上拧的正弦振荡器，本质就是这一行。
""")
play(p)


# ═══════════════════════════════════════════════════════════
step(2, "白噪声 vs 粉噪声 —— 频谱形状决定听感")

w = white_noise(2.0, SR, amp=0.3)
pk = pink_noise(2.0, SR, amp=0.3)
pw, pp = f"{OUT}/02-white.wav", f"{OUT}/02-pink.wav"
write_wav(pw, w, SR); write_wav(pp, pk, SR)

print(f"  白噪声: 峰值 {peak_db(w):.1f} dBFS | RMS {rms_db(w):.1f} dBFS")
print(f"  粉噪声: 峰值 {peak_db(pk):.1f} dBFS | RMS {rms_db(pk):.1f} dBFS")
print("""
  白噪声: 每个频率的能量相同 → 听起来"嘶嘶"，偏亮、偏刺
  粉噪声: 每个倍频程的能量相同 (-3dB/oct) → 听起来"沙沙"，更自然

  为什么粉噪声更自然? 因为自然界的噪声(雨、风、水流)大多是粉噪声。
  人耳对频率是对数感知的，所以"每倍频程等能量"才是听觉上的"平坦"。

  → 这就是为什么混响的尾音、以及很多合成器的噪声源，用的是粉噪声。
""")
print("  播放白噪声..."); play(pw)
print("  播放粉噪声..."); play(pp)


# ═══════════════════════════════════════════════════════════
step(3, "-6dB 到底是多少 —— dB 与线性增益")

x1 = sine(440, 1.5, sr=SR, amp=0.5)
x2 = x1 * 0.5                       # 再减半
p1, p2 = f"{OUT}/03-gain-6dB.wav", f"{OUT}/03-gain-12dB.wav"
write_wav(p1, x1, SR); write_wav(p2, x2, SR)

d1, d2 = peak_db(x1), peak_db(x2)
print(f"  幅度 0.5  → {d1:.2f} dBFS")
print(f"  幅度 0.25 → {d2:.2f} dBFS   (再减半)")
print(f"  差值: {d1-d2:.2f} dB")

# 直接拼起来，一次听完对比
combined = np.concatenate([x1, x2])
pc = f"{OUT}/03-compare.wav"
write_wav(pc, combined, SR)
print(f"""
  关键关系: 幅度减半 = {20*np.log10(0.5):.2f} dB ≈ -6 dB

  ⚠️ 注意: 是 20*log10，不是 10*log10
     20*log10 用于"幅度"(电压、采样值)
     10*log10 用于"功率"(能量)
     混用是新手最常见的错误之一。

  播放: 先是 0.5，然后跳到 0.25，你应该能明显听出"变小了"
""")
play(pc)


# ═══════════════════════════════════════════════════════════
step(4, "第一次听到「滤波器在动」—— 一阶低通")

def one_pole_lowpass(x, cutoff, sr):
    """一阶低通 (RC 数字等价)。

    核心: y[n] = (1-a)*x[n] + a*y[n-1]
    a 越接近 1，截止频率越低(滤得越狠)。
    """
    a = np.exp(-2 * np.pi * cutoff / sr)
    y = np.empty_like(x)
    prev = 0.0
    for n in range(len(x)):
        prev = (1 - a) * x[n] + a * prev
        y[n] = prev
    return y


# 用粉噪声(宽带)做素材，扫截止频率，能明显听到音色变化
src = pink_noise(4.0, SR, amp=0.4)
seg = len(src) // 4
out = np.empty_like(src)
for i, fc in enumerate([20000, 4000, 1000, 200]):
    out[i*seg:(i+1)*seg] = one_pole_lowpass(src[i*seg:(i+1)*seg], fc, SR)

pf = f"{OUT}/04-lowpass-sweep.wav"
write_wav(pf, out, SR)
print(f"""
  粉噪声依次通过 4 个截止频率: 20kHz → 4kHz → 1kHz → 200Hz

  你应该听到声音从"明亮"逐渐变成"闷"、"远"、"像隔了一堵墙"。

  ⚠️ 注意: Python 循环处理 4 秒音频(192000 样本)会慢，等一下。
     这正是以后要用 C++ 的原因 —— 但不是现在。现在你只要验证算法。

  一阶低通是 -6dB/oct (每倍频程衰减 6dB)。
  二阶(Biquad)是 -12dB/oct，见 [[Biquad 滤波器]]。
""")
play(pf)


# ═══════════════════════════════════════════════════════════
step(5, "验证: 你的滤波器 vs 数学解析解")

# 用**脉冲响应**测频响 —— 确定性、精确、可自动化
# 不要用白噪声 FFT: 它有随机起伏，你会以为是自己写错了
print("""
  方法: 喂一个单位脉冲，得到脉冲响应，FFT 得到频率响应。
        然后和**解析解**逐点对比。

  为什么不"听起来对就行":
    "听起来对"能骗过你，0.001dB 的偏差骗不过。
    而且这个测试可以自动化 —— 以后改代码时不会悄悄改坏。
""")

for fc in [1000]:
    a = np.exp(-2 * np.pi * fc / SR)

    def theory(hz, a=a):
        """一阶低通的解析频率响应。"""
        w = 2 * np.pi * hz / SR
        return 20 * np.log10(abs((1 - a) / (1 - a * np.exp(-1j * w))))

    h = one_pole_lowpass(impulse(8192), fc, SR)
    print(f"  截止频率 fc = {fc} Hz")
    ok = check_response(h, theory, SR, tol_db=0.05)
    if ok:
        print("""
  ✅ 你的实现和数学完全一致。

  看 fc 那一行: -3.00 dB —— 这就是"截止频率"的定义。
  再看每翻一倍频: 大约 -6 dB —— 这就是 -6dB/oct。
  二阶(Biquad)会是 -12dB/oct，见 [[Biquad 滤波器]]。
""")

print(f"\n{'='*60}")
print("  ✅ exp-001 完成")
print(f"{'='*60}")
print(f"""
  生成的文件在: {OUT}/

  现在做三件事:
  1. 重听 03-compare.wav，确认你能听出 -6dB 的差别
  2. 重听 04-lowpass-sweep.wav，确认滤波器的效果符合直觉
  3. 把结论写进 20-Notes/ —— 你自己的理解比代码值钱

  下一步: exp-002 写 Biquad 滤波器 (见 30-Wiki/DSP/Biquad 滤波器.md)
""")
