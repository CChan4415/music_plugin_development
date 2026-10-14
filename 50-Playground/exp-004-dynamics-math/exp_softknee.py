"""软膝 soft knee 的数值验证 —— 为 30-Wiki/DSP/软膝 soft knee.md 提供实测数据。"""
import numpy as np

def gr_hard(x, T, R):
    s = 1.0/R - 1.0
    return np.where(x > T, s*(x-T), 0.0)

def gr_quad(x, T, R, W):
    """标准二次软膝。膝跨 [T-W/2, T+W/2]"""
    s = 1.0/R - 1.0
    d = x - T
    return np.where(2*d < -W, 0.0,
           np.where(2*d <= W, s*(d + W*0.5)**2/(2*W), s*d))

def gr_hermite(x, T, R, W):
    """Hermite 三次插值: y(0)=0, y'(0)=0, y(1)=sW/2, y'(1)=sW  (u 域)"""
    s = 1.0/R - 1.0
    u = (x - T + W*0.5)/W
    h01 = -2*u**3 + 3*u**2
    h11 =  u**3 -  u**2
    y = h01*(s*W*0.5) + h11*(s*W)
    return np.where(u < 0, 0.0, np.where(u <= 1, y, s*(x-T)))

def gr_softplus(x, T, R, W):
    """softplus 膝: 一阶导 = slope * sigmoid(2d/W)。C^inf，但永远不为 0"""
    s = 1.0/R - 1.0
    z = 2.0*(x - T)/W
    sp = np.maximum(z, 0.0) + np.log1p(np.exp(-np.abs(z)))   # 数值稳定
    return s*(W*0.5)*sp

T, R, W = -20.0, 4.0, 12.0
s = 1.0/R - 1.0
lo, hi = T - W/2, T + W/2

print("=== 1. 二次软膝 是否等于 Hermite 三次插值？ ===")
xs = np.linspace(lo, hi, 20001)   # ← 只在膝内比较（膝外 hermite 用 clip，quad 用线性外推）
d = np.max(np.abs(gr_quad(xs,T,R,W) - gr_hermite(xs,T,R,W)))
print(f"   膝内 max|quad - hermite| = {d:.3e}")
print("   → 恒等。二次软膝 就是 Hermite 边界条件下的解，天然 C1，不需要三次项")
print("   → 教科书里的『三次软膝』通常指的是别的边界条件，或就是同一个东西的误称\n")

print("=== 2. 边界连续性断言 (T=-20, R=4, W=12) ===")
checks = [
    ("膝下边界 quad(T-W/2) == 0",      gr_quad(np.array([lo]),T,R,W)[0], 0.0),
    ("膝上边界 quad(T+W/2) == s*W/2",  gr_quad(np.array([hi]),T,R,W)[0], s*W/2),
    ("膝外上方 quad(T+W) == s*W/2*2",  gr_quad(np.array([T+W]),T,R,W)[0], s*W),
]
for name, got, want in checks:
    print(f"   {name:<34} 实测 {got:>14.10f}  理论 {want:>14.10f}  {'✅' if abs(got-want)<1e-12 else '❌'}")
print(f"   硬膝在 x=T 处跳变: 左={gr_hard(np.array([T-1e-9]),T,R)[0]:.6f} 右={gr_hard(np.array([T+1e-9]),T,R)[0]:.6f}  ← 折点\n")

print("=== 3. 一阶导连续性（中心差分 h=1e-6，单位 dB/dB） ===")
h = 1e-6
for name, fn in [("hard", lambda t: gr_hard(np.array([t]),T,R)[0]),
                 ("quad", lambda t: gr_quad(np.array([t]),T,R,W)[0]),
                 ("softplus", lambda t: gr_softplus(np.array([t]),T,R,W)[0])]:
    dl = (fn(lo+h)-fn(lo-h))/(2*h); dc = (fn(T+h)-fn(T-h))/(2*h); dh = (fn(hi+h)-fn(hi-h))/(2*h)
    print(f"   {name:>9}: f'(T-W/2)={dl:>9.5f}  f'(T)={dc:>9.5f}  f'(T+W/2)={dh:>9.5f}   硬膝斜率={s}")
print("   → quad 两端导数 0 与 slope 都精确接上（C1）；softplus 永远不为 0，没有『不压缩』区\n")

print("=== 4. 膝宽 W 如何改变 GR（T=-20, R=4, 二次膝） ===")
print(f"   {'输入dB':>7} " + "".join(f"{('W='+str(w)):>10}" for w in [0,3,6,12,20,30]))
for xin in [-30, -26, -23, -20, -17, -14, -8]:
    row = [gr_hard(np.array([xin]),T,R)[0]] + [gr_quad(np.array([xin]),T,R,w)[0] for w in [3,6,12,20,30]]
    print(f"   {xin:>7} " + "".join(f"{v:>10.3f}" for v in row))
print()

print("=== 5. 软膝的『有效阈值偏移』—— 解析公式 vs 实测 ===")
print("   膝内 |GR| = |s|(d+W/2)^2/(2W)  ⟹  达到 |GR|=g 需要 d = -W/2 + sqrt(2Wg/|s|)")
for w in [3, 6, 12, 20]:
    row = []
    for g in [0.5, 1.0, 3.0]:
        d_theory = -w/2 + np.sqrt(2*w*g/abs(s))
        # 数值求解
        xx = np.linspace(T-40, T+10, 400001)
        gv = gr_quad(xx,T,R,w)
        d_num = xx[np.argmin(np.abs(gv+g))] - T
        row.append(f"|GR|={g}: 理论{T+d_theory:>7.3f} 实测{T+d_num:>7.3f}")
    print(f"   W={w:>2}dB  " + " | ".join(row))
print("   → 把 threshold 定义为膝中心时，W=12 的软膝在 x=T 处已压 1.125 dB，")
print("     在 x=T-22 处（阈值以下 2 dB）就已压 0.5 dB —— 这就是『参数照抄却更狠』\n")

print("=== 6. 膝形状的听感差异：同一 GR 深度下的斜率变化率 ===")
for name, fn in [("quad", lambda t: gr_quad(np.array([t]),T,R,W)[0]),
                 ("softplus", lambda t: gr_softplus(np.array([t]),T,R,W)[0])]:
    g = fn(np.linspace(lo,hi,9))
    print(f"   {name:>9} 膝内 GR 序列: " + " ".join(f"{v:6.3f}" for v in g))
