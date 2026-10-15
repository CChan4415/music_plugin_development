---
title: sanitizer 工具说明说明
type: meta
domain: realtime
status: solid
confidence: high
sources: []
tags: [recipe]
created: 2026-10-15
updated: 2026-10-15
---

# sanitizer 工具

本目录的演示程序，用于验证 sanitizer 能抓到什么。

## asan_demo.cpp — 堆越界

```bash
clang++ -std=c++17 -O1 -g -fsanitize=address asan_demo.cpp -o asan_demo
./asan_demo            # 正常（不越界）
./asan_demo overflow   # 触发 heap-buffer-overflow
```

实测输出：
```
ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6060000002b0
WRITE of size 4 at 0x6060000002b0 thread T0
    #0 ... in main+0x1d8
```

## ubsan_demo.cpp — 五类未定义行为

```bash
clang++ -std=c++17 -O1 -fsanitize=undefined -fno-sanitize-recover=all \
    ubsan_demo.cpp -o ubsan_demo
./ubsan_demo 0    # 有符号整数溢出
./ubsan_demo 1    # 除零
./ubsan_demo 2    # 浮点转整数越界
./ubsan_demo 3    # 移位越界
./ubsan_demo 4    # 未对齐访问
```

实测输出（每一类都精确定位到源码行）：
```
ubsan_demo.cpp:9:27:  runtime error: signed integer overflow: 2000000000 + 2000000000
ubsan_demo.cpp:15:24: runtime error: division by zero
ubsan_demo.cpp:21:26: runtime error: 1e+20 is outside the range of representable values of type 'int'
ubsan_demo.cpp:27:27: runtime error: shift exponent 40 is too large for 32-bit type 'int32_t'
ubsan_demo.cpp:34:13: runtime error: store to misaligned address ... requires 8 byte alignment
```

**全部 5 类都被抓到。** 详见 [[AddressSanitizer]] 与 [[UndefinedBehaviorSanitizer]]。
