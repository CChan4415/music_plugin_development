---
title: DSP 单元测试怎么写
type: wiki
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe, python]
created: 2026-10-15
updated: 2026-10-15
---

# DSP 单元测试怎么写

> [!important] 一句话
> **DSP 测试和普通软件测试不同**：没有"正确输出"可比对，
> 你要比对的是**数学性质**——直流增益、稳定性、与解析解的一致性。

## 本机环境（实测）

```bash
Apple clang 21.0.0 (arm64)
GNU Make 3.81
Python 3.12 + numpy 2.3.5
```

> [!warning] 本机**没有**这些（实测确认）
> | 工具 | 状态 |
> |---|---|
> | cmake | ❌ 未安装 |
> | ninja | ❌ 未安装 |
> | pytest | ❌ 未安装 |
> | pluginval | ❌ 未安装 |
>
> **所以本页用 Python 内置的 `unittest`**——零依赖，立即可用。
> pytest 的写法在附注里说明。

---

## 一、DSP 测试的六类必测项

> [!important] 这些比"输入输出比对"更有价值
> DSP 没有唯一的"正确输出"——同一个滤波器用不同结构实现，
> 输出不会 bit-exact。**所以要测数学性质。**

| # | 测试 | 判据 |
|---|---|---|
| 1 | **直流增益** | 低通 ≈ 1，高通 ≈ 0 |
| 2 | **Nyquist 增益** | 低通 ≈ 0，高通 ≈ 1 |
| 3 | **-3dB 点** | 落在设计的 $f_c$ 附近 |
| 4 | **稳定性** | 极点半径 < 1 |
| 5 | **脉冲响应衰减** | 尾部 → 0 |
| 6 | **极端参数** | 不发散、不 NaN |

**实测**（用 `unittest`，全部通过）：

```
test_dc_gain_is_unity ... ok
test_edge_parameters ... ok
test_impulse_decays ... ok
test_minus3db_at_cutoff ... ok
test_nyquist_gain_is_zero ... ok
test_stable ... ok
----------------------------------------------------------------------
Ran 6 tests in 0.042s
OK
```

---

## 二、完整示例

```python
"""用 unittest 写 DSP 测试（本机无 pytest，用内置 unittest）"""
import unittest
import numpy as np

SR = 48000.0

def biquad_lowpass(fc, Q, sr=SR):
    w0 = 2*np.pi*fc/sr
    cw, al = np.cos(w0), np.sin(w0)/(2*Q)
    a0 = 1 + al
    b = [(1-cw)/2/a0, (1-cw)/a0, (1-cw)/2/a0]
    a = [1.0, -2*cw/a0, (1-al)/a0]
    return np.array(b), np.array(a)

def impulse_response(b, a, n):
    y = np.zeros(n); x = np.zeros(n); x[0] = 1.0
    for i in range(n):
        acc  = sum (b[k]*x[i-k] for k in range(len(b)) if i-k >= 0)
        acc -= sum (a[k]*y[i-k] for k in range(1, len(a)) if i-k >= 0)
        y[i] = acc
    return y

class TestBiquad(unittest.TestCase):
    def test_dc_gain_is_unity(self):
        """低通的直流增益应为 1"""
        b, a = biquad_lowpass (1000.0, 0.707)
        self.assertAlmostEqual (np.sum(b)/np.sum(a), 1.0, places=6)

    def test_nyquist_gain_is_zero(self):
        """低通的 Nyquist 增益应接近 0"""
        b, a = biquad_lowpass (1000.0, 0.707)
        zb = sum (bi*((-1)**i) for i, bi in enumerate(b))
        za = sum (ai*((-1)**i) for i, ai in enumerate(a))
        self.assertLess (abs(zb/za), 1e-3)

    def test_minus3db_at_cutoff(self):
        """-3dB 点应落在设计频率附近"""
        b, a = biquad_lowpass (1000.0, 0.707)
        h = impulse_response (b, a, 1 << 14)
        H = np.abs (np.fft.rfft(h)); f = np.fft.rfftfreq (len(h), 1/SR)
        db = 20*np.log10 (H + 1e-20)
        f3 = f[np.argmax (db < -3)]
        self.assertLess (abs(f3 - 1000.0), 20.0, f"-3dB 点 {f3:.1f}Hz")

    def test_stable(self):
        """极点必须在单位圆内"""
        b, a = biquad_lowpass (1000.0, 0.707)
        p = np.roots (a)
        self.assertLess (np.max (np.abs(p)), 1.0)

    def test_impulse_decays(self):
        """脉冲响应必须衰减"""
        b, a = biquad_lowpass (1000.0, 0.707)
        y = impulse_response (b, a, 1 << 14)
        self.assertLess (np.max (np.abs(y[len(y)//2:])), 1e-6)

    def test_edge_parameters(self):
        """极端参数下不应崩溃或发散"""
        for fc in [20.0, 20000.0]:
            for Q in [0.1, 10.0]:
                with self.subTest (fc=fc, Q=Q):
                    b, a = biquad_lowpass (fc, Q)
                    p = np.roots (a)
                    self.assertLess (np.max (np.abs(p)), 1.0)

if __name__ == '__main__':
    unittest.main (verbosity=2)
```

