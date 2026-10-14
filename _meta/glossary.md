---
title: 中英术语对照表
type: meta
status: seed
updated: 2026-10-14
---

# 中英术语对照表

> [!note] 为什么需要这个
> 中文教程和英文文档的术语不一致，是学习音频编程的一大摩擦。
> 查英文资料时不知道中文叫什么，看中文教程时不知道英文关键词是什么——两头都卡。
> **这张表是搜索关键词的来源。**

## 音频基础

| 中文 | English | 备注 |
|---|---|---|
| 采样 | sampling | |
| 采样率 | sample rate | |
| 量化 | quantization | |
| 位深 | bit depth | |
| 混叠 | aliasing | 搜资料用这个，别搜"折叠失真" |
| 奈奎斯特频率 | Nyquist frequency | |
| 抖动（位深） | dither | ⚠️ 和时钟抖动 jitter 不是一回事 |
| 时钟抖动 | jitter | |
| 分贝 | decibel / dB | |
| 增益级联 | gain staging | |
| 脉冲响应 | impulse response (IR) | |
| 频率响应 | frequency response | |
| 相位 | phase | |
| 群延迟 | group delay | |
| 线性相位 | linear phase | |
| 最小相位 | minimum phase | |
| 过采样 | oversampling | |
| 重采样 | resampling | |
| 抽取 | decimation | |
| 内插 | interpolation | ⚠️ 也指延迟线插值，看上下文 |

## DSP

| 中文 | English | 备注 |
|---|---|---|
| 有限脉冲响应 | FIR (Finite Impulse Response) | |
| 无限脉冲响应 | IIR (Infinite Impulse Response) | |
| 双二阶滤波器 | biquad | 也叫 second-order section (SOS) |
| 状态变量滤波器 | state variable filter (SVF) | |
| 传递函数 | transfer function | |
| z 变换 | z-transform | |
| 极点 / 零点 | pole / zero | |
| 稳定性 | stability | |
| 快速傅里叶变换 | FFT | |
| 短时傅里叶变换 | STFT | |
| 窗函数 | window function | |
| 重叠相加 | overlap-add | |
| 相位声码器 | phase vocoder | |
| 延迟线 | delay line | |
| 分数延迟 | fractional delay | |
| 梳状滤波器 | comb filter | |
| 全通滤波器 | allpass filter | |
| 反馈延迟网络 | feedback delay network (FDN) | |
| 卷积混响 | convolution reverb | |
| 波形整形 | waveshaping | |
| 饱和 | saturation | |
| 削波 | clipping | |
| 软削波 | soft clipping | |
| 动态范围压缩 | dynamic range compression | |
| 前瞻 | lookahead | |
| 软膝 | soft knee | |
| 侧链 | sidechain | |
| 包络跟随器 | envelope follower | |
| 参数平滑 | parameter smoothing | |
| 拉链噪声 | zipper noise | |
| 粒子合成 | granular synthesis | |
| 物理建模 | physical modeling | |
| 波导 | waveguide | |
| 抗混叠振荡器 | anti-aliased oscillator | 关键词：BLIT / BLEP / DPW / PolyBLEP |
| 零延迟反馈 | zero-delay feedback (ZDF) | |
| 多速率处理 | multirate processing | |
| 自适应滤波 | adaptive filter | 关键词：LMS / NLMS |

## 心理声学

| 中文 | English | 备注 |
|---|---|---|
| 心理声学 | psychoacoustics | |
| 等响曲线 | equal-loudness contour | |
| 掩蔽效应 | masking | |
| 临界频带 | critical band | |
| 响度 | loudness | |
| 感知响度单位 | LUFS / LKFS | |
| 真峰值 | true peak | |
| 音高 | pitch | |
| 音色 | timbre | |
| 拍频 | beating | |
| 失谐 | detune | |
| 瞬态 | transient | |
| 攻击（时间） | attack | ⚠️ 和 note attack 不同义 |
| 双耳时间差 | ITD | |
| 双耳强度差 | ILD | |

## 工程与格式

| 中文 | English | 备注 |
|---|---|---|
| 宿主 | host / DAW | |
| 插件 | plugin | |
| 音频单元 | Audio Unit (AU) | |
| 音频缓冲区 | audio buffer | |
| 块大小 | block size / buffer size | |
| 实时线程 | realtime thread / audio thread | |
| 无锁 | lock-free | |
| 单生产者单消费者 | SPSC | |
| 非规格化数 | denormal / subnormal | |
| 优先级反转 | priority inversion | |
| 旁路 | bypass | |
| 自动化 | automation | |
| 预设 | preset | |
| 参数平滑 | parameter smoothing | |
| 离线渲染 | offline render / bounce | |
| 公证 | notarization | macOS 发布必需 |
| 代码签名 | code signing | |

> [!tip] 搜索技巧
> 遇到不懂的中文术语，**先在这张表里找英文，再用英文搜**。
> 音频 DSP 的高质量资料几乎都是英文的（KVR 论坛、musicdsp.org、GitHub、论文）。
> 中文资料的深度通常不够。
