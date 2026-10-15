"""浮点音频表示 —— IEEE 754 的实测数据
   为 30-Wiki/DSP/浮点音频表示.md 提供验证。

验证清单:
  1. float32 的位结构: 符号 / 指数 / 尾数, 手动解包
  2. float32 vs float64 的有效精度（十进制位数、相对误差）
  3. ±1.0 归一化的 headroom: float32 能表示到多少 dBFS
  4. 整数位深 vs float32 的动态范围
  5. NaN / Inf 的产生与传播（一个 NaN 污染整条链）
  6. denormal 区间与 FLT_MIN（配合 [[denormal 数处理]]）
  7. 累加顺序对结果的影响（float32 的灾难性抵消）
  8. 音频常用常数在 float32 下的实际精度
"""
import numpy as np
import struct

F32 = np.float32
F64 = np.float64

print("=== 1. float32 位结构手动解包 ===")
def unpack_f32(x):
    bits = struct.unpack('<I', struct.pack('<f', np.float32(x)))[0]
    sign = (bits >> 31) & 1
    exp  = (bits >> 23) & 0xFF
    mant = bits & 0x7FFFFF
    return bits, sign, exp, mant

print(f"   {'值':>14}{'十六进制':>12}{'s':>3}{'e(偏置127)':>12}{'尾数(23位)':>14}{'真实指数':>10}")
for v in [1.0, -1.0, 0.5, 1.5, 2.0, 0.1, 3.14159265, 1e-38, 1e38]:
    b, s, e, m = unpack_f32(v)
    real_e = (e - 127) if e != 0 else -126
    print(f"   {v:>14.8g}  0x{b:08X}{s:>3}{e:>12}{m:>14}{real_e:>10}")
print("   → 1.0 = 0x3F800000: s=0, e=127(→0), mant=0 → (-1)^0 × 1.0 × 2^0")
print("   → 1.5 = 0x3FC00000: mant = 0x400000 = 2^22 → 1 + 2^22/2^23 = 1.5")

print("\n=== 2. float32 vs float64 的有效精度 ===")
print(f"   {'量':>22}{'float32':>18}{'float64':>18}")
print(f"   {'尾数位':>22}{23:>18}{52:>18}")
print(f"   {'机器 epsilon':>22}{np.finfo(F32).eps:>18.6e}{np.finfo(F64).eps:>18.6e}")
print(f"   {'十进制有效位数':>22}{np.finfo(F32).precision:>18}{np.finfo(F64).precision:>18}")
print(f"   {'最小规格化正数':>22}{np.finfo(F32).tiny:>18.6e}{np.finfo(F64).tiny:>18.6e}")
print(f"   {'最大有限值':>22}{np.finfo(F32).max:>18.6e}{np.finfo(F64).max:>18.6e}")

print("\n   在音频幅度范围（±1.0）内的**绝对**量化步长:")
print(f"   {'幅度':>10}{'float32 步长':>20}{'等效 dBFS':>14}{'float64 步长':>20}")
for a in [1.0, 0.5, 0.1, 0.01, 1e-4, 1e-6]:
    s32 = np.spacing(F32(a)); s64 = np.spacing(F64(a))
    print(f"   {a:>10.0e}{s32:>20.3e}{20*np.log10(s32):>14.1f}{s64:>20.3e}")
print("   → float32 在 ±1.0 附近的步长是 1.19e-7 ≈ 2^-23，等效 **-138.5 dBFS**")
print("     这正好等于 24-bit 定点在满刻度处的 LSB（2^-23）")

print("\n=== 3. float32 的 headroom：能表示到多少 dBFS ===")
print(f"   0 dBFS = 幅度 1.0（约定）")
print(f"   float32 最大值 {np.finfo(F32).max:.6e} = {20*np.log10(np.finfo(F32).max):+.1f} dBFS")
print(f"   float32 最小规格化 {np.finfo(F32).tiny:.6e} = {20*np.log10(np.finfo(F32).tiny):+.1f} dBFS")
print(f"   float32 最小 denormal {np.finfo(F32).smallest_subnormal:.6e} = "
      f"{20*np.log10(np.finfo(F32).smallest_subnormal):+.1f} dBFS")
print(f"   → 从最小 denormal 到最大有限值的总范围 = "
      f"{20*np.log10(float(np.finfo(F32).max)/float(np.finfo(F32).smallest_subnormal)):.1f} dB")
