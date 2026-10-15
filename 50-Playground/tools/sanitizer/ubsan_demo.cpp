#include <cstdio>
#include <cstdint>
#include <cmath>
int main(int argc, char** argv) {
    int which = (argc > 1) ? argv[1][0] - '0' : 0;
    switch (which) {
        case 0: {   // 有符号整数溢出
            int32_t a = 2000000000;
            int32_t b = a + a;
            printf("int 溢出: %d\n", b);
            break;
        }
        case 1: {   // 除零
            volatile int z = 0;
            int r = 10 / z;
            printf("除零: %d\n", r);
            break;
        }
        case 2: {   // 浮点转整数越界
            double f = 1e20;
            int i = (int)f;
            printf("float→int: %d\n", i);
            break;
        }
        case 3: {   // 移位越界
            int32_t v = 1;
            int32_t s = v << 40;
            printf("移位: %d\n", s);
            break;
        }
        case 4: {   // 未对齐访问（本机 arm64 会怎样）
            char buf[16] = {};
            double* p = (double*)(buf + 1);
            *p = 1.0;
            printf("未对齐: ok\n");
            break;
        }
    }
    return 0;
}
