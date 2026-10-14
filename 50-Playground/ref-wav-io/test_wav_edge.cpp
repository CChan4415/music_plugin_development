#include <vector>
#include <string>
#include <fstream>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cmath>
struct WavData { std::vector<float> samples; uint32_t sampleRate = 0;
                 uint16_t numChannels = 0, bitsPerSample = 0; };
// 逐字节读最稳：直接 read 进结构体会被 padding 搞错字段位置。WAV 一律小端。
static uint32_t readLE (std::ifstream& f, int n)   // 读 n 字节，按小端拼成整数
{   unsigned char b[4] = { 0 };  f.read ((char*) b, n);
    uint32_t v = 0;  for (int i = 0; i < n; ++i) v |= (uint32_t) b[i] << (8 * i);
    return v; }
// 剥掉头部后，音频就是一串交错的整数 —— 这就是 WAV 的全部
WavData loadWav (const std::string& path)
{
    std::ifstream f (path, std::ios::binary);   // ⚠️ 永远加 binary
    WavData out;  f.seekg (12);                 // 跳过 RIFF/size/WAVE
    while (f)                                   // 逐个 chunk 走，别假设顺序
    {
        char id[4];
        if (! f.read (id, 4)) break;
        const uint32_t size = readLE (f, 4);
        const auto chunkStart = f.tellg();
        const std::string tag (id, 4);
        if (tag == "fmt ")   // format(2) ch(2) rate(4) byteRate(4) align(2) bits(2)
        {   readLE (f, 2);  out.numChannels = (uint16_t) readLE (f, 2);
            out.sampleRate = readLE (f, 4);  readLE (f, 4); readLE (f, 2);
            out.bitsPerSample = (uint16_t) readLE (f, 2); }
        else if (tag == "data")
        {   out.samples.resize (size / (out.bitsPerSample / 8));
            for (float& x : out.samples)
                if (out.bitsPerSample == 16)   // int16 → float：除以 32768
                    x = (float) (int16_t) readLE (f, 2) / 32768.0f;
                else                           // 32-bit float：位模式即 IEEE-754
                { const uint32_t b = readLE (f, 4); std::memcpy (&x, &b, 4); } }
        // 跳到 chunk 末尾；size 为奇数时有一个补齐字节（WAV 硬规定）
        f.seekg (chunkStart + (std::streamoff) size + (std::streamoff) (size & 1));
    }
    return out;
}

int main(int argc, char** argv){
    for (int i=1;i<argc;i++){
        WavData w = loadWav(argv[i]);
        double peak = 0, sum = 0;
        for (float x : w.samples){ peak = std::max(peak, (double)std::fabs(x)); sum += (double)x*x; }
        printf("  %-15s rate=%u ch=%u bits=%u samples=%zu peak=%.4f rms=%.4f\n",
               argv[i], w.sampleRate, w.numChannels, w.bitsPerSample,
               w.samples.size(), peak, std::sqrt(sum/w.samples.size()));
    }
    return 0;
}
