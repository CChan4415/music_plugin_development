#include <atomic>
#include <thread>
#include <cstdio>
struct Msg { uint32_t a,b,c,d,e,f,g,h; };
std::atomic<uint64_t> g_w{0}, g_r{0};
Msg g_buf[256];
int main(){
    std::atomic<long> bad{0}, got{0};
    const long N = 2000000;
    std::thread p([]{ for(long i=0;i<N;i++){
        auto w = g_w.load(std::memory_order_relaxed);
        auto& m = g_buf[w & 255];
        m.a=m.b=m.c=m.d=m.e=m.f=m.g=m.h=(uint32_t)i;
        g_w.store(w+1, std::memory_order_relaxed); } });
    std::thread c([&]{ long n=0; while(n<N){
        auto r = g_r.load(std::memory_order_relaxed);
        auto w = g_w.load(std::memory_order_relaxed);
        if (w==r) continue;
        auto m = g_buf[r & 255];
        if (!(m.a==m.b&&m.b==m.c&&m.c==m.d&&m.d==m.e&&m.e==m.f&&m.f==m.g&&m.g==m.h))
            bad.fetch_add(1, std::memory_order_relaxed);
        g_r.store(r+1, std::memory_order_relaxed); ++n; } });
    p.join(); c.join();
    printf("  relaxed 索引 + 非原子 payload: 撕裂 %ld / %ld\n", bad.load(), N);
    return 0;
}
