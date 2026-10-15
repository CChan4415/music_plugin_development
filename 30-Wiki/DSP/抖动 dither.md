---
title: 抖动 dither
type: wiki
domain: dsp
status: solid
confidence: high
sources: ["[[Downey - Think DSP]]"]
tags: [math, recipe, gotcha]
created: 2026-10-15
updated: 2026-10-15
---

# 抖动 dither

> [!important] 一句话
> **降低位深时，故意加一点点噪声，听起来会更好。**
> 因为它把"与信号相关的谐波失真"换成了"不相关的宽带噪声"——而人耳对后者宽容得多。

## 反直觉但真实

| 直觉 | 实际 |
|---|---|
| 加噪声 → 更脏 | ✅ 加**特定**噪声 → 听感更干净 |
| 降位深 → 精度损失 | ✅ 损失无法避免，但可以**改变损失的性质** |
| 总失真应该变小 | ❌ 总失真可能略增，但**听感更好** |

> [!note] 这不是玄学
> 下面的实测数据会说明：**失真的"性质"比"大小"更重要**。

---

## 一、问题：量化误差与信号相关

16-bit 量化时，误差范围是 ±0.5 LSB。**如果误差是随机的，它听起来像嘶声**——无害。

但**不用 dither 时，误差与信号相关**：

```
输入：一个 1 LSB 幅度的小正弦
量化：信号大部分被"卡"在同一个量化台阶上
输出：变成方波状的失真 → 产生**谐波**
```

**谐波失真的听感**：像"音色变了"、"有嗡声"——**比噪声刺耳得多**。

---

## 二、实测：dither 做了什么

**测试条件**：1 LSB 幅度的 1kHz 正弦，16-bit 量化，48kHz。

| dither | 基频 | **谐波** | **噪声** | 谐波 − 噪声 |
|---|---|---|---|---|
| **无** | -89.5 dB | **-101.0 dB** | -147.1 dB | **46.1 dB** |
| **RPDF** | -90.3 dB | **-128.8 dB** | -138.0 dB | **9.2 dB** |
| **TPDF** | -90.3 dB | **-127.9 dB** | -135.4 dB | **7.5 dB** |

> [!important] 怎么读这张表
> - **谐波降低约 27 dB**（-101.0 → -127.9）
> - **噪声抬高约 12 dB**（-147.1 → -135.4）
> - **"谐波 − 噪声"从 46 dB 降到 7.5 dB**
>
> **总失真没有变小**（甚至可能略增），
> 但失真的**性质**从"跟着信号走的谐波"变成了"恒定的宽带噪声"。
>
> **这就是 dither 的全部价值。**

---

## 三、dither 的类型

| 类型 | 分布 | 特点 |
|---|---|---|
| **RPDF** | 均匀分布（Rectangular） | 最简单；能消除相关，但**噪声调制**残留 |
| **TPDF** | 三角分布（两个均匀相加） | **标准选择**；完全消除误差的统计依赖 |
| **高斯** | 正态分布 | 数学上不理想（尾部无限），实践少用 |

> [!tip] 为什么 TPDF 是标准
> 理论上，**TPDF dither 能让量化误差的一阶和二阶统计量都与信号无关**。
> RPDF 只能消除一阶（均值），高阶统计仍有残留 → 会产生"噪声调制"（noise modulation）：
> 噪声电平随信号变化，听起来像"呼吸"。
>
> **实现 TPDF 只需两个均匀分布相加**：
> ```cpp
> float tpdf (std::mt19937& rng) {
>     std::uniform_real_distribution<float> d (-0.5f, 0.5f);
>     return d (rng) + d (rng);      // 两个均匀 → 三角
> }
> ```

---

## 四、噪声整形（Noise Shaping）

> [!important] 更进一步：把噪声"搬"到听不见的地方
> 人耳对**高频**噪声不敏感（尤其 15kHz 以上）。
> 那为什么不把量化噪声推到那里去？

**原理**：把量化误差**滤波后反馈**回输入。

