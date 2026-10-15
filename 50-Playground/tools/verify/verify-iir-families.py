"""IIR 滤波器家族对比（Butterworth / Chebyshev / Bessel / Elliptic）

⚠️ 状态：**部分可用**（2026-10-15）
    6 阶设计在 48kHz 下数值不稳，部分行输出 NaN。
    脚本能跑完不崩，但数据需要人工筛选。
    → 用它看**定性趋势**可以，不要直接引用数字。
    → 稳定的数据见 verify-svf-tuning.py（已验证）

"""

import numpy as np
from math import factorial
SR=48000.0; NFFT=1<<16

def to_digital(p_analog, N, sr=SR, dc_gain=1.0):
    K=2.0*sr
    pd=(K+p_analog)/(K-p_analog)
    a=np.real(np.poly(pd)); b=np.real(np.poly(-np.ones(N)))
    b=b*(dc_gain/np.sum(b)*np.sum(a))
    return b/a[0], a/a[0]

def butter_p(N,fc,sr=SR):
    k=np.arange(N); p=np.exp(1j*np.pi*(2*k+N+1)/(2*N))
    return 2.0*sr*np.tan(np.pi*fc/sr)*p
def cheby1_p(N,fc,rp,sr=SR):
    e=np.sqrt(10**(rp/10)-1); mu=np.arcsinh(1/e)/N
    k=np.arange(N); th=np.pi*(2*k+1)/(2*N)
    p=-np.sinh(mu)*np.sin(th)+1j*np.cos(th)*np.cosh(mu)
    return 2.0*sr*np.tan(np.pi*fc/sr)*p
