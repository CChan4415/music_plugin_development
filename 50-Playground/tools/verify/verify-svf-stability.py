import numpy as np
SR=48000.0

# 正确的 Chamberlin 自由响应状态矩阵（推导见下）
#   low[n+1]  = low[n] + f*band[n]
#   high[n]   = -low[n+1] - q*band[n]
#   band[n+1] = band[n] + f*high[n]
# ⇒ [low;band]_{n+1} = A [low;band]_n,  A = [[1, f], [-f, 1-f²-fq]]
#   det(A) = 1 - fq,  trace(A) = 2 - f² - fq
def A_mat(f,q): return np.array([[1.0, f],[-f, 1.0-f*f-f*q]])
def stable(f,q):
    det=1-f*q; tr=2-f*f-f*q
    return abs(det)<1 and abs(tr)<1+det
def f_bound(q): return np.sqrt(q*q+4)-q

print("="*90)
print("Chamberlin SVF 稳定性（修正后的状态矩阵）")
print("稳定 ⟺ |det|<1 且 |trace|<1+det  ⟺  f² + 2fq − 4 < 0  ⟺  f < √(q²+4) − q")
print("="*90)
print(f"{'q=1/Q':>7} {'f':>6} {'det':>8} {'trace':>9} {'|λ|max':>9} {'特征值判据':>10} {'闭式判据':>9} {'一致':>5}")
for q in [0.5,1.0,2.0]:
    for f in [0.5,1.0,1.5,2.0,2.5,3.0]:
        lam=np.abs(np.linalg.eigvals(A_mat(f,q))).max()
        e=lam<1; c=stable(f,q)
        print(f"{q:>7.2f} {f:>6.2f} {1-f*q:>8.3f} {2-f*f-f*q:>9.3f} {lam:>9.5f} {str(e):>10} {str(c):>9} {'✅' if e==c else '❌':>5}")

print("\n" + "="*90)
print("实测边界 vs 闭式 f<√(q²+4)−q（数值仿真，无输入自由响应）")
print("="*90)
def sim(f,q,n=200000):
    low=0.0; band=1e-6; peak=0.0
    for i in range(n):
        low  = low + f*band
        high = -low - q*band
        band = band + f*high
        if i>n//2: peak=max(peak, abs(low)+abs(band))
    return peak
print(f"{'q':>7} {'闭式边界':>11} {'仿真边界':>11} {'偏差':>10}   {'fc边界@48k':>11}")
for q in [0.05,0.25,0.5,1.0,1.41421,2.0,5.0]:
    lo,hi=0.001,min(f_bound(q)*2,6.0)
    for _ in range(35):
        mid=(lo+hi)/2
        if sim(mid,q)<1e-12: lo=mid
        else: hi=mid
    th=f_bound(q)
    fc=SR*np.arcsin(min(th,2.0)/2.0)/np.pi
    print(f"{q:>7.3f} {th:>11.5f} {lo:>11.5f} {lo-th:>+10.2e}   {fc:>9.0f} Hz")

print("\n" + "="*90)
print("换算成 Q 和实际截止频率上限（fs=48kHz）")
print("f_max=(√(1+4Q²)−1)/Q ; fc_max = (fs/π)·arcsin(f_max/2)")
print("="*90)
print(f"{'Q':>8} {'q=1/Q':>8} {'f_max':>9} {'fc_max Hz':>11} {'fc_max/fs':>10} {'备注':>22}")
for Q in [0.5,0.577,0.707,1.0,2.0,5.0,10.0,50.0]:
    q=1.0/Q; fmax=f_bound(q); fc=SR*np.arcsin(min(fmax,2.0)/2.0)/np.pi
    note = "← Butterworth Q" if abs(Q-0.7071)<1e-3 else ("← 临界阻尼" if abs(Q-0.5)<1e-3 else "")
    print(f"{Q:>8.3f} {q:>8.3f} {fmax:>9.4f} {fc:>11.0f} {fc/SR:>10.4f} {note:>22}")
