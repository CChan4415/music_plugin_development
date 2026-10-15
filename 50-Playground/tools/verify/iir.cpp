#include <vector>
#include <cmath>
#include <algorithm>
#include <cstddef>

// ---------- 级联 biquad（高阶 IIR 的标准做法）----------
struct BiquadCoeffs { float b0, b1, b2, a1, a2; };

class Biquad
{
public:
    void reset() { z1 = z2 = 0.0f; }
    void setCoeffs (const BiquadCoeffs& c) { cf = c; }
    float process (float x)
    {
        // Direct Form II Transposed
        const float y = cf.b0 * x + z1;
        z1 = cf.b1 * x - cf.a1 * y + z2;
        z2 = cf.b2 * x - cf.a2 * y;
        return y;
    }
private:
    BiquadCoeffs cf { 1.0f, 0.0f, 0.0f, 0.0f, 0.0f };
    float z1 = 0.0f, z2 = 0.0f;
};

class CascadedBiquads
{
public:
    static constexpr int kMaxStages = 12;
    void prepare (int numStages)
    {
        stages = std::clamp (numStages, 0, kMaxStages);
        for (int i = 0; i < stages; ++i) filters[i].reset();
    }
    void setStage (int i, const BiquadCoeffs& c)
    {
        if (i >= 0 && i < stages) filters[i].setCoeffs (c);
    }
    float process (float x)
    {
        for (int i = 0; i < stages; ++i) x = filters[i].process (x);
        return x;
    }
private:
    Biquad filters[kMaxStages];
    int stages = 0;
};

// 单个 Butterworth 二阶节（RBJ 形式），Q 由级联位置决定
inline BiquadCoeffs butterworthLpStage (double fc, double Q, double sr)
{
    const double w = 2.0 * M_PI * fc / sr;
    const double cw = std::cos (w);
    const double alpha = std::sin (w) / (2.0 * Q);
    const double a0 = 1.0 + alpha;
    BiquadCoeffs cf;
    cf.b0 = (float) (((1.0 - cw) * 0.5) / a0);
    cf.b1 = (float) ((1.0 - cw) / a0);
    cf.b2 = cf.b0;
    cf.a1 = (float) ((-2.0 * cw) / a0);
    cf.a2 = (float) ((1.0 - alpha) / a0);
    return cf;
}

int main()
{
    CascadedBiquads f;
    f.prepare (3);
    // 6 阶 Butterworth 的极点 Q 值
    const double Qs[3] = { 0.51763809, 0.70710678, 1.93185165 };
    for (int i = 0; i < 3; ++i) f.setStage (i, butterworthLpStage (1000.0, Qs[i], 48000.0));
    double acc = 0.0;
    for (int n = 0; n < 8192; ++n) acc += f.process (n == 0 ? 1.0f : 0.0f);
    return std::fabs (acc - 1.0) < 0.05 ? 0 : 1;
}
