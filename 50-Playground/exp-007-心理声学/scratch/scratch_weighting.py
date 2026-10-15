import numpy as np
nc = lambda f0, Q=0.7071067811865476, G=0.0: None

# ================= A/B/C 加权：解析公式（IEC 61672 定义的模拟原型） =================
def a_weight_db(f):
    f = np.asarray(f, float); f2 = f*f
    num = (12194.0**2) * f2**2
    den = (f2 + 20.6**2) * np.sqrt((f2 + 107.7**2)*(f2 + 737.9**2)) * (f2 + 12194.0**2)
    return 20*np.log10(num/den) + 2.00

def b_weight_db(f):
    f = np.asarray(f, float); f2 = f*f
    num = (12194.0**2) * f*np.sqrt(f2)
    den = (f2 + 20.6**2) * np.sqrt(f2 + 158.5**2) * (f2 + 12194.0**2)
    return 20*np.log10(num/den) + 0.17

def c_weight_db(f):
    f = np.asarray(f, float); f2 = f*f
    num = (12194.0**2) * f2
    den = (f2 + 20.6**2) * (f2 + 12194.0**2)
    return 20*np.log10(num/den) + 0.06

f = np.array([10,20,31.5,50,63,100,125,200,250,400,500,800,1000,1250,2000,3150,4000,5000,8000,10000,12500,16000,20000], float)
print(f"{'f(Hz)':>8} {'A(dB)':>9} {'B(dB)':>9} {'C(dB)':>9}")
for hz, a, b, c in zip(f, a_weight_db(f), b_weight_db(f), c_weight_db(f)):
    print(f"{hz:>8.1f} {a:>+9.2f} {b:>+9.2f} {c:>+9.2f}")
print("\n=== 归一化自检：1 kHz 处应为 0.00 dB ===")
print(f"A(1000) = {a_weight_db(1000.0):+.4f} dB")
print(f"B(1000) = {b_weight_db(1000.0):+.4f} dB")
print(f"C(1000) = {c_weight_db(1000.0):+.4f} dB")
# 极值点
ff = np.logspace(np.log10(5), np.log10(20000), 400000)
for nm, fn in [('A', a_weight_db), ('B', b_weight_db), ('C', c_weight_db)]:
    y = fn(ff); i = np.argmin(y)
    # 高频平台值
    print(f"{nm}: 最小 {y[i]:+.2f} dB @ {ff[i]:.1f} Hz ; 20kHz {fn(20000.0):+.2f} dB ; 10Hz {fn(10.0):+.2f} dB")