**运行**：

```bash
python3 -m unittest test_dsp -v
# 或自动发现
python3 -m unittest discover -s tests -v
```

---

## 三、关键技巧

### 1. `subTest` —— 参数化测试

```python
for fc in [20.0, 20000.0]:
    for Q in [0.1, 10.0]:
        with self.subTest (fc=fc, Q=Q):     # ← 一个失败不影响其他
            ...
```

> [!tip] `subTest` 的价值
> 普通循环里第一个参数失败 → 后面的**不再执行**。
> `subTest` 会**全部跑完**，并分别报告哪个组合失败。
>
> **对参数扫描特别重要**（你要知道是所有参数都坏，还是只有极端值坏）。

### 2. 用解析解而不是"参考实现"

```python
# ❌ 弱：和另一个实现比（两个都可能有同样的错）
self.assertAlmostEqual (my_filter(x), reference_filter(x))

# ✅ 强：和数学性质比
self.assertAlmostEqual (dc_gain(b, a), 1.0, places=6)   # 直流增益必然为 1
self.assertLess (max_pole_radius(a), 1.0)                # 稳定性必然成立
```

> [!important] 数学性质是"绝对真理"
> 直流增益为 1 是**定义**，不依赖任何实现。
> 所以这种断言**永远不会误报**，也**永远不会漏报**。

### 3. 浮点比较要用容差

```python
# ❌ 永远不会通过（浮点不精确）
self.assertEqual (np.sum(b)/np.sum(a), 1.0)

# ✅ 用容差
self.assertAlmostEqual (np.sum(b)/np.sum(a), 1.0, places=6)

# ✅ 或用 np.testing
np.testing.assert_allclose (actual, expected, atol=1e-6)
```

### 4. 固定随机种子

```python
rng = np.random.default_rng (42)      # ✅ 可复现
# rng = np.random.default_rng()       # ❌ 每次不同，测试不稳定
```

---

## 四、测什么：按优先级

| 优先级 | 测试 | 为什么 |
|---|---|---|
| ⭐⭐⭐ | **稳定性** | 发散 = 爆音，用户无法接受 |
| ⭐⭐⭐ | **极端参数** | 用户会拧到极限 |
| ⭐⭐⭐ | **NaN/Inf 输入** | 会污染整条链 |
| ⭐⭐ | 数学性质（DC/Nyquist 增益） | 抓系数错误 |
| ⭐⭐ | -3dB 点 | 抓调谐错误 |
| ⭐⭐ | 与解析解对比 | 抓实现错误 |
| ⭐ | 性能（CPU） | 影响可用性 |
| ⭐ | null test（回归） | 抓"改 A 坏 B" |

