#include <atomic>
#include <cstdio>
#include <thread>
#include <cstdint>
#include <cstring>

// 演示: relaxed 索引 + 多字段 payload → ARM64 上真的会读到撕裂/陈旧数据
struct Msg { uint32_t a, b, c, d, e, f, g, h; };   // 32 字节，非单指令存储

template <int Order>   // 0 = relaxed, 1 = release/acquire
struct Q {
    static constexpr int N = 256;
    std::atomic<uint64_t> w{0}, r{0};
    Msg buf[N]{};
    bool push(const Msg& m) {
        uint64_t ww = w.load(std::memory_order_relaxed);
        if (ww - r.load(std::memory_order_acquire) >= N-1) return false;
        buf[ww & (N-1)] = m;
        if (Order) w.store(ww+1, std::memory_order_release);
        else       w.store(ww+1, std::memory_order_relaxed);
        return true;
    }
    bool pop(Msg& out) {
        uint64_t rr = r.load(std::memory_order_relaxed);
        uint64_t ww = Order ? w.load(std::memory_order_acquire)
                            : w.load(std::memory_order_relaxed);
        if (ww == rr) return false;
        out = buf[rr & (N-1)];
        if (Order) r.store(rr+1, std::memory_order_release);
        else       r.store(rr+1, std::memory_order_relaxed);
        return true;
    }
};

template <int Order>
void run(const char* name, long iters) {
    Q<Order> q;
    std::atomic<uint64_t> bad{0}, good{0};
    std::thread prod([&]{
        for (long i=0;i<iters;++i) {
            Msg m; m.a=m.b=m.c=m.d=m.e=m.f=m.g=m.h=(uint32_t)i;
            while (!q.push(m)) {}          // 满就重试（这里为了跑满次数）
        }
    });
    std::thread cons([&]{
        Msg m; long got=0;
        while (got < iters) {
            if (q.pop(m)) {
                ++got;
                bool ok = (m.a==m.b && m.b==m.c && m.c==m.d && m.d==m.e &&
                           m.e==m.f && m.f==m.g && m.g==m.h);
                if (ok) good.fetch_add(1,std::memory_order_relaxed);
                else    bad.fetch_add(1,std::memory_order_relaxed);
            }
        }
    });
    prod.join(); cons.join();
    std::printf("  %-22s 完整消息 %llu, 撕裂/陈旧 %llu  %s\n", name,
                (unsigned long long)good.load(), (unsigned long long)bad.load(),
                bad.load()? "❌ 数据竞争真的发作了" : "（本次未观测到）");
}

int main() {
    std::puts("=== relaxed vs release/acquire：32 字节消息，200 万次 ===");
    for (int rep=0; rep<3; ++rep) {
        run<0>("relaxed 索引", 2'000'000);
        run<1>("release/acquire", 2'000'000);
    }
    return 0;
}
