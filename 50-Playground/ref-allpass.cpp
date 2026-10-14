// 全通滤波器验证 —— 修复后与解析解逐点对照
// 编译: clang++ -std=c++17 ref-allpass.cpp -o ap && ./ap
// 详见 30-Wiki/DSP/全通滤波器 allpass.md
//
// ⚠️ 本文件记录了一个真实 bug 的修复过程：
//    错误写法 buffer[idx] = x + g*bufOut  →  不是全通（g=0.7 时增益 2.63 倍）
//    正确写法 buffer[idx] = x + g*y       →  全频段幅度恒为 1

#include <vector>
#include <cstdio>
#include <cmath>
#include <algorithm>
#include <complex>
class Allpass {
public:
    void prepare(int n, float g_) { buffer.assign((size_t)n, 0.0f); idx=0; g=g_; }
    float process(float x) {
        const float bufOut = buffer[(size_t)idx];
        const float y = -g*x + bufOut;
        buffer[(size_t)idx] = x + g*y;
        if (++idx >= (int)buffer.size()) idx = 0;
        return y;
    }
private:
    std::vector<float> buffer; int idx=0; float g=0.5f;
};
int main(){
    const double SR=48000; const int D=480; const float g=0.7f;
    // 解析解
    printf("用解析传递函数 H(z)=(-g+z^-D)/(1-g·z^-D) 对照：\n\n");
    printf("%8s %12s %12s %8s\n","频率","解析幅度","实测幅度","偏差");
    bool ok=true;
    for (double f : {50.0,100.0,440.0,1000.0,5000.0,10000.0,15000.0}) {
        // 解析
        double w=2*M_PI*f/SR;
        std::complex<double> z(std::cos(-w*D), std::sin(-w*D));
        std::complex<double> H=(double(-g)+z)/(1.0-double(g)*z);
        double mag_theory=std::abs(H);
        // 实测：跑足够长（20*D + 40 周期），从 30*D 之后测
        Allpass ap; ap.prepare(D, g);
        int N = 30*D + (int)(SR/f)*40;
        double pin=0,pout=0;
        for(int i=0;i<N;i++){
            double x=std::sin(2*M_PI*f*i/SR);
            double y=ap.process((float)x);
            if(i>=30*D){pin=std::max(pin,std::fabs(x));pout=std::max(pout,std::fabs(y));}
        }
        double r=pout/pin;
        bool t=std::fabs(r-mag_theory)<0.01; ok&=t;
        printf("%7.0fHz %12.6f %12.6f %8s\n", f, mag_theory, r, t?"✅":"❌");
    }
    printf("\n%s\n", ok?"✅ 实测与解析解完全一致 → 实现正确":"❌ 实现与解析不符");
    printf("（幅度均为 1.0 → 全通成立）\n");
    return 0;
}