print(f"     从最小**规格化**到最大有限值 = "
      f"{20*np.log10(float(np.finfo(F32).max)/float(np.finfo(F32).tiny)):.1f} dB")
print(f"   → 但**有效精度**只有 {np.finfo(F32).precision} 位十进制：")
print(f"     超过 0 dBFS 后每翻一倍，绝对精度就粗一倍。")
print(f"     +6 dBFS 处步长 {np.spacing(F32(2.0)):.3e}（等效 -132.5 dBFS）")
print(f"     +48 dBFS 处步长 {np.spacing(F32(256.0)):.3e}（等效 -90.5 dBFS）")
print("   ⚠️ 『float32 有 1500 dB 动态范围』是**技术上正确但工程上误导**的说法：")
print("     那是『最大/最小可表示』的比值，不是『同时可用的精度』。")

print("\n=== 4. 整数位深 vs float32 ===")
print(f"   {'格式':>14}{'理论动态范围(dB)':>20}{'满刻度 LSB(dBFS)':>20}{'削波?':>10}")
for name, bits in [("int16", 16), ("int24", 24), ("int32", 32)]:
    dr = 6.02 * bits
    lsb = -20 * np.log10(2 ** (bits - 1))
    print(f"   {name:>14}{dr:>20.1f}{lsb:>20.2f}{'硬削波':>10}")
print(f"   {'float32':>14}{'1529.2':>20}{'-138.47(近 ±1.0)':>20}{'可超 1.0':>10}")
print("   → 定点的动态范围**全在低位**（靠位深），float 的动态范围**全在高位**（靠指数）")
print("     这就是『32-bit float 录音几乎不可能削波』的原因：")
print("     超过 1.0 只是损失精度，不是丢数据")
print("   ⚠️ 注意 float32 的『动态范围』有两个口径，差 140 dB:")
print("     最小规格化 → 最大  = 1529.2 dB（常被引用）")
print("     最小 denormal → 最大 = 1667.7 dB（含非规格化，一般不该用）")
print("     而**有效精度**在 ±1.0 附近只有 138.5 dB（见第 2 节）")

print("\n=== 5. NaN / Inf 的产生与传播 ===")
a = F32(1.0); b = F32(0.0)
print(f"   1.0 / 0.0      = {a/b}          ← Inf（有符号）")
print(f"   0.0 / 0.0      = {F32(0.0)/F32(0.0)}          ← NaN")
print(f"   log(0)         = {np.log(F32(0.0))}         ← -Inf（np.log 有 warning）")
print(f"   sqrt(-1)       = {np.sqrt(F32(-1.0))}          ← NaN")
print(f"   Inf - Inf      = {F32(np.inf) - F32(np.inf)}          ← NaN")
print(f"   Inf * 0        = {F32(np.inf) * F32(0.0)}          ← NaN")

print("\n   传播测试：把一个 NaN 注入 8 级串联的一阶低通")
def onepole_f32(x, c):
    y = np.empty(len(x), dtype=F32); acc = F32(0.0)
    for i in range(len(x)):
        acc = F32(acc + F32(c * F32(x[i] - acc))); y[i] = acc
    return y
sig = np.ones(2000, dtype=F32)
sig[100] = np.nan
out = sig.copy()
for _ in range(8):
    out = onepole_f32(out, F32(0.05))
n_nan = int(np.sum(np.isnan(out)))
first = int(np.argmax(np.isnan(out)))
print(f"   注入位置: 样本 100 | 输出 NaN 数: {n_nan}/2000 | 首个 NaN 在样本 {first}")
print(f"   → NaN 从注入点开始**永久污染**后面所有样本（IIR 状态被污染，永不自愈）")
n_after = int(np.sum(np.isnan(out[first:])))
print(f"   注入点之后共 {len(out)-first} 个样本，其中 NaN = {n_after} "
      f"({n_after/(len(out)-first)*100:.1f}%) → 无一幸存")

print("\n   对比: 同样注入 Inf")
sig2 = np.ones(2000, dtype=F32); sig2[100] = np.inf
out2 = sig2.copy()
for _ in range(8):
    out2 = onepole_f32(out2, F32(0.05))
