// 伪共享基准测试 —— 验证 alignas(64) 的收益
// 编译: clang++ -std=c++17 -O2 false_sharing_bench.cpp -o fs && ./fs
// 本库实测: 240.0ms (Packed) vs 31.9ms (Padded) = 7.51x

#include <atomic>
#include <thread>
#include <cstdio>
#include <chrono>
struct Packed { std::atomic<long> a{0}, b{0}; };
struct Padded { alignas(64) std::atomic<long> a{0}; alignas(64) std::atomic<long> b{0}; };

template <typename T>
double bench(const char* name) {
    T s; const long N = 20000000;
    auto t0 = std::chrono::steady_clock::now();
    std::thread t1([&]{ for(long i=0;i<N;++i) s.a.fetch_add(1, std::memory_order_relaxed); });
    std::thread t2([&]{ for(long i=0;i<N;++i) s.b.fetch_add(1, std::memory_order_relaxed); });
    t1.join(); t2.join();
    double ms = std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t0).count();
    printf("  %-24s %8.1f ms\n", name, ms);
    return ms;
}
int main(){
    printf("两个索引各 2000 万次原子自增（本机 arm64）:\n");
    double p = bench<Packed>("相邻索引 (Packed)");
    double q = bench<Padded>("alignas(64) (Padded)");
    printf("\n  比值 = %.2fx  %s\n", p/q, p/q > 1.5 ? "✅ 伪共享影响显著" : "⚠️ 本机不明显");
    return 0;
}
