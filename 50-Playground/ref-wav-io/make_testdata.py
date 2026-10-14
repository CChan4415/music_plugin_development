#!/usr/bin/env python3
"""生成 WAV 边界测试文件 —— 用来验证你的 WAV 解析器。

三种最容易写错的边界：
  1. stereo16.wav  16-bit 立体声（交错存储，容易把声道搞错）
  2. float32.wav   32-bit IEEE float（不是整数！位模式直接就是 float）
  3. listodd.wav   含**奇数长度** LIST chunk（不处理补齐字节 → 后面全部错位）

用法:
    python3 make_testdata.py          # 在当前目录生成三个 wav
"""
import numpy as np, wave, struct, os

SR = 48000
t = np.arange(SR) / SR

# 1) 16-bit 立体声
L = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16)
R = (np.sin(2 * np.pi * 660 * t) * 0.5 * 32767).astype(np.int16)
with wave.open('stereo16.wav', 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes(np.stack([L, R], axis=1).tobytes())

# 2) 32-bit float
mono = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
data = b''.join(struct.pack('<f', v) for v in mono)
with open('float32.wav', 'wb') as f:
    f.write(b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVE')
    f.write(b'fmt ' + struct.pack('<IHHIIHH', 16, 3, 1, SR, SR * 4, 4, 32))
    f.write(b'data' + struct.pack('<I', len(data)) + data)

# 3) 含奇数长度 LIST chunk（RIFF 规定奇数长度要补一个字节）
mono16 = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16).tobytes()
listdata = b'INFO' + b'X'                       # 5 字节 = 奇数
pad = b'\x00' if len(listdata) % 2 else b''
chunk = b'LIST' + struct.pack('<I', len(listdata)) + listdata + pad
with open('listodd.wav', 'wb') as f:
    total = 4 + len(chunk) + 8 + 16 + 8 + len(mono16)
    f.write(b'RIFF' + struct.pack('<I', total) + b'WAVE')
    f.write(chunk)
    f.write(b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, SR, SR * 2, 2, 16))
    f.write(b'data' + struct.pack('<I', len(mono16)) + mono16)

print("已生成: stereo16.wav / float32.wav / listodd.wav")
print("期望: 三个文件的 rate 都是 48000，peak 都是 0.5")
