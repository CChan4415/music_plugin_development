// 原子操作开销基准 —— 实测数据见 30-Wiki/Realtime-Engineering/参数自动化与线程安全.md
// 编译: clang++ -std=c++17 -O2 atomic_benchmark.cpp -o ab && ./ab
//
// 实测（Apple Silicon arm64, clang 21, -O2, 5000 万次）:
//   普通 float 数组读        0.609 ns/次
//   atomic relaxed load     0.727 ns/次  (1.19x)
//   atomic seq_cst load     0.625 ns/次  (1.03x)
//
// 48kHz 每样本预算 20833 ns → 原子读占 0.0035%（可忽略）
// ⚠️ 这是单线程无竞争的情况；多核竞争下的成本未实测

#include <atomic>
#include <chrono>
#include <cstdio>
#include <mutex>
#include <cmath>
static double now_ns(){ return std::chrono::duration<double,std::nano>(
    std::chrono::steady_clock::now().time_since_epoch()).count(); }
int main(){
    const long N = 50000000;
    double sink = 0;
    // 每次读不同的 atomic（避免被提升出循环）
    static std::atomic<float> arr[64];
    for (int i=0;i<64;i++) arr[i].store(0.5f+i*0.001f);

    double t0 = now_ns();
    for (long i=0;i<N;i++) sink += arr[i & 63].load(std::memory_order_relaxed);
    double t_relaxed = (now_ns()-t0)/N;

    t0 = now_ns();
    for (long i=0;i<N;i++) sink += arr[i & 63].load(std::memory_order_seq_cst);
    double t_seqcst = (now_ns()-t0)/N;

    // 普通数组基线
    static float plain[64];
    for (int i=0;i<64;i++) plain[i]=0.5f+i*0.001f;
    t0 = now_ns();
    for (long i=0;i<N;i++) sink += plain[i & 63];
    double t_plain = (now_ns()-t0)/N;

    printf("  %-30s %7.3f ns/次\n", "普通 float 数组读", t_plain);
    printf("  %-30s %7.3f ns/次  (%.2fx)\n", "atomic relaxed load", t_relaxed, t_relaxed/t_plain);
    printf("  %-30s %7.3f ns/次  (%.2fx)\n", "atomic seq_cst load", t_seqcst, t_seqcst/t_plain);
    printf("\n  48kHz 预算 20833 ns → relaxed 占 %.4f%%\n", t_relaxed/20833.3*100);
    printf("  sink=%.3f（防优化）\n", sink);
    return 0;
}
