import numpy as np
print("="*94)
print("① 几何解释（修正：要乘 b0）")
print("   H(z) = b0 · ∏(1 − z_k z^-1) / ∏(1 − p_k z^-1)")
print("   |H(e^{jw})| = |b0| · ∏|e^{jw} − z_k| / ∏|e^{jw} − p_k|")
print("   = b0 × (到各零点的距离之积) / (到各极点的距离之积)")
print("="*94)
def biquad_lp(fc,Q,sr=48000):
    w=2*np.pi*fc/sr; al=np.sin(w)/(2*Q); c=np.cos(w); a0=1+al
    b=np.array([(1-c)/2, 1-c, (1-c)/2])/a0
    a=np.array([1.0, -2*c/a0, (1-al)/a0])
    return b,a
print(f"   {'频率Hz':>8} {'|H| 多项式':>12} {'|H| 几何':>12} {'偏差':>10}")
for fc,Q in [(1000,0.707),(1000,5.0)]:
    b,a=biquad_lp(fc,Q); zk=np.roots(b); pk=np.roots(a)
    print(f"   --- fc={fc}Hz, Q={Q}: 极点={np.round(pk,5)} (|p|={np.abs(pk)[0]:.5f}), 零点={np.round(zk,5)} (|z|={np.abs(zk)[0]:.5f}) ---")
    for fq in [100,1000,5000,15000]:
        z=np.exp(1j*2*np.pi*fq/48000)
        H=abs((b[0]+b[1]/z+b[2]/z**2)/(1+a[1]/z+a[2]/z**2))
        g=abs(b[0])*np.prod([abs(z-zz) for zz in zk])/np.prod([abs(z-pp) for pp in pk])
        print(f"   {fq:>8} {H:>12.6f} {g:>12.6f} {H-g:>+10.2e}")

print("\n" + "="*94)
print("② 稳定性判据实测（修正：不 break，跑满 3 秒看末尾幅值）")
print("="*94)
print(f"   {'极点 p':>9} {'|p|':>9} {'3秒后|y|max':>15} {'判定':>12}")
for p in [0.5,0.9,0.99,0.999,0.9999,1.0,1.0001,1.001,1.01,1.1]:
    n=int(48000*3); yp=0.0; peak=0.0
    for i in range(n):
        x=1.0 if i==0 else 0.0
        yp=x+p*yp
        if i>=n-4800: peak=max(peak,abs(yp))
        if not np.isfinite(yp) or abs(yp)>1e30: peak=float('inf'); break
    v = "✅ 稳定" if peak<1e-3 else ("⚠️ 临界(不衰减)" if peak<10 else "❌ 发散")
    print(f"   {p:>9.4f} {abs(p):>9.4f} {peak:>15.4e} {v:>12}")

print("\n" + "="*94)
print("③ 二阶系统稳定性：|a2|<1 且 |a1|<1+a2  （三角形稳定区）")
print("="*94)
print(f"   {'a1':>7} {'a2':>7} {'|a2|<1':>7} {'|a1|<1+a2':>10} {'|极点|max':>10} {'实测':>8} {'一致':>6}")
for a1,a2 in [(0.0,0.0),(-1.0,0.5),(1.0,0.5),(-1.5,0.7),(1.5,0.7),(-1.9,0.95),(1.9,0.95),(0.0,1.0),(0.0,1.01),(-2.0,1.0)]:
    n=48000*2; y1=y2=0.0; peak=0.0
    for i in range(n):
        x=1.0 if i==0 else 0.0
        y=x-a1*y1-a2*y2; y2=y1; y1=y
        if i>=n-4800: peak=max(peak,abs(y))
        if not np.isfinite(y) or abs(y)>1e30: peak=float('inf'); break
    c1=abs(a2)<1; c2=abs(a1)<1+a2
    r=np.abs(np.roots([1.0,a1,a2])).max() if a2!=0 else abs(-a1)
    meas = peak<1e-3
    print(f"   {a1:>7.2f} {a2:>7.2f} {str(c1):>7} {str(c2):>10} {r:>10.4f} {('稳定' if meas else '发散'):>8} {'✅' if meas==(c1 and c2) else '❌':>6}")