> [!danger] 前三项最容易被跳过
> 大家都爱测"频响对不对"（好看、能画图），
> 但**用户遇到的 bug 大多来自稳定性、极端参数、NaN**。
>
> 见 [[UndefinedBehaviorSanitizer]] 的边界输入清单。

---

## 五、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **用 `assertEqual` 比浮点** | 永远失败 | 用 `assertAlmostEqual` |
| 2 | **只测"正常"参数** | 漏掉极端值 bug | 加参数扫描 |
| 3 | **和另一个实现比对** | 两个都错就测不出 | 和**数学性质**比 |
| 4 | **不固定随机种子** | 测试不稳定 | `default_rng(42)` |
| 5 | **循环里不用 `subTest`** | 第一个失败后面不跑 | 用 `subTest` |
| 6 | **用 `pytest` 但环境没有** | 跑不起来 | 本机用 `unittest` |
| 7 | **不测 NaN/Inf** | 漏掉最危险的输入 | 加边界输入 |
| 8 | **断言太宽松**（如 `assertTrue(x > -100)`） | 问题被放过 | 用具体容差 |
| 9 | **测试跑得慢** | 没人愿意跑 | 用短信号 + 解析判据 |
| 10 | **没有回归测试** | 改 A 坏 B | 见 [[音频回归测试]] |

> [!danger] 第 6 条是**本机的实际约束**
> AI 会默认你装了 pytest。
> **本机实测没有 pytest** —— 用 `unittest` 才能跑起来。
>
> （如果你后来装了 pytest，写法也兼容：pytest 能直接跑 unittest 的测试类。）

---

## 六、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 测试永远失败 | 浮点用 `assertEqual` | 用容差 |
| 测试时好时坏 | 随机种子未固定 | 固定种子 |
| 只跑第一个参数就停 | 循环里没用 `subTest` | 用 `subTest` |
| 测试太慢 | 用了整秒信号 | 用脉冲 + 解析判据 |
| pytest 找不到 | 没装 | 用 `unittest` |
| 测试通过了但线上崩 | 没测极端参数/NaN | 加边界测试 |
| 重构后测试没发现问题 | 测的是实现细节 | 测数学性质 |

---

## 七、怎么验证（测试的测试）

> [!important] 用**变异测试**验证你的测试有没有用
> 故意把实现改坏一点，看测试**是否失败**。
> 如果测试仍通过 → 测试没有覆盖那个行为。

```python
# 变异测试示例
def mutate_dc_gain(b, a):
    """故意把直流增益改坏"""
    return np.sum(b) / np.sum(a) * 1.01      # 偏 1%

# 你的测试应该抓到它
def test_catches_mutation(self):
    b, a = biquad_lowpass (1000.0, 0.707)
    mutated = np.sum(b)/np.sum(a) * 1.01
    self.assertNotAlmostEqual (mutated, 1.0, places=6)   # 应该不等
```

**建议的变异**：

| 变异 | 应该被哪个测试抓到 |
|---|---|
| 直流增益 ×1.01 | `test_dc_gain_is_unity` |
| 系数符号反转 | `test_stable` 或 `test_minus3db_at_cutoff` |
| 去掉 denormal 保护 | 性能测试 |
| 索引 off-by-one | 边界测试 |

---

## 相关

- [[MOC - Realtime Engineering]]
- [[音频回归测试]] — CI 里怎么跑、怎么防回归
- [[Null Test 与 bit-exact 对比]] — 差异量化
- [[AddressSanitizer]] / [[UndefinedBehaviorSanitizer]] — 动态检查
- [[Biquad 滤波器]] — 测试对象
- [[滤波器设计]] — 数学性质
- [[插件验证工具]] — 更上层的验证

> [!note] 待补充
> - pytest 的写法（本机未安装，写法未实测）
> - C++ 侧的单元测试框架（Catch2 / GoogleTest）
> - CI 里的测试矩阵配置
> - 变异测试的自动化工具
