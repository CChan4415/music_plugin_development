import numpy as np
print("=== 关键差异：收敛速度（不是最终精度）===\n")
rng = np.random.default_rng(42)
N_TAP = 32
h_true = rng.standard_normal(N_TAP)*0.1; h_true /= np.linalg.norm(h_true)

def run(kind, x, d, param, n_tap=N_TAP):
    w = np.zeros(n_tap); e = np.zeros(len(x))
    P = np.eye(n_tap) if kind=="RLS" else None
    for n in range(n_tap, len(x)):
        xv = x[n-n_tap+1:n+1][::-1]
        y = w @ xv; e[n] = d[n] - y
        if kind == "LMS":
            w += 2*param*e[n]*xv
        elif kind == "NLMS":
            w += param*e[n]*xv/(np.dot(xv,xv)+1e-6)
        else:  # RLS
            k = P @ xv / (param + xv @ P @ xv)
            w += k*e[n]
            P = (P - np.outer(k, xv @ P))/param
    return e

N = 4000
x = rng.standard_normal(N)*0.5
d = np.convolve(x, h_true)[:N] + rng.standard_normal(N)*0.001

print(f"{'算法':<10} {'参数':>8} {'到达-20dB':>12} {'到达-30dB':>12} {'末段MSE':>10}")
for kind, param, label in [("LMS",0.01,"0.01"), ("NLMS",0.5,"0.5"), ("RLS",0.999,"0.999")]:
    e = run(kind, x, d, param)
    # 用滑动 RMS 找首次到达阈值
    win = 64
    rms = np.sqrt(np.convolve(e**2, np.ones(win)/win, mode='valid')+1e-30)
    db = 10*np.log10(rms)
    def first_below(th):
        idx = np.where(db < th)[0]
        return idx[0] if len(idx) else -1
    t20 = first_below(-20); t30 = first_below(-30)
    mse = 10*np.log10(np.mean(e[-500:]**2)+1e-30)
    print(f"{kind:<10} {label:>8} {t20:>12} {t30:>12} {mse:>9.1f}dB")

print("""
✅ 关键差异在**收敛速度**：
   • LMS 最慢（但最简单、最便宜）
   • NLMS 快得多（对输入功率归一化）
   • RLS 最快（但计算量 O(N²)）
   
   三者最终精度接近（都能到 -40dB）
""")
