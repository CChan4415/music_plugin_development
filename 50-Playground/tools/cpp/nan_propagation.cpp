#include <cstdio>
#include <cmath>
#include <cstdint>
// IIR 反馈环：NaN 一旦进入，永不恢复
int main(){
    printf("=== NaN 在 IIR 反馈环里的传播（本库验证）===\n\n");
    const double a = 0.9;
    double y = 0.0;
    printf("  注入位置   注入后第 1 个样本    第 100 个    第 10000 个\n");
    for (int inject = 0; inject < 3; ++inject) {
        y = 0.0;
        double v1=0, v100=0, v10000=0;
        for (int n = 0; n < 10001; ++n) {
            double x = 0.0;
            if (n == 100 && inject == 1) x = std::nan("");
            if (n == 100 && inject == 2) x = 1.0/0.0;   // Inf
            y = x + a*y;
            if (n == 101) v1 = y;
            if (n == 200) v100 = y;
            if (n == 10000) v10000 = y;
        }
        const char* name = (inject==0)?"无":(inject==1)?"NaN":"Inf";
        printf("  %-10s %14.4f %14.4f %14.4f\n", name, v1, v100, v10000);
    }
    printf("\n  → 一次 NaN/Inf 注入后，**永远无法恢复**（0*NaN = NaN）\n");

    printf("\n=== 防护手段的效果 ===\n");
    auto run = [&](const char* name, bool sanitize){
        double y = 0.0; long fixed = 0;
        for (int n = 0; n < 10001; ++n) {
            double x = (n == 100) ? std::nan("") : 0.0;
            y = x + a*y;
            if (sanitize && !std::isfinite(y)) { y = 0.0; ++fixed; }
        }
        printf("  %-24s 最终 y=%.4f  修复次数=%ld\n", name, y, fixed);
    };
    run("不防护", false);
    run("isfinite 检查并清零", true);

    printf("\n=== 对比：FIR（无反馈）===\n");
    {
        const int N = 8; double buf[N] = {};
        double y = 0.0;
        for (int n = 0; n < 10001; ++n) {
            double x = (n == 100) ? std::nan("") : 0.0;
            for (int i = N-1; i > 0; --i) buf[i] = buf[i-1];
            buf[0] = x;
            y = 0; for (int i=0;i<N;i++) y += buf[i]*0.125;
        }
        printf("  最终 y=%.4f  ← NaN 被冲出了（有限记忆）\n", y);
    }
    return 0;
}
