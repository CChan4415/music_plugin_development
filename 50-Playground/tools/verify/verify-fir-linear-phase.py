import numpy as np
SR=48000.0; NFFT=1<<16
def fir_lp(N,fc,sr=SR,win='hamming'):
    n=np.arange(N); M=(N-1)/2
    h=np.sinc(2*fc/sr*(n-M))*2*fc/sr
    return h*{'hamming':np.hamming,'hann':np.hanning,'blackman':np.blackman,'rect':np.ones}[win](N)
def butter_lp(N,fc,sr=SR):
    k=np.arange(N); p=np.exp(1j*np.pi*(2*k+N+1)/(2*N))
    K=2.0*sr; W=K*np.tan(np.pi*fc/sr)
    pd=(K+W*p)/(K-W*p); g=W**N/np.prod(K-W*p)
    b=np.real(g*np.poly(-np.ones(N))); a=np.real(np.poly(pd))
    return b/a[0], a/a[0]
def iir_ir(b,a,n):
    y=np.zeros(n); xs=np.zeros(len(b)-1); ys=np.zeros(len(a)-1); x=np.zeros(n); x[0]=1.0
    for i in range(n):
        acc=b[0]*x[i]
        for j in range(1,len(b)): acc+=b[j]*xs[j-1]
        for j in range(1,len(a)): acc-=a[j]*ys[j-1]
        y[i]=acc
        if len(xs): xs[1:]=xs[:-1]; xs[0]=x[i]
        if len(ys): ys[1:]=ys[:-1]; ys[0]=acc
    return y

print("="*94)
print("① 线性相位残差（只在通带内测：f < fc/2）")
print("="*94)
fc=4000
print(f"   {'N':>5} {'延迟':>7} {'通带残差 max|°|':>16} {'结论':>20}")
for N in [11,21,51,101,201,501]:
    h=fir_lp(N,fc)
    H=np.fft.rfft(h,NFFT); f=np.fft.rfftfreq(NFFT,1/SR)
    res=np.degrees(np.angle(H*np.exp(1j*2*np.pi*f/SR*(N-1)/2)))
    b=(f>20)&(f<fc/2)
    print(f"   {N:>5} {(N-1)/2:>7.0f} {np.abs(res[b]).max():>16.8f} {'✅ 严格线性相位' if np.abs(res[b]).max()<1e-6 else '⚠️':>20}")
b4,a4=butter_lp(4,fc); h4=iir_ir(b4,a4,1<<14)
H4=np.fft.rfft(h4,NFFT); f=np.fft.rfftfreq(NFFT,1/SR)
ph=np.unwrap(np.angle(H4)); gd=-np.gradient(ph,2*np.pi*f/SR)
M=gd[np.argmin(np.abs(f-100))]
res4=np.degrees(np.angle(H4*np.exp(1j*2*np.pi*f/SR*M))); b=(f>20)&(f<fc/2)
print(f"   {'IIR N=4':>5} {M:>7.2f} {np.abs(res4[b]).max():>16.3f} {'❌ 非线性相位':>20}")

print("\n" + "="*94)
print("② 相位失真怎么变成『瞬态被抹掉』：方波前后沿对比")
print("="*94)
n=512; sq=np.zeros(n); sq[100:300]=1.0
def apply(h,x): return np.convolve(x,h)[:len(x)]
h101=fir_lp(101,4000)
yf=apply(h101,sq); yi=apply(h4,sq)
print(f"   {'信号':>12} {'上升沿 10%→90% 时间(样本)':>24} {'过冲':>8}")
def edge(y):
    i=np.argmax(y>0.1); j=np.argmax(y>0.9); return j-i, (y.max()-1.0)*100
for nm,y in [('原始方波',sq),('FIR 101 抽头',yf),('IIR 4阶 Butter',yi)]:
    e,ov=edge(y); print(f"   {nm:>12} {e:>24} {ov:>7.1f}%")

print("\n" + "="*94)
print("③ 因果性代价：FIR 的延迟必须被补偿，否则多轨会错位")
print("="*94)
print(f"   101 抽头 @48kHz → 延迟 {(101-1)/2/48:.4f} ms")
print(f"   在 120 BPM 下，一个 16 分音符 = {60000/120/4:.2f} ms → 延迟占 {(101-1)/2/48/(60000/120/4)*100:.3f}%")
print("   结论：单轨 EQ 无所谓；并联分频（crossover）必须两条路径延迟一致，否则分频点附近抵消")
