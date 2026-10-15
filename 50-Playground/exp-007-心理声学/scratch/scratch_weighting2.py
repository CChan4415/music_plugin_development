import numpy as np

def A(f):
    f=np.asarray(f,float); f2=f*f
    return 20*np.log10((12194.0**2*f2**2)/((f2+20.6**2)*np.sqrt((f2+107.7**2)*(f2+737.9**2))*(f2+12194.0**2)))+2.00
def B(f):
    f=np.asarray(f,float); f2=f*f
    return 20*np.log10((12194.0**2*f2*f)/((f2+20.6**2)*np.sqrt(f2+158.5**2)*(f2+12194.0**2)))+0.17
def C(f):
    f=np.asarray(f,float); f2=f*f
    return 20*np.log10((12194.0**2*f2)/((f2+20.6**2)*(f2+12194.0**2)))+0.06

print("=== 归一化自检（1 kHz 应为 0.00）===")
for n,fn in [('A',A),('B',B),('C',C)]: print(f"  {n}(1kHz) = {fn(1000.0):+.4f} dB")
f = np.array([10,20,31.5,50,63,100,125,200,250,400,500,800,1000,1250,2000,3150,4000,5000,8000,10000,12500,16000,20000],float)
print(f"\n{'f(Hz)':>8} {'A(dB)':>9} {'B(dB)':>9} {'C(dB)':>9}")
for hz,a,b,c in zip(f,A(f),B(f),C(f)): print(f"{hz:>8.1f} {a:>+9.2f} {b:>+9.2f} {c:>+9.2f}")
