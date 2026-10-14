#include <atomic>
#include <cstdlib>
#include <cstdio>
#include <new>
std::atomic<bool> inAudioThread { false };
void* operator new (std::size_t size)
{
    if (inAudioThread.load (std::memory_order_relaxed))
    {
        printf("  ❌ 检测到音频线程里分配内存！size=%zu\n", size);
        std::abort();
    }
    if (auto* p = std::malloc (size)) return p;
    throw std::bad_alloc();
}
void operator delete (void* p) noexcept { std::free (p); }
void operator delete (void* p, std::size_t) noexcept { std::free (p); }

int main(){
    printf("测试 1: 非音频线程分配\n");
    auto* p = new int(42); printf("  ✅ 正常分配 %d\n", *p); delete p;

    printf("测试 2: 音频线程里分配（应该被抓到）\n");
    inAudioThread.store(true);
    fflush(stdout);
    auto* q = new int(1);
    printf("  ❌ 没抓到\n");
    delete q;
    return 0;
}
