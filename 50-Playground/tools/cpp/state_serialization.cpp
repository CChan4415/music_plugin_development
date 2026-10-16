#include <cstdio>
#include <cstring>
#include <cstdint>
#include <vector>
#include <cmath>
// 模拟：把插件状态序列化成字节流
struct State {
    float gain = 0.5f;
    float cutoff = 1000.0f;
    int   filterType = 0;
    bool  bypassed = false;
    double sampleRate = 48000.0;
    float delayBuf[8] = {};        // ⚠️ 状态 vs 参数？
};
// 版本化的序列化
std::vector<uint8_t> serialize(const State& s, int version){
    std::vector<uint8_t> out;
    auto put = [&](const void* p, size_t n){ const uint8_t* b=(const uint8_t*)p;
        out.insert(out.end(), b, b+n); };
    // ① 版本号放最前
    put(&version, sizeof(version));
    // ② 参数
    put(&s.gain, sizeof(s.gain));
    put(&s.cutoff, sizeof(s.cutoff));
    put(&s.filterType, sizeof(s.filterType));
    put(&s.bypassed, sizeof(s.bypassed));
    return out;
}
int main(){
    printf("=== 状态保存与恢复：实测 ===\n\n");
    State s1; s1.gain=0.75f; s1.cutoff=2500.0f; s1.filterType=2; s1.bypassed=true;
    auto data = serialize(s1, 1);
    printf("① 序列化后大小: %zu 字节\n", data.size());
    printf("   字段: version(4) + gain(4) + cutoff(4) + filterType(4) + bypassed(1) = 17\n\n");

    printf("② 为什么版本号必须放最前\n");
    printf("   - 老版本工程只有前 16 字节\n");
    printf("   - 新版本加了字段 → 读到越界 → 崩溃或乱码\n");
    printf("   - 有版本号 → 可以先读版本，再决定怎么解析\n\n");

    printf("③ 浮点位模式 vs 文本\n");
    float g = 0.1f;
    uint32_t bits; std::memcpy(&bits, &g, 4);
    printf("   float 0.1f 位模式 = 0x%08x\n", bits);
    printf("   文本 \"0.1\" = 3 字节，但不精确（二进制浮点无法精确表示 0.1）\n");
    printf("   → 二进制保存是 bit-exact 的；文本保存有精度损失\n\n");

    printf("④ 不同字节序/对齐的问题\n");
    struct Padded { uint8_t a; uint32_t b; };
    printf("   struct {uint8_t; uint32_t;} 的 sizeof = %zu（不是 5！有对齐填充）\n", sizeof(Padded));
    printf("   → 直接 memcpy 整个 struct 会把填充字节也存进去\n");
    printf("   → 跨编译器/平台可能不一致\n");
    printf("   → **逐字段序列化**更安全\n");
    return 0;
}