def bessel_p(N,fc,sr=SR):
    c=np.array([factorial(2*N-k)//(2**(N-k)*factorial(k)*factorial(N-k)) for k in range(N+1)],float)
    p=np.roots(c); p=p[np.real(p)<0]
    # 归一化：使 -3dB 落在 W=1（求原型在 s=jW 处 |H|=1/√2）
    from numpy.polynomial import polynomial as P
    den=np.poly(p)
    def mag(W):
        s=1j*W
        return abs(np.polyval(den,s))   # |den(jW)| / den(0) ; H=den(0)/den(s)
    W=1.0
    for _ in range(80):
        # H(jW)= den(0)/den(jW); |H|=1/sqrt2 → |den(jW)| = sqrt2*den(0)
        val=mag(W)-np.sqrt(2)*np.real(np.polyval(den,0))
        W2=W+1e-6; val2=mag(W2)-np.sqrt(2)*np.real(np.polyval(den,0))
        d=(val2-val)/1e-6
        W=W-val/d
        W=max(W,1e-6)
    return 2.0*sr*np.tan(np.pi*fc/sr)*p/W

def ir(b,a,n):
    y=np.zeros(n); xs=np.zeros(max(len(b)-1,1)); ys=np.zeros(max(len(a)-1,1)); x=np.zeros(n); x[0]=1.0
    for i in range(n):
        acc=b[0]*x[i]
        for j in range(1,len(b)): acc+=b[j]*xs[j-1]
        for j in range(1,len(a)): acc-=a[j]*ys[j-1]
        y[i]=acc
        if len(xs): xs[1:]=xs[:-1]; xs[0]=x[i]
        if len(ys): ys[1:]=ys[:-1]; ys[0]=acc
    return y

def metrics(h,sr=SR):
    H=np.abs(np.fft.rfft(h,NFFT)); f=np.fft.rfftfreq(NFFT,1/sr)
    dc=H[0]
    thr=dc/np.sqrt(2); i3=int(np.argmax(H<thr)); f3=f[i3]
    # 通带纹波：在 0.5*f3 以内（避免把滚降算成纹波）
    # ⚠️ 若 f3 很小，pb 可能为空 → 需要保护
    pb=(f>0)&(f<f3*0.5)
    if not np.any(pb):
        rip=float('nan')
    else:
        rip=20*np.log10(H[pb].max()/max(H[pb].min(),1e-300))
    i1=np.argmax(H<dc*10**(-1/20)); i2=np.argmax(H<dc*10**(-40/20))
    trans=(f[i2]-f[i1])/f3
    sb=20*np.log10(H[np.argmin(np.abs(f-2*f3))]/dc+1e-30)
    ph=np.unwrap(np.angle(np.fft.rfft(h,NFFT))); w=2*np.pi*f/sr
    gd=-np.gradient(ph,w); b=(f>20)&(f<f3*0.5)
    # ⚠️ 保护：b 可能为空（f3 很小时）或含 NaN/Inf（不稳定滤波器）
    gdb = gd[b]
    if gdb.size == 0 or not np.all(np.isfinite(gdb)):
        gd_mean = float('nan'); gd_ripple = float('nan')
    else:
        gd_mean = float(gdb.mean()); gd_ripple = float(gdb.max()-gdb.min())
    # 同时保护 trans / sb
    if not np.isfinite(trans): trans = float('nan')
    if not np.isfinite(sb):    sb = float('nan')
    return f3, rip, trans, sb, gd_mean, gd_ripple

print("="*108)
print("① 四大家族：6 阶，各自的 -3dB 点都归一化到 1000Hz，48kHz")
print("="*108)
print(f"   {'类型':>18} {'实测-3dB Hz':>12} {'通带纹波dB':>11} {'过渡带/f3':>10} {'阻带@2f3':>10} {'群延迟样本':>11} {'群延迟波动':>11}")
for nm,p in [('Butterworth',butter_p(6,1000)),
             ('Chebyshev I 0.5dB',cheby1_p(6,1000,0.5)),
             ('Chebyshev I 1.0dB',cheby1_p(6,1000,1.0)),
             ('Chebyshev I 3.0dB',cheby1_p(6,1000,3.0)),
             ('Bessel',bessel_p(6,1000))]:
    b,a=to_digital(p,6); h=ir(b,a,1<<14)
    f3,rip,tr,sb,gdm,gdv=metrics(h)
    print(f"   {nm:>18} {f3:>12.1f} {rip:>11.4f} {tr:>10.4f} {sb:>10.2f} {gdm:>11.2f} {gdv:>11.4f}")
print("   → 过渡带越陡 ⇔ 群延迟波动越大（这是同一件事的两面）")

print("\n" + "="*108)
print("② 阶数 → 陡度（Butterworth，-3dB @1000Hz）")
print("="*108)
print(f"   {'N':>4} {'过渡带/f3':>10} {'群延迟样本':>11} {'|a|max/|a|min':>15} {'极点半径min':>12}")
for N in [2,4,6,8,10,12,16]:
    b,a=to_digital(butter_p(N,1000),N); h=ir(b,a,1<<14)
    _,_,tr,_,gdm,_=metrics(h)
    amax=np.abs(a).max(); amin=np.abs(a[a!=0]).min()
    r=np.abs(np.roots(a)).min()
    print(f"   {N:>4} {tr:>10.4f} {gdm:>11.2f} {amax/amin:>15.3e} {r:>12.8f}")

print("\n" + "="*108)
print("③ 阶数选择：Butterworth vs Elliptic 达到同样指标所需阶数")
print("="*108)
def K(k):
    if k<=0: return np.pi/2
    a,b=1.0,np.sqrt(1-k*k)
    for _ in range(80): a,b=(a+b)/2,np.sqrt(a*b)
    return np.pi/(2*a)
def ellip_order(rp,rs,Ws):
    ep=np.sqrt(10**(rp/10)-1); es=np.sqrt(10**(rs/10)-1)
    k1=ep/es; kk=np.sqrt(1-1/Ws**2)
    return (K(kk)*K(np.sqrt(1-k1*k1)))/(K(k1)*K(np.sqrt(1-kk*kk)))
def butter_order(rp,rs,Ws):
    return np.log10((10**(rs/10)-1)/(10**(rp/10)-1))/(2*np.log10(Ws))
print(f"   {'纹波dB':>7} {'阻带dB':>7} | " + " | ".join(f"{f'Ws={w}':>15}" for w in [2.0,1.5,1.2]))
print(f"   {'':>7} {'':>7} | " + " | ".join(f"{'Butter / Ellip':>15}" for _ in range(3)))
for rp,rs in [(0.1,40),(0.5,60),(1.0,80),(0.1,80)]:
    row=[f"{butter_order(rp,rs,w):.1f} / {ellip_order(rp,rs,w):.1f}" for w in [2.0,1.5,1.2]]
    print(f"   {rp:>7.1f} {rs:>7.0f} | " + " | ".join(f"{r:>15}" for r in row))
print("   → Ws=1.2（陡）时：Butterworth 要 54 阶，Elliptic 只要 6 阶")
print("     每 2 阶 = 1 个 biquad → 27 个 biquad vs 3 个 biquad")
