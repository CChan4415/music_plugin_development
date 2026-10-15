import numpy as np
SR=48000.0
def butter_p(N,fc,sr=SR):
    k=np.arange(N); p=np.exp(1j*np.pi*(2*k+N+1)/(2*N))
    return 2.0*sr*np.tan(np.pi*fc/sr)*p
def to_digital(p,N,sr=SR,dc=1.0):
    K=2.0*sr; pd=(K+p)/(K-p)
    a=np.real(np.poly(pd)); b=np.real(np.poly(-np.ones(N)))
    b=b*(dc/np.sum(b)*np.sum(a)); return b/a[0],a/a[0]

def sos_from_ba(b,a):
    """稳健分解：极点按共轭配对；每节取【与极点数相同】的零点（关键！）"""
    total_dc=np.sum(b)/np.sum(a)
    pk=list(np.roots(a)); zk=list(np.roots(b)); sos=[]
    while pk:
        p=pk.pop(0); pp=[p]
        if abs(p.imag)>1e-9 and pk:
            j=int(np.argmin([abs(q-np.conj(p)) for q in pk])); pp.append(pk.pop(j))
        zp=[]
        for _ in range(len(pp)):
            if zk: zp.append(zk.pop(0))
        b2=np.real(np.poly(zp)) if zp else np.array([1.0])
        a2=np.real(np.poly(pp))
        b2=np.concatenate([b2,np.zeros(max(0,3-len(b2)))])
        a2=np.concatenate([a2,np.zeros(max(0,3-len(a2)))])
        b2=b2/a2[0]; a2=a2/a2[0]
        s=b2.sum()/a2.sum()
        sos.append((b2/s,a2))
    b2,a2=sos[0]; sos[0]=(b2*total_dc,a2)
    return sos,total_dc

def run_direct(b,a,x,dtype):
    b=np.asarray(b,dtype=dtype); a=np.asarray(a,dtype=dtype); N=len(a)-1
    xs=np.zeros(N,dtype=dtype); ys=np.zeros(N,dtype=dtype); y=np.zeros(len(x),dtype=dtype)
    for n in range(len(x)):
        xn=dtype(x[n]); acc=dtype(0)
        for i in range(len(b)): acc=dtype(acc+dtype(b[i]*(xn if i==0 else xs[i-1])))
        for i in range(1,len(a)): acc=dtype(acc-dtype(a[i]*ys[i-1]))
        y[n]=acc
        if N: xs[1:]=xs[:-1]; xs[0]=xn; ys[1:]=ys[:-1]; ys[0]=acc
    return y.astype(np.float64)

def run_sos(sos,x,dtype):
    y=np.asarray(x,dtype=dtype)
    for b2,a2 in sos:
        b2=np.asarray(b2,dtype=dtype); a2=np.asarray(a2,dtype=dtype)
        z1=dtype(0); z2=dtype(0); out=np.zeros(len(y),dtype=dtype)
        for n in range(len(y)):
            xn=y[n]; acc=dtype(b2[0]*xn+z1)
            z1=dtype(b2[1]*xn-dtype(a2[1]*acc)+z2)
            z2=dtype(b2[2]*xn-dtype(a2[2]*acc))
            out[n]=acc
        y=out
    return y.astype(np.float64)

print("="*102)
print("① SOS 分解正确性校验（float64）")
print("="*102)
for N in [2,4,6,8,12]:
    b,a=to_digital(butter_p(N,1000),N); sos,_=sos_from_ba(b,a)
    n=1<<12; imp=np.zeros(n); imp[0]=1.0
    hd=run_direct(b,a,imp,np.float64); hs=run_sos(sos,imp,np.float64)
    print(f"   N={N}: 直接型DC={hd.sum():.10f}  SOS DC={hs.sum():.10f}  逐点最大差={np.abs(hd-hs).max():.3e}  {'✅' if np.abs(hd-hs).max()<1e-8 else '❌'}")

print("\n" + "="*102)
print("② ⭐ float32：直接型 vs 级联二阶节（Butterworth LP fc=1000Hz @48kHz）")
print("="*102)
print(f"   {'N':>3} {'biquad':>7} {'直接型 DC增益':>20} {'SOS DC增益':>12} {'直接型':>10} {'SOS':>9}")
for N in [2,4,6,8,10,12,16,20,24]:
    b,a=to_digital(butter_p(N,1000),N); sos,_=sos_from_ba(b,a)
    n=1<<13; imp=np.zeros(n); imp[0]=1.0
    hd=run_direct(b,a,imp,np.float32); hs=run_sos(sos,imp,np.float32)
    dcd=hd.sum(); dcs=hs.sum()
    okd='✅ 正常' if np.isfinite(dcd) and abs(dcd-1)<0.05 else '❌ 已坏'
    oks='✅ 正常' if np.isfinite(dcs) and abs(dcs-1)<0.05 else '❌ 已坏'
    print(f"   {N:>3} {len(sos):>7} {dcd:>20.6f} {dcs:>12.6f} {okd:>10} {oks:>9}")

print("\n" + "="*102)
print("③ N=8 float32 频响误差（以 float64 为参考）")
print("="*102)
N=8; b,a=to_digital(butter_p(N,1000),N); sos,_=sos_from_ba(b,a)
n=1<<14; imp=np.zeros(n); imp[0]=1.0
ref=np.abs(np.fft.rfft(run_direct(b,a,imp,np.float64),1<<16))
hd=np.abs(np.fft.rfft(run_direct(b,a,imp,np.float32),1<<16))
hs=np.abs(np.fft.rfft(run_sos(sos,imp,np.float32),1<<16))
f=np.fft.rfftfreq(1<<16,1/SR)
print(f"   {'频率Hz':>8} {'float64':>11} {'直接型f32':>12} {'SOS f32':>11} {'直接型误差dB':>13} {'SOS误差dB':>11}")
for fq in [100,500,1000,2000,5000,10000]:
    i=np.argmin(np.abs(f-fq))
    r=20*np.log10(ref[i]+1e-30); d=20*np.log10(hd[i]+1e-30); s=20*np.log10(hs[i]+1e-30)
    print(f"   {fq:>8} {r:>11.4f} {d:>12.4f} {s:>11.4f} {d-r:>+13.4f} {s-r:>+11.4f}")

print("\n" + "="*102)
print("④ 根因：分母系数动态范围 vs 阶数")
print("="*102)
print(f"   {'N':>3} {'|a|max':>11} {'|a|min':>11} {'max/min':>11} {'float32 损失位数':>17}")
for N in [2,4,6,8,10,12,16,20]:
    b,a=to_digital(butter_p(N,1000),N)
    r=np.abs(a).max()/np.abs(a[a!=0]).min()
    print(f"   {N:>3} {np.abs(a).max():>11.3e} {np.abs(a[a!=0]).min():>11.3e} {r:>11.3e} {np.log2(r):>17.1f} bit")
