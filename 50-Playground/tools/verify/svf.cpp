#include <cmath>
#include <algorithm>
#include <vector>
#include <cstddef>

// ---------- Chamberlin SVF ----------
class ChamberlinSVF
{
public:
    void prepare (double sampleRate)
    {
        sr = sampleRate;
        reset();
    }
    void reset() { low = band = 0.0f; }

    // fc 必须钳制；返回 false 表示被钳制过（可用来提示用户）
    bool setParams (float cutoffHz, float q)
    {
        q = std::max (q, 0.05f);
        const float qq = 1.0f / q;                       // q = 1/Q
        // 稳定性边界： f < sqrt(q^2 + 4) - q
        const float fMax = std::sqrt (qq * qq + 4.0f) - qq;
        // f = 2 sin(pi fc / fs)  →  fc_max = (fs/pi) asin(fMax/2)
        const float fcMax = (float) (sr / M_PI) * std::asin (std::min (fMax * 0.5f, 1.0f));
        const bool clamped = cutoffHz > fcMax * 0.98f;
        cutoffHz = std::clamp (cutoffHz, 5.0f, fcMax * 0.98f);
        f = 2.0f * std::sin ((float) M_PI * cutoffHz / (float) sr);
        qq_ = qq;
        return ! clamped;
    }

    float processLow (float x)
    {
        low  = low + f * band;
        const float high = x - low - qq_ * band;
        band = band + f * high;
        return low;
    }
    float processHigh (float x)
    {
        low  = low + f * band;
        const float high = x - low - qq_ * band;
        band = band + f * high;
        return high;
    }
    float processBand (float x)
    {
        low  = low + f * band;
        const float high = x - low - qq_ * band;
        band = band + f * high;
        return band;
    }

private:
    double sr = 48000.0;
    float f = 0.1f, qq_ = 1.0f;
    float low = 0.0f, band = 0.0f;
};

// ---------- TPT / ZDF SVF（Zavalishin）----------
class TptSVF
{
public:
    void prepare (double sampleRate) { sr = sampleRate; reset(); }
    void reset() { ic1eq = ic2eq = 0.0f; }

    void setParams (float cutoffHz, float q)
    {
        cutoffHz = std::clamp (cutoffHz, 5.0f, (float) sr * 0.49f);
        q = std::max (q, 0.05f);
        const float g = std::tan ((float) M_PI * cutoffHz / (float) sr);
        const float k = 1.0f / q;
        a1 = 1.0f / (1.0f + g * (g + k));
        a2 = g * a1;
        a3 = g * a2;
        k_ = k;
    }

    float processLow (float x)  { tick (x); return v2; }
    float processBand (float x) { tick (x); return v1; }
    float processHigh (float x) { tick (x); return v0 - k_ * v1 - v2; }

private:
    void tick (float x)
    {
        v0 = x;
        v3 = v0 - ic2eq;
        v1 = a1 * ic1eq + a2 * v3;
        v2 = ic2eq + a2 * ic1eq + a3 * v3;
        ic1eq = 2.0f * v1 - ic1eq;
        ic2eq = 2.0f * v2 - ic2eq;
    }
    double sr = 48000.0;
    float a1 = 0.0f, a2 = 0.0f, a3 = 0.0f, k_ = 1.0f;
    float ic1eq = 0.0f, ic2eq = 0.0f;
    float v0 = 0.0f, v1 = 0.0f, v2 = 0.0f, v3 = 0.0f;
};

int main()
{
    ChamberlinSVF c; c.prepare (48000.0); c.setParams (1000.0f, 1.0f);
    TptSVF t;        t.prepare (48000.0); t.setParams (1000.0f, 1.0f);
    double acc = 0.0;
    for (int n = 0; n < 48000; ++n)
    {
        const float x = (n == 0) ? 1.0f : 0.0f;
        acc += c.processLow (x) + t.processLow (x);
    }
    return acc > 0.0 ? 0 : 1;
}
