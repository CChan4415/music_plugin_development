// 最小 WAV 读写：不依赖任何库，只有标准库
// 这是 C++ 零基础路线的阶段 2 核心练习
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

int main(void) {
    // ---- 1. 生成 1 秒 440Hz 正弦，写 WAV ----
    const int SR = 48000, N = SR;
    int16_t *buf = malloc(N * sizeof(int16_t));
    for (int i = 0; i < N; i++)
        buf[i] = (int16_t)(sin(2.0 * M_PI * 440.0 * i / SR) * 0.5 * 32767);

    FILE *f = fopen("out.wav", "wb");
    // RIFF header（44 字节，标准 PCM）
    uint32_t dataSize = N * 2;
    fwrite("RIFF", 1, 4, f);
    uint32_t chunkSize = 36 + dataSize;  fwrite(&chunkSize, 4, 1, f);
    fwrite("WAVE", 1, 4, f);
    fwrite("fmt ", 1, 4, f);
    uint32_t fmtSize = 16;      fwrite(&fmtSize, 4, 1, f);
    uint16_t audioFmt = 1;      fwrite(&audioFmt, 2, 1, f);   // 1 = PCM
    uint16_t channels = 1;      fwrite(&channels, 2, 1, f);
    uint32_t sampleRate = SR;   fwrite(&sampleRate, 4, 1, f);
    uint32_t byteRate = SR * 2; fwrite(&byteRate, 4, 1, f);
    uint16_t blockAlign = 2;    fwrite(&blockAlign, 2, 1, f);
    uint16_t bitsPerSample = 16; fwrite(&bitsPerSample, 2, 1, f);
    fwrite("data", 1, 4, f);
    fwrite(&dataSize, 4, 1, f);
    fwrite(buf, 2, N, f);
    fclose(f);
    printf("写入 out.wav: %d 样本\n", N);

    // ---- 2. 读回来，减 6dB，写出去 ----
    f = fopen("out.wav", "rb");
    char riff[5] = {0}; fread(riff, 1, 4, f);
    fseek(f, 4, SEEK_CUR);                 // 跳过 chunkSize
    char wave[5] = {0}; fread(wave, 1, 4, f);
    fseek(f, 4 + 4 + 2 + 2, SEEK_CUR);     // 跳过 fmt 块头 + 格式信息
    uint32_t sr; fread(&sr, 4, 1, f);
    fseek(f, 4 + 2 + 2, SEEK_CUR);         // 跳过 byteRate/blockAlign/bits
    fseek(f, 4, SEEK_CUR);                 // 跳过 "data"
    uint32_t ds; fread(&ds, 4, 1, f);
    int n = ds / 2;
    int16_t *in = malloc(ds);
    fread(in, 2, n, f);
    fclose(f);
    printf("读回 out.wav: %d 样本, 采样率 %u, 头 %s/%s\n", n, sr, riff, wave);

    // 减 6dB = 乘 0.5
    FILE *g = fopen("out-6db.wav", "wb");
    fseek(f, 0, SEEK_SET);
    // 直接复制原头
    f = fopen("out.wav", "rb");
    char hdr[44]; fread(hdr, 1, 44, f); fclose(f);
    fwrite(hdr, 1, 44, g);
    for (int i = 0; i < n; i++) { int16_t v = (int16_t)(in[i] * 0.5); fwrite(&v, 2, 1, g); }
    fclose(g);
    printf("写入 out-6db.wav (每样本 ×0.5)\n");
    free(buf); free(in);
    return 0;
}