```
一阶误差反馈：
  y[n] = quant( x[n] - e[n-1] )
  e[n] = y[n] - (x[n] - e[n-1])     ← 本轮的量化误差

二阶：
  y[n] = quant( x[n] - 2·e[n-1] + e[n-2] )
```

**实测**（低电平正弦，测噪声谱的形状）：

| 处理 | 低频噪声（100–2k） | 高频噪声（15k+） | 高 − 低 |
|---|---|---|---|
| TPDF 无整形 | -137.7 dB | -138.0 dB | -0.3 dB（平坦） |
| **一阶噪声整形** | **-157.5 dB** | -132.5 dB | **+25.1 dB** |
| **二阶噪声整形** | **-177.3 dB** | -126.8 dB | **+50.4 dB** |

> [!tip] 效果
> - 一阶：低频噪声降 **20 dB**
> - 二阶：低频噪声降 **40 dB**
>
> 代价：高频噪声升高（但人耳不敏感）。
> **总噪声能量可能略增，但听感上更安静。**

**CD 母带处理常用这个技术**（16-bit 是硬限制，只能靠整形改善听感）。

> [!warning] 噪声整形的代价
> - 噪声电平升高 → 如果后续还要处理（如再压缩），会被放大
> - 某些播放设备的高频响应不好 → 可能听得到
> - **只在最终输出（降位深）时用，不要在中间环节用**

---

## 五、什么时候需要 dither

| 场景 | 需要吗 | 原因 |
|---|---|---|
| 32-bit float → **16-bit**（导出 CD/发行） | ✅ **需要** | 位深差距大 |
| 32-bit float → 24-bit | 🟠 边际 | 差距小（-144dB），几乎听不出 |
| 32-bit float → 32-bit float | ❌ 不需要 | 没有量化损失 |
| **插件内部处理** | ❌ **绝对不要** | 内部应该全程 float |
| 录音（ADC） | ✅ 硬件层面已有 | ADC 自己会做 |

> [!danger] 最常见的错误
> **在插件内部的处理链里加 dither。**
> 插件内部应该用 float 全程处理，只有在**最终降位深输出**时才需要 dither。
> 中间加 dither 只会白白增加噪声。

---

## 六、实现

```cpp
// TPDF dither + 一阶噪声整形（用于最终降位深）
class Dither
{
public:
    void prepare (int targetBits)
    {
        scale = (float) (1 << (targetBits - 1));   // 目标位深的半幅
    }

    // 输入 float [-1,1]，输出量化后的整数（以 float 返回）
    float process (float x)
    {
        // 1. 噪声整形：减去上一轮的误差
        const float shaped = x - errorPrev;

        // 2. TPDF dither（2 LSB 峰峰值）
        const float d = tpdf (rng) / scale;
        const float dithered = shaped + d;

        // 3. 量化
        const float q = std::round (dithered * scale) / scale;

        // 4. 记录误差（用于下一轮反馈）
        errorPrev = q - shaped;

        return q;
    }

private:
    std::mt19937 rng { 12345 };          // ⚠️ 固定种子保证可复现
    float scale = 32768.0f;
    float errorPrev = 0.0f;

    float tpdf (std::mt19937& g)
    {
        std::uniform_real_distribution<float> d (-0.5f, 0.5f);
        return d (g) + d (g);
    }
};
```

> [!warning] 三个实现细节
> 1. **RNG 必须是成员**，不能是函数内 static（多实例会互相干扰）
> 2. **固定种子**，否则测试无法复现
> 3. **不要用 `std::random_device`**（系统调用，会阻塞）

---

## 七、AI 会怎么写错

