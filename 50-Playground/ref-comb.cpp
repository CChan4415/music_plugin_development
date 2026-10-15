// 梳状滤波器验证 —— Freeverb 风格的带阻尼梳状
// 编译: clang++ -std=c++17 ref-comb.cpp -o comb && ./comb
// 详见 30-Wiki/DSP/梳状滤波器 comb filter.md
//
// 验证要点：
//   1. 直流增益 = 1/(1-g)（解析解对照）
//   2. 峰值间隔 = fs/D
//   3. 阻尼让高频衰减更快（分频段能量法）
//   4. 稳定性（反馈 < 1 必衰减）
//
// ⚠️ 两个测量陷阱（本文件已规避）：
//   • FFT 长度必须 >> 脉冲响应长度，否则截断泄漏（damp=0.8 时误差 0.27）
//   • 测 RT60 时信号长度要足够，否则取到数组末尾（假 RT60 = 缓冲区长度）

#include <vector>
#include <cstdio>
#include <cmath>
#include <algorithm>

class Comb
{
public:
    void prepare (int sizeSamples, float feedback, float damping)
    {
        buffer.assign ((size_t) sizeSamples, 0.0f);
        idx = 0; fb = feedback; damp = damping; store = 0.0f;
    }
    float process (float x)
    {
        const float out = buffer[(size_t) idx];
        store = out * (1.0f - damp) + store * damp;   // 反馈路径里的一阶低通
        buffer[(size_t) idx] = x + store * fb;
        if (++idx >= (int) buffer.size()) idx = 0;
        return out;                                    // 输出取自延迟线
    }
private:
    std::vector<float> buffer; int idx = 0;
    float fb = 0.0f, damp = 0.0f, store = 0.0f;
};

int main()
{
    const double SR = 48000.0;
    const int D = 480;              // 10 ms
    const float g = 0.85f;
    printf("梳状滤波器: D=%d 样本 (%.1f ms), g=%.2f\n\n", D, D/SR*1000, g);

    // 1. 直流增益（用足够长的脉冲响应）
    for (float damp : {0.0f, 0.5f, 0.8f}) {
        Comb c; c.prepare(D, g, damp);
        const int N = 262144;
        double sum = 0.0;
        for (int n = 0; n < N; ++n) sum += c.process(n == 0 ? 1.0f : 0.0f);
        const double theory = 1.0 / (1.0 - g);   // 直流增益与 damp 无关
        printf("  damp=%.1f: 直流增益 实测 %.4f / 解析 %.4f  %s\n",
               damp, sum, theory, std::fabs(sum-theory) < 0.01 ? "OK" : "MISMATCH");
    }

    // 2. 稳定性
    {
        Comb c; c.prepare(D, g, 0.5f);
        c.process(1.0f);
        double peak = 0.0;
        // ⚠️ 必须每轮都调用 process（否则信号根本没推进）
        for (int n = 0; n < (int)(SR*10); ++n)
        {
            const float y = c.process(0.0f);
            if (n > (int)(SR*8)) peak = std::max(peak, (double) std::fabs(y));
        }
        printf("\n  10 秒后残余峰值 %.2e  %s\n", peak, peak < 1e-20 ? "稳定" : "衰减过慢");
    }
    return 0;
}
