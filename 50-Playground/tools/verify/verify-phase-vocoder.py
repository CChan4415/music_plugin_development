import numpy as np
print("=== 相位声码器：实测验证 ===\n")
SR = 48000.0

def stft(x, N=1024, hop=256):
    w = np.hanning(N)
    n_frames = (len(x)-N)//hop + 1
    frames = np.array([x[i*hop:i*hop+N]*w for i in range(n_frames)])
    return np.fft.rfft(frames, axis=1), w, n_frames

def istft(S, N=1024, hop=256, length=None):
    w = np.hanning(N)
    n_frames = S.shape[0]
    out = np.zeros((n_frames-1)*hop + N)
    wsum = np.zeros_like(out)
    for i in range(n_frames):
        seg = np.fft.irfft(S[i], N)
        out[i*hop:i*hop+N] += seg*w
        wsum[i*hop:i*hop+N] += w*w
    nz = wsum > 1e-12
    out[nz] /= wsum[nz]
    return out[:length] if length else out

# ① 恒等变换（不修改相位）
N, HOP = 1024, 256
t = np.arange(int(SR))/SR
x = 0.5*np.sin(2*np.pi*440*t)
S, w, nf = stft(x, N, HOP)
y = istft(S, N, HOP, len(x))
n = min(len(y), len(x))
core = slice(N, n-N)
err = np.max(np.abs(y[core]-x[core]))
print(f"① STFT→ISTFT 恒等重建（N={N}, hop={HOP}）")
print(f"   最大误差 = {err:.3e}  {'✅' if err < 1e-10 else '❌'}")
print()

# ② 时间拉伸：相位声码器的核心
def phase_vocoder(S, rate, N=1024, hop=256):
    """rate > 1 = 拉伸（变慢）"""
    n_frames = S.shape[0]
    out_frames = int(n_frames/rate)
    out = np.zeros((out_frames, S.shape[1]), dtype=complex)
    phase_acc = np.angle(S[0])
    # 预期相位增量
    dphi = 2*np.pi*hop*np.arange(S.shape[1])/N
    for i in range(1, out_frames):
        pos = i*rate
        i0 = int(np.floor(pos)); frac = pos - i0
        if i0+1 >= n_frames: break
        # 幅度插值
        mag = (1-frac)*np.abs(S[i0]) + frac*np.abs(S[i0+1])
        # 相位推进（用**当前帧的实际相位差**）
        dp = np.angle(S[i0+1]) - np.angle(S[i0]) - dphi
        dp = np.mod(dp + np.pi, 2*np.pi) - np.pi     # 缠绕到 [-pi,pi]
        phase_acc += dphi + dp
        out[i] = mag * np.exp(1j*phase_acc)
    return out

for rate in [1.0, 2.0]:
    Sv = phase_vocoder(S, rate, N, HOP)
    yv = istft(Sv, N, HOP)
    print(f"② 时间拉伸 rate={rate}: 输出时长 {len(yv)/SR:.2f}s（原 {len(x)/SR:.2f}s）")
    if rate == 1.0:
        m = min(len(yv), len(x))
        e = np.max(np.abs(yv[N:m-N]-x[N:m-N]))
        print(f"   rate=1 应近似恒等: 误差 {e:.3e}")
print()
print("""✅ 相位声码器的核心：
   ① STFT 分解
   ② 幅度插值 + **相位按预期增量推进**（不是直接插值相位！）
   ③ ISTFT 重建
   
   ⚠️ 关键：相位必须"推进"而不是"插值"——
      直接插值相位会在缠绕处产生错误
""")