| # | AI 常犯 | 后果 | 怎么查 |
|---|---|---|---|
| 1 | **用均匀分布而非三角分布** | 噪声调制（呼吸感） | 检查是否两个均匀相加 |
| 2 | **在插件内部加 dither** | 白白增加噪声 | 只在降位深时用 |
| 3 | **dither 幅度不对** | 太小无效、太大可闻 | 标准是 2 LSB 峰峰值（TPDF） |
| 4 | **噪声整形忘了反馈误差** | 变成普通 dither | 检查 `errorPrev` 是否参与 |
| 5 | **用 `std::random_device`** | 系统调用，违反实时契约 | grep |
| 6 | **RNG 写成函数内 static** | 多实例干扰、初始化可能在音频线程 | 检查是否成员变量 |
| 7 | **每次调用重新构造分布对象** | 浪费 CPU | 分布对象应为成员 |
| 8 | **以为"32→24 bit 也需要 dither"** | 无意义的复杂度 | 差距太小，边际 |

> [!warning] 第 1 条最隐蔽
> 用 RPDF（均匀分布）**也能降低谐波**（实测 -128.8 dB），
> 所以你的测试会通过，听感也"改善了"。
> 但它有**噪声调制**残留——噪声电平随信号变化，长时间听会累。
>
> **必须是两个均匀分布相加**（三角分布）。

---

## 八、常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| 加了 dither 还是能听到失真 | 幅度太小 | 用 2 LSB 峰峰值 TPDF |
| 噪声有"呼吸"感 | 用了 RPDF | 改用 TPDF |
| 插件整体噪声变大 | 在内部处理链加了 dither | 只在最终输出加 |
| 测试结果不可复现 | 用了随机种子 | 固定种子 |
| 安静时 CPU 飙升 | 用了 `random_device` | 用 `std::mt19937` 成员 |
| 噪声整形后高频刺耳 | 整形阶数过高 | 降阶，或改用简单 TPDF |

---

## 九、怎么验证

```python
import numpy as np
SR, N = 48000, 48000
t = np.arange(N) / SR
s = 2**15 - 1
rng = np.random.default_rng(7)

def analyze(sig, f0=1000.0):
    """返回 (基频, 谐波能量, 噪声能量)"""
    w = np.hanning(len(sig))
    X = np.abs(np.fft.rfft(sig * w)) / np.sum(w) * 2
    fr = np.fft.rfftfreq(len(sig), 1/SR)
    fund = X[np.argmin(np.abs(fr - f0))]
    harm = np.sqrt(sum(X[np.argmin(np.abs(fr - k*f0))]**2
                       for k in range(2, 12) if k*f0 < SR/2))
    mask = np.ones(len(fr), bool)
    for k in range(1, 12):
        if k*f0 < SR/2:
            mask &= np.abs(fr - k*f0) > 100
    mask &= fr > 20
    return fund, harm, np.sqrt(np.mean(X[mask]**2))

# 1 LSB 幅度的小正弦
x = (1.0/s) * np.sin(2*np.pi*1000*t)

# 无 dither
q_none = np.round(x*s)/s
# TPDF dither
d = (rng.uniform(-0.5,0.5,N) + rng.uniform(-0.5,0.5,N))/s
q_tpdf = np.round((x+d)*s)/s

for name, y in [("无 dither", q_none), ("TPDF", q_tpdf)]:
    f, h, n = analyze(y)
    print(f"{name:>10}: 谐波 {20*np.log10(h+1e-20):>7.1f} dB, "
          f"噪声 {20*np.log10(n+1e-20):>7.1f} dB")
# 期望：TPDF 的谐波显著更低
```

**断言**：`TPDF 的谐波电平应比无 dither 低 20 dB 以上`。

---

## 相关

- [[MOC - DSP]]
- [[采样与量化]] — 量化误差的完整背景
- [[位深与动态范围]] — 6.02N+1.76 公式
- [[浮点音频表示]] — 为什么内部用 float
- [[音频测量基础]] — 怎么测谐波与噪声
- [[10-Sources/books/Downey - Think DSP]]

> [!note] 待补充
> - 各阶噪声整形的系数（二阶、三阶的滤波器设计）
> - 心理声学加权的噪声整形（按等响曲线定制）
> - 实测：噪声整形的 ABX 听音测试
> - 与其他降位深方案（如 POW-r 算法）的对比