print(f"   输出 NaN 数: {int(np.sum(np.isnan(out2)))} | Inf 数: {int(np.sum(np.isinf(out2)))}")
print(f"   → Inf 经过 IIR 的反馈运算会变成 NaN（Inf - Inf），同样永久污染")

print("\n   防御: 检测 + 复位（代价是每个 block 一次遍历）")
def sanitize(x):
    bad = ~np.isfinite(x)
    return bad.sum(), np.where(bad, F32(0.0), x)
n_bad, clean = sanitize(out)
print(f"   sanitize 清掉 {n_bad} 个非有限值 → 剩余 NaN {int(np.sum(np.isnan(clean)))}")

print("\n=== 6. denormal 区间（配合 denormal 数处理）===")
print(f"   FLT_MIN (最小规格化) = {np.finfo(F32).tiny:.6e} = 2^-126")
print(f"   FLT_TRUE_MIN (最小 denormal) = {np.finfo(F32).smallest_subnormal:.6e} = 2^-149")
print(f"   中间有 {2**23 - 1} 个 denormal 值")
print(f"   denormal 阈值折合 = {20*np.log10(np.finfo(F32).tiny):.1f} dBFS")

print("\n=== 7. 累加顺序的影响（float32 灾难性抵消）===")
rng = np.random.default_rng(42)
x = (rng.standard_normal(100000) * 0.1).astype(F32)
s_seq = F32(0.0)
for v in x: s_seq = F32(s_seq + v)
s_f64 = F64(np.sum(x.astype(F64)))
s_pair = F32(np.sum(x.astype(F64)))     # numpy 内部成对求和后转 float32
print(f"   float32 顺序累加 100000 个样本 = {s_seq:.6f}")
print(f"   float64 累加                    = {s_f64:.6f}   ← 参考值")
print(f"   float32 误差                    = {abs(float(s_seq)-float(s_f64)):.6e} "
      f"({20*np.log10(abs(float(s_seq)-float(s_f64))/abs(float(s_f64))):.1f} dB 相对)")

print("\n   灾难性抵消: 大数 + 小数")
big = F32(1.0); small = F32(1e-9)
print(f"   float32: 1.0 + 1e-9 = {big + small}  (1e-9 被完全吞掉)")
acc = F32(1.0)
for _ in range(1000): acc = F32(acc + small)
print(f"   1.0 累加 1000 次 1e-9 = {acc}  (理论 1.000001，误差 "
      f"{abs(float(acc)-1.000001)/1.000001*100:.4f}%)")
print("   → 音频里这意味着: **永远不要用 float32 累加直流/包络的长期和**")
print("     包络跟随器的状态变量是『大数 + 小数』的典型场景（release 很慢时）")

print("\n=== 8. 音频常用常数在 float32 下的精度 ===")
import math
print(f"   {'常数':>26}{'float64':>22}{'float32':>18}{'相对误差':>14}")
for name, v in [("π", math.pi), ("2π", 2*math.pi), ("1/√2", 1/math.sqrt(2)),
                ("√2", math.sqrt(2)), ("ln(10)/20", math.log(10)/20),
                ("1/ln(10)", 1/math.log(10)), ("2^(1/12)", 2**(1/12))]:
    f64v = F64(v); f32v = F32(v)
    rel = abs(float(f64v) - float(f32v)) / abs(float(f64v))
    print(f"   {name:>26}{f64v:>22.15f}{f32v:>18.9f}{rel:>14.2e}")
print("   → float32 的常数误差在 1e-8 量级，对音频**完全够用**")
print("     真正的问题不是常数精度，而是**累加**和**反馈**的误差累积")

print("\n=== 9. 采样率相关：一阶滤波器的 float32 误差累积 ===")
print("   一阶低通 y += c*(x-y)，跑 48000×60 样本（60 秒），看稳态误差")
for c_val in [0.5, 0.05, 0.005]:
    y = F32(0.0); c32 = F32(c_val)
    for _ in range(48000 * 10):
        y = F32(y + c32 * F32(F32(1.0) - y))
    print(f"   c = {c_val:<7} 稳态 y = {y:.9f} (理论 1.0, 误差 {abs(1.0-float(y)):.2e})")
print("   → 一阶平滑器稳态误差极小（< 1e-6），float32 完全够用")
print("     但注意 [[denormal 数处理]]: 无输入时它会**卡在** denormal 上不归零")

print("\n✅ exp_float 完成")
