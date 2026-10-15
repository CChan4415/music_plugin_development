#include <cstdio>
#include <cmath>
#include <vector>
// 简化版"插件核心"，用于验证构建流程
class Biquad {
public:
    void setLowpass(float fc, float Q, double sr) {
        const double w0 = 2*M_PI*fc/sr, cw = std::cos(w0), al = std::sin(w0)/(2*Q), a0 = 1+al;
        b0=(float)((1-cw)/2/a0); b1=(float)((1-cw)/a0); b2=b0;
        a1=(float)(-2*cw/a0);    a2=(float)((1-al)/a0);
    }
    float process(float x) {
        const float y = b0*x + z1;
        z1 = b1*x - a1*y + z2;
        z2 = b2*x - a2*y;
        return y;
    }
private:
    float b0=1,b1=0,b2=0,a1=0,a2=0,z1=0,z2=0;
};
int main() {
    Biquad f; f.setLowpass(1000.0f, 0.707f, 48000.0);
    double acc = 0;
    for (int i = 0; i < 48000; ++i)
        acc += std::fabs(f.process((float)std::sin(2*M_PI*1000*i/48000.0)));
    std::printf("  平均输出 %.6f\n", acc/48000);
    return 0;
}
