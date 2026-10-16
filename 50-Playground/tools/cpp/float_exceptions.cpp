#include <cstdio>
#include <cmath>
#include <cfenv>
#include <cstdint>
#include <cstring>
#pragma STDC FENV_ACCESS ON
static void show_flags(const char* tag){
    int f = std::fetestexcept(FE_ALL_EXCEPT);
    printf("  %-28s 标志:", tag);
    if (f & FE_INVALID)   printf(" INVALID");
    if (f & FE_DIVBYZERO) printf(" DIVBYZERO");
    if (f & FE_OVERFLOW)  printf(" OVERFLOW");
    if (f & FE_UNDERFLOW) printf(" UNDERFLOW");
    if (f & FE_INEXACT)   printf(" INEXACT");
    if (!f) printf(" （无）");
    printf("\n");
    std::feclearexcept(FE_ALL_EXCEPT);
}
int main(){
    printf("=== 各种运算触发的浮点异常标志 ===\n\n");
    volatile double z = 0.0, o = 1.0, big = 1e308, tiny = 1e-308;
    volatile float fz = 0.0f, fbig = 3.4e38f, ftiny = 1e-40f;

    std::feclearexcept(FE_ALL_EXCEPT);
    volatile double r1 = o / z;  show_flags("1.0 / 0.0");
    printf("     结果 = %f  (isinf=%d)\n", (double)r1, std::isinf(r1));

    std::feclearexcept(FE_ALL_EXCEPT);
    volatile double r2 = z / z;  show_flags("0.0 / 0.0");
    printf("     结果 = %f  (isnan=%d)\n", (double)r2, std::isnan(r2));

    std::feclearexcept(FE_ALL_EXCEPT);
    volatile double r3 = big * 10.0; show_flags("1e308 * 10（上溢）");
    printf("     结果 = %f  (isinf=%d)\n", (double)r3, std::isinf(r3));

    std::feclearexcept(FE_ALL_EXCEPT);
    volatile double r4 = tiny / 1e10; show_flags("1e-308 / 1e10（下溢）");

    std::feclearexcept(FE_ALL_EXCEPT);
    volatile double r5 = std::sqrt(-1.0); show_flags("sqrt(-1)");
    printf("     结果 = %f  (isnan=%d)\n", (double)r5, std::isnan(r5));

    std::feclearexcept(FE_ALL_EXCEPT);
    volatile double r6 = std::log(0.0); show_flags("log(0)");
    printf("     结果 = %f\n", (double)r6);

    printf("\n=== NaN/Inf 的传播 ===\n");
    volatile double nan_v = std::nan("");
    volatile double inf_v = o / z;
    printf("  NaN + 1     = %f\n", (double)(nan_v + 1.0));
    printf("  NaN * 0     = %f  ← 不会变回 0！\n", (double)(nan_v * 0.0));
    printf("  Inf - Inf   = %f\n", (double)(inf_v - inf_v));
    printf("  Inf * 0     = %f\n", (double)(inf_v * 0.0));
    printf("  1/Inf       = %f\n", (double)(o / inf_v));
    printf("  NaN > 0 ?   %s  ← 任何比较都是 false\n", (nan_v > 0) ? "true":"false");
    printf("  NaN != NaN ? %s\n", (nan_v != nan_v) ? "true":"false");
    return 0;
}
