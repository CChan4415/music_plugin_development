---
title: Python 优先的 DSP 学习路径
type: wiki
domain: dsp
status: seed
confidence: high
sources: []
tags: [recipe, python, todo]
created: 2026-10-14
updated: 2026-10-14
---

# Python 优先的 DSP 学习路径

> [!important] 这一页的核心主张
> **你不会 C++，但这不该阻止你明天就听到自己写的混响。**
> 用 Python + numpy，你可以在**几天内**写出滤波器、延迟、压缩器、混响，
> 并且**用耳朵和图表验证它们**。
>
> 这些代码不是玩具——**它们是你以后 C++ 实现的参考实现（reference implementation）**。

## 为什么这条路是对的

| | 直接学 C++ 做 DSP | 先 Python 后 C++ |
|---|---|---|
| 第一天能做什么 | 配环境、看编译错误 | **听到自己算的正弦波** |
| 一个滤波器要写多少行 | 200+ 行 + CMake + 构建配置 | **10 行** |
| 出错时在调什么 | 分不清是语法错还是算法错 | **只可能是算法错** |
| 画频响验证 | 要额外配绘图库和构建 | **3 行 matplotlib** |
| 放弃风险 | 高（前两周全是挫败） | 低（每天都有声音） |

> [!note] 一个关键洞察
> **DSP 的难点是数学和直觉，不是语言。**
> 你同时学"语言语法"和"DSP 原理"时，两种错误混在一起，无法区分。
> 先用 Python 把 DSP 原理搞清楚，之后学 C++ 只是"翻译你已经懂的东西"。

---

## 环境准备

```bash
# 需要 numpy 和 matplotlib
pip install numpy matplotlib
```

> [!warning] 你现在这台机器的情况
> - DSH 内置的 Python 有 **numpy 2.3.5**，但**没有 matplotlib 和 scipy**
> - 系统 Python（miniconda）**numpy 都没有**
> - 建议：建一个专用环境，别污染系统 Python
> ```bash
> conda create -n audiodsp python=3.12 numpy matplotlib scipy soundfile -y
> conda activate audiodsp
> ```

**读写 WAV**：先用标准库 `wave`（不用装任何东西），理解格式后再用 `soundfile` 图方便。

---

## 第一步：听到你算出来的声音

```python
import numpy as np, wave, struct

SR = 48000          # 采样率
DUR = 2.0           # 秒
FREQ = 440.0        # A4

# 生成正弦波 —— 这一行就是"振荡器"
t = np.arange(int(SR * DUR)) / SR
x = np.sin(2 * np.pi * FREQ * t)

# 写 WAV（16-bit PCM）
y = (x * 0.5 * 32767).astype(np.int16)     # 0.5 = 留 -6dB 余量
with wave.open('sine440.wav', 'wb') as f:
    f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes(y.tobytes())

print("done")
```

**播放它。** 用 `afplay sine440.wav`（macOS 自带）。

> [!tip] 这一步的深层意义
> `np.sin(2 * np.pi * FREQ * t)` 这一行，就是**加法合成的全部基础**。
> 你以前在合成器上拧的那些正弦振荡器，本质就是这个。
> **现在它是你的代码了。**

---

## 第二步：把"效果器"理解成"数组运算"

这是从音乐人思维转向 DSP 思维的关键一步：

| 音乐上的说法 | DSP/代码上的说法 |
|---|---|
| 音量推子 | `x * gain` |
| 淡入 | `x * np.linspace(0, 1, len(x))` |
| 声像 | 左右声道分别乘不同增益 |
| 延迟 1/8 拍 | `np.concatenate([np.zeros(d), x[:-d]])` |
| 混响 | 多个不同延迟的叠加 + 反馈 |
| 滤波 | 用**前一个输出**算**当前输出**（有记忆） |

**关键分界线**：
- **无记忆**的处理（增益、声像、失真）= 逐点函数，向量化一行搞定
- **有记忆**的处理（滤波、延迟、混响）= 需要**循环 + 状态变量**

```python
# 有记忆的处理：必须循环（因为 y[n] 依赖 y[n-1]）
def one_pole_lowpass(x, cutoff, sr):
    a = np.exp(-2 * np.pi * cutoff / sr)      # 系数
    y = np.zeros_like(x)
    prev = 0.0
    for n in range(len(x)):
        prev = (1 - a) * x[n] + a * prev       # 这就是"一阶低通"
        y[n] = prev
    return y
```

> [!warning] Python 循环很慢
> 处理 2 秒音频（96000 样本）大约要 0.1 秒，可以接受。
> 但**不要**用 Python 循环做实时处理——这正是以后要用 C++ 的原因。
> 现在你只是**验证算法**，慢一点没关系。

---

## 第三步：验证——用眼睛和耳朵同时确认

```python
import matplotlib.pyplot as plt

def plot_spectrum(x, sr, title=""):
    X = np.fft.rfft(x * np.hanning(len(x)))    # 加窗减少泄漏
    f = np.fft.rfftfreq(len(x), 1/sr)
    mag = 20 * np.log10(np.abs(X) + 1e-12)     # 转 dB
    plt.semilogx(f, mag); plt.xlabel('Hz'); plt.ylabel('dB')
    plt.title(title); plt.grid(True); plt.show()
```

> [!important] 每个 DSP 都要做这两个测试
> **数值测试**（眼睛）：喂脉冲/扫频/白噪声，画图看结果是否符合理论。
> **听觉测试**（耳朵）：播出来听，是否符合你的音乐直觉。
>
> **两个都要。** 图对了但听着怪，说明你漏了什么（比如相位）；
> 听着对但图不对，说明你还没理解你在做什么。

