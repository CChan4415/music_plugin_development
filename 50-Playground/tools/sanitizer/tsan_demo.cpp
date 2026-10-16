#include <atomic>
#include <thread>
#include <cstdio>
#include <vector>
// ① 非原子共享变量（TSan 应该抓）
int g_plain = 0;
// ② relaxed 原子（TSan 不报 —— 原子操作不是 race）
std::atomic<int> g_atomic{0};
// ③ 32 字节 payload + relaxed 索引（会真的撕裂，但 TSan 不报索引本身）
struct Msg { uint32_t a,b,c,d,e,f,g,h; };
std::atomic<uint64_t> g_w{0}, g_r{0};
Msg g_buf[256];
int main(int argc, char** argv){
    int mode = (argc>1)? argv[1][0]-'0' : 0;
    if (mode == 0) {
        std::thread t1([]{ for(int i=0;i<100000;i++) g_plain++; });
        std::thread t2([]{ for(int i=0;i<100000;i++) g_plain++; });
        t1.join(); t2.join();
        printf("  mode0: 非原子共享 → g_plain=%d\n", g_plain);
    } else if (mode == 1) {
        std::thread t1([]{ for(int i=0;i<100000;i++) g_atomic.fetch_add(1,std::memory_order_relaxed); });
        std::thread t2([]{ for(int i=0;i<100000;i++) g_atomic.fetch_add(1,std::memory_order_relaxed); });
        t1.join(); t2.join();
        printf("  mode1: relaxed 原子 → g_atomic=%d\n", g_atomic.load());
    } else {
        // relaxed 索引 + 非原子 payload → TSan 应报 payload 的 race
        std::thread p([]{ for(uint64_t i=0;i<500000;i++){
            auto w = g_w.load(std::memory_order_relaxed);
            auto& m = g_buf[w & 255]; m.a=m.b=m.c=m.d=m.e=m.f=m.g=m.h=(uint32_t)i;
            g_w.store(w+1, std::memory_order_relaxed); } });
        std::thread c([]{ uint64_t got=0; while(got<500000){
            auto r = g_r.load(std::memory_order_relaxed);
            auto w = g_w.load(std::memory_order_relaxed);
            if (w==r) continue;
            auto m = g_buf[r & 255]; (void)m;
            g_r.store(r+1, std::memory_order_relaxed); ++got; } });
        p.join(); c.join();
        printf("  mode2: relaxed 索引 + 非原子 payload\n");
    }
    return 0;
}
