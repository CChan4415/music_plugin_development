import numpy as np, sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[2] / 'tools'))
from audio_io import db
SR=48000; D=1617; g=0.84

def G(w, damp, g=g, D=D):
    """环路增益 G(e^{jw})"""
    return g*(1-damp)/(1-damp*np.exp(-1j*w))*np.exp(-1j*w*D)

def pole_freq(k, damp, g=g, D=D):
    """解 angle(G)=0 (mod 2π) 找第 k 个极点频率（阻尼会把它从 k*fs/D 移开）"""
    f0 = k*SR/D
    lo, hi = f0 - SR/D*0.5, f0 + SR/D*0.5
    for _ in range(200):
        mid=(lo+hi)/2
        a=np.angle(G(2*np.pi*mid/SR, damp))
        if np.angle(G(2*np.pi*lo/SR,damp))*a <= 0: hi=mid
        else: lo=mid
    return (lo+hi)/2

def rt60_from_pole(fpole, damp, g=g, D=D):
    L=abs(G(2*np.pi*fpole/SR, damp))
    return -3.0*D/(SR*np.log10(L)), L

class C:
    def __init__(s,fb,damp): s.b=np.zeros(D);s.i=0;s.fb=fb;s.damp=damp;s.st=0.0
    def p(s,x):
        o=s.b[s.i]; s.st=o*(1-s.damp)+s.st*s.damp; s.b[s.i]=x+s.st*s.fb
        s.i=(s.i+1)%D; return o

def rt60_meas(fq,damp):
    c=C(g,damp)
    for n in range(int(SR*5)): c.p(np.sin(2*np.pi*fq*n/SR))
    need=int(SR*6)
    y=np.array([c.p(0.0) for _ in range(need)])
    nper=len(y)//D
    env=np.array([np.abs(y[k*D:(k+1)*D]).max() for k in range(nper)])
    e=db(env); t=np.arange(nper)*D/SR
    pk=e.max(); m=(e<pk-3)&(e>pk-40)
    if m.sum()<3: return float('nan')
    return -60.0/np.polyfit(t[m],e[m],1)[0]

print("="*84)
print("阻尼梳状：真正的极点频率 ≠ k·fs/D（阻尼滤波器的相位把极点推开了）")
print("="*84)
print(f"{'k':>3} {'k*fs/D':>9} | " + " | ".join(f"damp={d}: 极点Hz / RT60" for d in [0.0,0.6,0.9]))
for k in [1,10,100,400]:
    row=[]
    for damp in [0.0,0.6,0.9]:
        fp=pole_freq(k,damp); rt,L=rt60_from_pole(fp,damp)
        row.append(f"{fp:8.2f} / {rt:6.3f}s (L={L:.3f})")
    print(f"{k:>3} {k*SR/D:>9.2f} | " + " | ".join(row))

print("\n" + "="*84)
print("RT60 实测（在真正的极点频率上激励）vs 解析")
print("="*84)
print(f"{'damp':>5} {'k':>4} {'极点Hz':>9} {'|G|':>8} {'RT60解析':>9} {'RT60实测':>9} {'偏差%':>8}")
for damp in [0.0,0.6,0.9]:
    for k in [1,10,100,400]:
        fp=pole_freq(k,damp); th,L=rt60_from_pole(fp,damp); me=rt60_meas(fp,damp)
        print(f"{damp:>5.1f} {k:>4} {fp:>9.2f} {L:>8.4f} {th:>9.4f} {me:>9.4f} {(me-th)/th*100:>+8.2f}")

print("\n" + "="*84)
print("⚠️ 同一个 damp=0.9，若在 k·fs/D（而非真实极点）上激励，误差有多大")
print("="*84)
for k in [1,10,100,400]:
    fp=pole_freq(k,0.9); fnom=k*SR/D
    th,_=rt60_from_pole(fp,0.9); me=rt60_meas(fnom,0.9)
    print(f"   k={k:>4}: 极点 {fp:7.2f}Hz, 标称 {fnom:7.2f}Hz (偏 {fp-fnom:+6.2f}Hz) → 解析RT60 {th:.4f}s, 在标称频率测 {me:.4f}s ({((me-th)/th*100):+.0f}%)")

print("\n" + "="*84)
print("阻尼的核心效果：RT60 随频率（解析，在各 k 的真实极点上）")
print("="*84)
print(f"{'damp':>5} " + " ".join(f"{f'{k*SR/D:.0f}Hz':>10}" for k in [1,10,100,400]) + f"{'12k/30Hz':>10}")
for damp in [0.0,0.2,0.4,0.6,0.8]:
    rts=[rt60_from_pole(pole_freq(k,damp),damp)[0] for k in [1,10,100,400]]
    print(f"{damp:>5.1f} " + " ".join(f"{v:>10.4f}" for v in rts) + f"{rts[-1]/rts[0]:>10.3f}")
