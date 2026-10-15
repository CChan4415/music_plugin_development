#include <vector>
#include <cmath>
#include <algorithm>
#include <cstddef>

// ---------- 窗化 sinc 设计的线性相位 FIR ----------
class FirFilter
{
public:
    // taps 必须是奇数 → Type I 线性相位，群延迟 = (N-1)/2 样本
    void prepare (int numTaps, float cutoffHz, double sampleRate)
    {
        N = numTaps | 1;                       // 强制奇数
        h.assign ((size_t) N, 0.0f);
        const double M = (N - 1) * 0.5;
        const double fc = std::min ((double) cutoffHz, sampleRate * 0.49);
        for (int n = 0; n < N; ++n)
        {
            const double t = (double) n - M;
            // 理想低通脉冲响应（sinc），t=0 时取极限 2fc/fs
            const double s = (std::fabs (t) < 1e-12)
                             ? 2.0 * fc / sampleRate
                             : std::sin (2.0 * M_PI * fc * t / sampleRate) / (M_PI * t);
            // Hamming 窗
            const double w = 0.54 - 0.46 * std::cos (2.0 * M_PI * n / (N - 1));
            h[(size_t) n] = (float) (s * w);
        }
        // 归一化直流增益为 1
        double sum = 0.0;
        for (float v : h) sum += v;
        if (std::fabs (sum) > 1e-12)
            for (float& v : h) v = (float) (v / sum);
        buffer.assign ((size_t) N, 0.0f);
        pos = 0;
    }

    float process (float x)
    {
        buffer[(size_t) pos] = x;
        double acc = 0.0;
        int p = pos;
        for (int n = 0; n < N; ++n)
        {
            acc += (double) h[(size_t) n] * buffer[(size_t) p];
            if (--p < 0) p = N - 1;
        }
        if (++pos >= N) pos = 0;
        return (float) acc;
    }

    int latencySamples() const { return (N - 1) / 2; }

private:
    std::vector<float> h, buffer;
    int N = 1, pos = 0;
};

int main()
{
    FirFilter f;
    f.prepare (101, 4000.0f, 48000.0);
    double acc = 0.0;
    for (int n = 0; n < 4096; ++n)
        acc += f.process (n == 0 ? 1.0f : 0.0f);
    return (f.latencySamples() == 50 && std::fabs (acc - 1.0) < 0.01) ? 0 : 1;
}
