import numpy as np
np.set_printoptions(precision=15, suppress=False)

# ---- BS.1770-4 公布的 48 kHz K 加权系数 ----
B1_48 = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
A1_48 = np.array([1.0, -1.69065929318241, 0.73248077421585])
B2_48 = np.array([1.0, -2.0, 1.0])
A2_48 = np.array([1.0, -1.99004745483398, 0.99007225036621])

def shelf(fs, f0=1681.974450955533, G=3.999843853973347, Q=0.7071752369554196):
    K = np.tan(np.pi*f0/fs); Vh = 10**(G/20); Vb = Vh**0.4996667741545416
    a0 = 1.0 + K/Q + K*K
    b = np.array([(Vh + Vb*K/Q + K*K)/a0, 2.0*(K*K - Vh)/a0, (Vh - Vb*K/Q + K*K)/a0])
    a = np.array([1.0, 2.0*(K*K - 1.0)/a0, (1.0 - K/Q + K*K)/a0])
    return b, a

def hp(fs, f0=38.13547087602444, Q=0.5003270373238773):
    K = np.tan(np.pi*f0/fs)
    a0 = 1.0 + K/Q + K*K
    b = np.array([1.0, -2.0, 1.0])
    a = np.array([1.0, 2.0*(K*K-1.0)/a0, (1.0-K/Q+K*K)/a0])
    return b, a

b1,a1 = shelf(48000.0); b2,a2 = hp(48000.0)
print("=== 解析设计 vs BS.1770 公布系数 (fs=48000) ===")
print("stage1 b 误差:", np.abs(b1-B1_48).max())
print("stage1 a 误差:", np.abs(a1-A1_48).max())
print("stage2 b 误差:", np.abs(b2-B2_48).max())
print("stage2 a 误差:", np.abs(a2-A2_48).max())
print("b1 =", b1); print("a1 =", a1)

def fresp(b, a, fs, f):
    z = np.exp(-2j*np.pi*np.asarray(f, float)/fs)
    return (b[0] + b[1]*z + b[2]*z**2) / (a[0] + a[1]*z + a[2]*z**2)

fs = 48000.0
f = np.array([20, 50, 100, 200, 500, 997, 1000, 2000, 5000, 10000, 20000], float)
H = fresp(b1,a1,fs,f) * fresp(b2,a2,fs,f)
print("\n=== K 加权频响（级联两级）===")
for hz, m in zip(f, 20*np.log10(np.abs(H))):
    print(f"  {hz:>7.0f} Hz  {m:+8.3f} dB")
