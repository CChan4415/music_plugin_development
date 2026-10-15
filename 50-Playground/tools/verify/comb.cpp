#include <vector>
#include <cmath>
#include <algorithm>
#include <cstddef>

// ---------- 前馈梳状（FIR）----------
class CombFeedforward
{
public:
    void prepare (int delaySamples, float gain)
    {
        buffer.assign ((size_t) delaySamples, 0.0f);
        idx = 0; g = gain;
    }
    float process (float x)
    {
        const float delayed = buffer[(size_t) idx];
        buffer[(size_t) idx] = x;
        if (++idx >= (int) buffer.size()) idx = 0;
        return x + g * delayed;
    }
private:
    std::vector<float> buffer;
    int idx = 0;
    float g = 0.5f;
};

// ---------- 反馈梳状（IIR）----------
class CombFeedback
{
public:
    void prepare (int delaySamples, float feedback)
    {
        buffer.assign ((size_t) delaySamples, 0.0f);
        idx = 0; fb = feedback;
    }
    float process (float x)
    {
        const float y = buffer[(size_t) idx];
        buffer[(size_t) idx] = x + fb * y;
        if (++idx >= (int) buffer.size()) idx = 0;
        return y;
    }
private:
    std::vector<float> buffer;
    int idx = 0;
    float fb = 0.5f;
};

// ---------- Freeverb 风格带阻尼反馈梳状 ----------
class CombDamped
{
public:
    void prepare (int delaySamples, float feedback, float damping)
    {
        buffer.assign ((size_t) delaySamples, 0.0f);
        idx = 0; fb = feedback; damp = damping; store = 0.0f;
    }
    void reset() { std::fill (buffer.begin(), buffer.end(), 0.0f); store = 0.0f; idx = 0; }
    float process (float x)
    {
        const float out = buffer[(size_t) idx];
        store = out * (1.0f - damp) + store * damp;   // 反馈路径里的一阶低通
        buffer[(size_t) idx] = x + store * fb;
        if (++idx >= (int) buffer.size()) idx = 0;
        return out;
    }
private:
    std::vector<float> buffer;
    int idx = 0;
    float fb = 0.5f, damp = 0.0f, store = 0.0f;
};

// ---------- 单个梳状的直流增益（设计期用）----------
inline float combDcGainFeedback (float feedback) { return 1.0f / (1.0f - feedback); }
inline float combPeakSpacingHz (float sampleRate, int delaySamples)
{
    return sampleRate / (float) delaySamples;
}

int main()
{
    CombFeedback c;
    c.prepare (480, 0.85f);
    double sum = 0.0;
    for (int n = 0; n < 262144; ++n)
        sum += c.process (n == 0 ? 1.0f : 0.0f);
    const double theory = combDcGainFeedback (0.85f);
    return std::fabs (sum - theory) < 0.01 ? 0 : 1;
}
