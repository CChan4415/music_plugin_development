#include <vector>
#include <cstdio>
int main(int argc, char** argv) {
    std::vector<float> buf(16, 0.0f);
    int idx = (argc > 1) ? 20 : 8;      // 故意越界
    printf("写入 buf[%d]（容量 16）\n", idx);
    buf[(size_t)idx] = 1.0f;            // ← 越界
    printf("值 = %.1f\n", buf[(size_t)idx]);
    return 0;
}