### 三个万能测试信号

| 信号 | 代码 | 测什么 |
|---|---|---|
| **脉冲** | `x = np.zeros(N); x[0] = 1.0` | 得到**脉冲响应**——完全描述一个线性系统 |
| **对数扫频** | 从 20Hz 扫到 20kHz | 得到**频率响应**，能听出问题 |
| **白噪声** | `np.random.randn(N)` | 测滤波器对宽带的整体影响 |

> [!tip] 脉冲响应是 DSP 里最重要的一个概念
> 一个线性时不变系统**完全由它的脉冲响应决定**。
> 这就是卷积混响的原理：拿到一个真实空间的脉冲响应，跟你的音频做卷积，
> 就等于把你的音频放进了那个空间。

---

## 十个练习（按顺序做，每个都能听）

> [!note] 这份清单对应 [[_meta/roadmap|路线图]] 阶段 1
> 每完成一个，在 `50-Playground/` 建一个目录，把脚本和结论留下。
> **结论要回写到 `30-Wiki/` 或 `20-Notes/`**，否则等于没做。

| # | 练习 | 你会学到 | 验证方式 |
|---|---|---|---|
| 1 | 生成 440Hz 正弦并存 WAV | 采样、时长、样本数 | 播放，用调音器 App 确认是 A4 |
| 2 | 生成白噪声和粉噪声 | 频谱形状与听感 | 对比听：粉噪声"更自然" |
| 3 | 把音量减半，确认是 -6dB | dB 与线性增益 | `20*log10(0.5) = -6.02` |
| 4 | 一阶低通，扫截止频率 | 滤波器基本概念 | 画频响，确认 -6dB/oct |
| 5 | Biquad 低通 | 二阶滤波器、系数计算 | 画频响，确认 -12dB/oct，见 [[Biquad 滤波器]] |
| 6 | 延迟线 + 1/8 拍回声 | 延迟、节拍同步 | 播放，数回声次数 |
| 7 | 梳状滤波 + 全通 → 简易混响 | 空间感的来源 | 对比干湿，听"房间" |
| 8 | 压缩器（含增益衰减曲线） | 动态处理 | 画输入-输出曲线，看软膝 |
| 9 | 参数不平滑 vs 平滑 | **zipper noise 长什么样** | 亲耳听到 bug，见 [[参数平滑 parameter smoothing]] |
| 10 | 故意不过采样做失真 | 混叠是什么声音 | 高频出现"金属味"，见 [[混叠 aliasing]] |

> [!important] 第 9 和第 10 项特别重要
> 它们让你**亲耳听到 bug**。
> 你以前做音乐时听过"数字味"、"颗粒感"，但不知道为什么。
> 做完这两个练习，你就知道了——**这是从音乐人到开发者的关键一步**。

---

## 从 Python 到 C++：怎么迁移

当你做完上面 10 个练习，C++ 的学习会变得**目标明确**：

```
Python 版本（你已经懂的算法）
        ↓ 逐行翻译
C++ 版本（同样的算法，不同的语法）
        ↓ 对比输出
两边数值一致？ → 说明 C++ 写对了
```

**这就是"参考实现"的用法**：
1. Python 版本是**标准答案**
2. C++ 版本是**产品**
3. 用 Python 脚本读两个 WAV 文件，相减，看差异有多大

```python
# null test：两个文件相减
a = read_wav('python_out.wav')
b = read_wav('cpp_out.wav')
diff = a - b
print(f"最大差异: {20*np.log10(np.max(np.abs(diff)) + 1e-12):.1f} dB")
# 如果 < -100dB，说明两个实现等价
```

> [!tip] Null test（零测试）是音频开发的核心验证手段
> 它把"听起来差不多"变成"数值上完全一致"。
> 以后你验证"我的插件旁路时是否完全无染色"、"优化前后是否等价"，
> 都用这个方法。见 [[Null Test 与 bit-exact 对比]]。

---

## 常见坑

| 症状 | 原因 | 解法 |
|---|---|---|
| WAV 播放是噪声 | dtype 不对（float 写成 int16 的字节） | 确认 `astype(np.int16)` 且归一化到 ±32767 |
| 声音有"嗡嗡"的周期噪声 | 缓冲区边界处理错、或循环里有整数溢出 | 检查 dtype，用 `float64` 计算 |
| 频谱图全是毛刺 | 没加窗 | `x * np.hanning(len(x))` |
| 滤波器输出爆炸 | 系数符号错、或参数超范围 | 见 [[Biquad 滤波器]] 的稳定性一节 |
| 处理很慢 | Python 循环 | 正常，接受它；或用 `scipy.signal.lfilter` 加速 |
| 听不出区别 | 参数变化太小，或没在正确的位置听 | 用极端参数先确认有效，再细调 |
| **验证脚本报出诡异结果** | **你的测量方法错了，不是被测代码错了** | **先怀疑测量工具**。测频率用 FFT，别用过零计数（见 [[2026-10-14 第一次验证：过零计数为什么错了]]） |

---

## 相关

- [[_meta/roadmap|开发路线图]] — 全局位置
- [[C++ 零基础到音频 DSP 路线]] — 下一步
- [[Biquad 滤波器]]
- [[参数平滑 parameter smoothing]]
- [[实时音频线程契约]] — 以后写 C++ 时必须遵守
- [[MOC - DSP]]
- [[MOC - Music & Acoustics]] — 音乐原理部分

> [!note] 待补充
> - 用 `scipy.signal` 加速滤波的写法（等基础版做完再优化）
> - Jupyter notebook 的组织方式
> - 怎么把 Python 原型变成一个可分享的 demo
