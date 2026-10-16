import numpy as np
print("=== 逼近并越过稳定上限 ===\n")
rng = np.random.default_rng(7)
N_TAP=16; h_true=rng.standard_normal(N_TAP)*0.1; h_true/=np.linalg.norm(h_true)
N=6000; x=rng.standard_normal(N)*0.5
d=np.convolve(x,h_true)[:N]
Px=np.mean(x**2)
mu_max = 1.0/(N_TAP*Px)
print(f"  1/(N·Px) = {mu_max:.4f}")
print(f"  2/(N·Px) = {2*mu_max:.4f}\n")
def run(mu):
    w=np.zeros(N_TAP); e=np.zeros(N); peak=0
    for n in range(N_TAP,N):
        xv=x[n-N_TAP+1:n+1][::-1]
        e[n]=d[n]-w@xv
        w += 2*mu*e[n]*xv
        if n > N//2: peak=max(peak, np.max(np.abs(w)))
    return e, peak
print(f"{'μ':>10} {'相对1/(N·Px)':>14} {'末段MSE':>12} {'权重峰值':>12} {'判定':>8}")
for mu in [0.05, 0.1, 0.2, 0.25, 0.3, 0.5, 1.0]:
    e, pk = run(mu)
    mse = 10*np.log10(np.mean(e[-1000:]**2)+1e-30)
    v = "✅" if mse<-20 else ("🟠" if mse<10 else "❌ 发散")
    print(f"{mu:>10} {mu/mu_max:>13.2f}x {mse:>12.1f} {pk:>12.2f} {v:>8}")
