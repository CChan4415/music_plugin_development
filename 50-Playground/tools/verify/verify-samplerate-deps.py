import numpy as np
print("=== 采样率变化：实测 ===\n")
print("① 为什么换采样率后 DSP 必须重置（用延迟线举例）")
print("   延迟线长度按**秒**定义，换采样率后长度必须重算\n")

def delay_samples(ms, sr): return int(ms*sr/1000)
print(f"{'延迟(ms)':>10} {'@44.1k':>9} {'@48k':>9} {'@96k':>9}")
for ms in [1, 10, 50, 100]:
    print(f"{ms:>10} {delay_samples(ms,44100):>9} {delay_samples(ms,48000):>9} {delay_samples(ms,96000):>9}")
print("""
⚠️ 如果代码里写死 sample 数（如 480）：
   @48kHz = 10ms ✅
   @96kHz = 5ms  ❌ 时间不对！
   → 必须按**秒**定义，在 prepare 里换算
""")

print("② 滤波器系数依赖采样率")
print("   Biquad 的 w0 = 2π·fc/fs —— fs 变了，系数必须重算\n")
def biquad_lowpass(fc, Q, sr):
    w0=2*np.pi*fc/sr; cw,al=np.cos(w0),np.sin(w0)/(2*Q); a0=1+al
    return np.array([(1-cw)/2/a0,(1-cw)/a0,(1-cw)/2/a0]), np.array([1.0,-2*cw/a0,(1-al)/a0])
print(f"{'采样率':>9} {'b0':>12} {'a1':>12}")
for sr in [44100, 48000, 96000]:
    b,a = biquad_lowpass(1000.0, 0.707, sr)
    print(f"{sr:>9} {b[0]:>12.8f} {a[1]:>12.8f}")
print("""
→ 系数完全不同。用旧系数在新采样率下跑 = 截止频率错
""")

print("③ 换采样率时状态残留的后果")
print("   一阶低通 y = (1-a)x + a·y，a = exp(-2πfc/fs)\n")
def onepole_run(sr, n, a_override=None):
    a = a_override if a_override is not None else np.exp(-2*np.pi*1000.0/sr)
    y = 0.0; out=[]
    for i in range(n):
        x = 1.0 if i==0 else 0.0     # 脉冲
        y = (1-a)*x + a*y
        out.append(y)
    return np.array(out), a
# 用 48k 的系数跑，但状态里留着 44.1k 的残余
_, a48 = onepole_run(48000, 10)
y_clean, _ = onepole_run(48000, 200, a_override=a48)
# 模拟：状态没重置（y 初值非 0）
y_dirty = []
y = 0.5   # ← 旧采样率留下的残余
for i in range(200):
    x = 1.0 if i==0 else 0.0
    y = (1-a48)*x + a48*y
    y_dirty.append(y)
y_dirty = np.array(y_dirty)
print(f"  状态干净: 前 5 个样本 {np.round(y_clean[:5],6)}")
print(f"  状态残留: 前 5 个样本 {np.round(y_dirty[:5],6)}")
print(f"  最大差异: {np.max(np.abs(y_clean-y_dirty)):.6f}")
print("""
→ 状态残留会让输出**从头就偏**，表现为换采样率瞬间的爆音/咔哒
""")
