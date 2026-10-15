import numpy as np
SR=48000.0
def f_from_fc(fc,sr=SR): return 2*np.sin(np.pi*fc/sr)
def pole_angle(f,q,sr=SR):
    tr=2-f*f-f*q; det=1-f*q
    if det<=0: return None
    c=tr/(2*np.sqrt(det))
    if abs(c)>1: return None
    return np.arccos(c)
def pole_freq(f,q,sr=SR):
    a=pole_angle(f,q,sr)
    return None if a is None else a*sr/(2*np.pi)

print("="*96)
print("① 为什么 f=2sin(π·fc/fs) 只在 Q=∞ 时精确")
print("   极点角满足 cos θ = (2−f²−fq)/(2√(1−fq))；代入 f=2sin(πfc/fs) 后")
print("   q=0 时右边 = 1−f²/2 = cos(2πfc/fs) ✅ 精确；q>0 时必然偏离")
print("="*96)
print(f"{'q=1/Q':>8} {'f=2sin(πfc/fs)':>16} {'cos θ (q>0)':>13} {'cos(2πfc/fs)':>13} {'θ 对应 Hz':>10} {'误差%':>8}")
fc=1000.0
for Q in [0.5,0.707,1.0,2.0,5.0,10.0,100.0,np.inf]:
    q=0.0 if np.isinf(Q) else 1.0/Q
    f=f_from_fc(fc); tr=2-f*f-f*q; det=1-f*q
    c=tr/(2*np.sqrt(det)); pf=np.arccos(np.clip(c,-1,1))*SR/(2*np.pi)
    print(f"{q:>8.4f} {f:>16.6f} {c:>13.6f} {np.cos(2*np.pi*fc/SR):>13.6f} {pf:>10.2f} {(pf-fc)/fc*100:>+8.2f}")

print("\n" + "="*96)
print("② 精确调谐：给定 fc 和 Q，反解 f（数值解）")
print("   目标 cos θ = cos(2πfc/fs) ⇒ f² + fq − 2 + 2c√(1−fq) = 0")
print("="*96)
def exact_f(fc,Q,sr=SR):
    c=np.cos(2*np.pi*fc/sr); q=1.0/Q
    lo,hi=0.0,min(2.0, np.sqrt(q*q+4)-q-1e-12)
    for _ in range(200):
        mid=(lo+hi)/2
        val=mid*mid+mid*q-2+2*c*np.sqrt(max(1-mid*q,0))
        if val<0: lo=mid
        else: hi=mid
    return (lo+hi)/2
print(f"{'fc':>7} {'Q':>7} {'f_approx':>10} {'f_exact':>10} {'差%':>8} {'极点(approx)':>13} {'极点(exact)':>12}")
for fc in [200,1000,5000,10000]:
    for Q in [0.707,1.0,2.0,10.0]:
        fa=f_from_fc(fc); q=1.0/Q
        fe=exact_f(fc,Q)
        pa=pole_freq(fa,q); pe=pole_freq(fe,q)
        # 极点角可能不存在（det<=0 或 |cos|>1）→ 用字符串占位
        pas = f"{pa:>13.2f}" if pa is not None else f"{'—':>13}"
        pes = f"{pe:>12.2f}" if pe is not None else f"{'—':>12}"
        print(f"{fc:>7} {Q:>7.3f} {fa:>10.5f} {fe:>10.5f} {(fe-fa)/fa*100:>+8.2f} {pas} {pes}")

print("\n" + "="*96)
print("③ 关键结论：Q 越高，2sin 近似越准；Q 低时误差可达 -12%")
print("="*96)
print(f"{'Q':>8} " + " ".join(f"{f'fc={x}Hz':>12}" for x in [200,1000,5000,10000]))
for Q in [0.5,0.707,1.0,2.0,5.0,10.0,50.0]:
    q=1.0/Q; row=[]
    for fc in [200,1000,5000,10000]:
        p=pole_freq(f_from_fc(fc),q)
        row.append(f"{(p-fc)/fc*100:>+11.2f}%" if p else f"{'n/a':>12}")
    print(f"{Q:>8.3f} " + " ".join(row))
