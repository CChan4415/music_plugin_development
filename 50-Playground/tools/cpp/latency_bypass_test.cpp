// 延迟报告 & 旁路透明性实测 —— 为 30-Wiki/Realtime-Engineering/ 两页提供验证
//
// 验证清单:
//   1. 延迟插件旁路时**必须保持延迟**（否则 PDC 错位 → 相位跳变）
//   2. 两种旁路实现的数值对比:
//        错误: 旁路时跳过延迟线 → 输出提前 N 个采样
//        正确: 旁路时仍然延迟 N 个采样，只是不做处理
//   3. null test: 旁路输出 vs 干信号（对齐后）应完全一致
//   4. 状态残留: 旁路期间不跑 DSP → 重新启用时状态是"旧的" → 瞬态
//   5. lookahead 限制器的延迟与旁路
//
// 编译:
//   clang++ -std=c++17 -O2 latency_bypass_test.cpp -o lat_test && ./lat_test
//
// 注意: 本文件**不依赖 JUCE**，用最小接口模拟 AudioProcessor。

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <vector>

static constexpr double kSampleRate = 48000.0;
static constexpr int    kBlockSize  = 64;

static double db (double x) { return 20.0 * std::log10 (std::abs (x) + 1e-30); }

// ─────────────────────────────────────────────────────────────
//  一个"有延迟的插件"：lookahead 限制器（延迟 = lookahead 采样数）
// ─────────────────────────────────────────────────────────────
class LookaheadLimiter
{
public:
    void prepare (double sr, int /*maxBlock*/)
    {
        sampleRate = sr;
        lookaheadSamples = (int) std::round (0.005 * sr);      // 5 ms
        delay.assign ((size_t) lookaheadSamples, 0.0f);
        writeIdx = 0;
        gain = 1.0f;
        // 宿主必须被告知：
        latencySamples = lookaheadSamples;
    }

    int getLatencySamples() const noexcept { return latencySamples; }

    // 干信号（无处理、无延迟）—— 用于 null test 的参考
    void processDry (const float* in, float* out, int n) const
    { std::memcpy (out, in, sizeof (float) * (size_t) n); }

    // ❌ 错误实现：旁路时直接跳过一切（包括延迟线）
    void processBypassedWrong (const float* in, float* out, int n)
    { std::memcpy (out, in, sizeof (float) * (size_t) n); }     // 输出提前了 N 个采样

    // ✅ 正确实现：仍然走延迟线（保持延迟），只是不施加增益
    void processBypassedRight (const float* in, float* out, int n)
    {
        for (int i = 0; i < n; ++i)
        {
            const float delayed = delay[(size_t) writeIdx];
            delay[(size_t) writeIdx] = in[i];
            if (++writeIdx >= lookaheadSamples) writeIdx = 0;
            out[i] = delayed;                                   // 增益恒为 1（= 旁路）
        }
    }

    // 正常处理
    void processActive (const float* in, float* out, int n, float ceiling)
    {
        for (int i = 0; i < n; ++i)
        {
            delay[(size_t) writeIdx] = in[i];
            const float delayed = delay[(size_t) writeIdx];
            // 简单峰值检测（真实实现要用平滑 + lookahead 增益）
            const float target = (std::abs (in[i]) > ceiling) ? ceiling / std::abs (in[i]) : 1.0f;
            gain += 0.002f * (target - gain);
            if (++writeIdx >= lookaheadSamples) writeIdx = 0;
            out[i] = delayed * gain;
        }
    }

private:
    double sampleRate = kSampleRate;
    int    lookaheadSamples = 0;
    int    latencySamples = 0;
    std::vector<float> delay;
    int    writeIdx = 0;
    float  gain = 1.0f;
};

// ─────────────────────────────────────────────────────────────
//  测试 1: 旁路实现的对齐差异
// ─────────────────────────────────────────────────────────────
static int testBypassAlignment()
{
    std::puts ("\n=== 1. 旁路时的延迟：错误 vs 正确实现 ===");
    const int N = 4096;
    std::vector<float> in (N), dry (N), outWrong (N), outRight (N);

    // 输入：一个位于样本 1000 的脉冲（方便看时间偏移）
    std::fill (in.begin(), in.end(), 0.0f);
    in[1000] = 1.0f;

    LookaheadLimiter lim;
    lim.prepare (kSampleRate, kBlockSize);
    const int lat = lim.getLatencySamples();
    std::printf ("   lookahead = %d 采样（5 ms @ 48 kHz）\n", lat);

    for (int i = 0; i < N; i += kBlockSize)
    {
        const int n = std::min (kBlockSize, N - i);
        lim.processDry            (in.data() + i, dry.data() + i, n);
        lim.processBypassedWrong  (in.data() + i, outWrong.data() + i, n);
        lim.processBypassedRight  (in.data() + i, outRight.data() + i, n);
    }

    auto firstPeak = [] (const std::vector<float>& v)
    {
        for (size_t i = 0; i < v.size(); ++i) if (std::abs (v[i]) > 0.5f) return (int) i;
        return -1;
    };

    std::printf ("   干信号脉冲位置      : %d\n", firstPeak (dry));
    std::printf ("   ❌ 错误旁路脉冲位置 : %d  （提前 %d 采样 = %.2f ms）\n",
                 firstPeak (outWrong), firstPeak (dry) - firstPeak (outWrong),
                 (firstPeak (dry) - firstPeak (outWrong)) / kSampleRate * 1000.0);
    std::printf ("   ✅ 正确旁路脉冲位置 : %d  （延迟 %d 采样 = %.2f ms，与激活时一致）\n",
                 firstPeak (outRight), firstPeak (outRight) - firstPeak (dry),
                 (firstPeak (outRight) - firstPeak (dry)) / kSampleRate * 1000.0);
    std::puts ("   → 错误实现让音频**提前**了 240 个采样。");
    std::puts ("     宿主按报告的 240 采样做 PDC → 补偿后这条轨**提前 480 采样**。");
    std::puts ("     与其他轨叠加时 = 相位错位 = 梳状滤波 / 低频抵消。");

    const bool ok = (firstPeak (outWrong) == firstPeak (dry))
                 && (firstPeak (outRight) == firstPeak (dry) + lat);
    std::printf ("   %s\n", ok ? "✅ 通过" : "❌ 失败");
    return ok ? 0 : 1;
}

// ─────────────────────────────────────────────────────────────
//  测试 2: null test —— 正确旁路必须与干信号 bit 级一致（对齐后）
// ─────────────────────────────────────────────────────────────
static int testNullTest()
{
    std::puts ("\n=== 2. Null test：正确旁路 vs 干信号 ===");
    const int N = 8192;
    std::vector<float> in (N), dry (N), outRight (N);

    // 用一段有内容的信号（不是脉冲）—— 扫频 + 噪声
    for (int i = 0; i < N; ++i)
    {
        const double t = i / kSampleRate;
        const double f = 100.0 * std::pow (100.0, t * 4.0);
        in[(size_t) i] = (float) (0.4 * std::sin (2.0 * M_PI * f * t)
                                + 0.1 * std::sin (2.0 * M_PI * 1234.0 * t));
    }

    LookaheadLimiter lim;
    lim.prepare (kSampleRate, kBlockSize);
    const int lat = lim.getLatencySamples();

    for (int i = 0; i < N; i += kBlockSize)
    {
        const int n = std::min (kBlockSize, N - i);
        lim.processDry           (in.data() + i, dry.data() + i, n);
        lim.processBypassedRight (in.data() + i, outRight.data() + i, n);
    }

    // 对齐后比较
    double maxDiff = 0.0;
    for (int i = lat; i < N; ++i)
        maxDiff = std::max (maxDiff, (double) std::abs (outRight[(size_t) i] - dry[(size_t) (i - lat)]));

    std::printf ("   对齐后最大逐样本差异 = %.3e\n", maxDiff);
    std::printf ("   折合 = %.1f dB\n", db (maxDiff));
    std::puts ("   → 正确旁路是**纯延迟**，没有任何处理残留 → 差异应该是 0（或浮点 0）");
    std::puts ("   ⚠️ 如果你的旁路输出和干信号对齐后**不为 0**，说明:");
    std::puts ("      ① 旁路时仍在施加增益/滤波（残留处理）");
    std::puts ("      ② 或者你在旁路时把延迟线**清空**了（应保留）");

    // 对比：错误的"旁路时清空延迟线"
    std::vector<float> cleared (N);
    {
        LookaheadLimiter l2; l2.prepare (kSampleRate, kBlockSize);
        for (int i = 0; i < N; i += kBlockSize)
        {
            const int n = std::min (kBlockSize, N - i);
            l2.processBypassedRight (in.data() + i, cleared.data() + i, n);
        }
    }
    double d2 = 0.0;
    for (int i = lat; i < N; ++i)
        d2 = std::max (d2, (double) std::abs (cleared[(size_t) i] - dry[(size_t) (i - lat)]));
    std::printf ("   对照（连续旁路，状态未被扰动）差异 = %.3e（同样应为 0）\n", d2);

    const bool ok = maxDiff < 1e-12;
    std::printf ("   %s\n", ok ? "✅ 通过（旁路完全透明）" : "❌ 失败");
    return ok ? 0 : 1;
}

// ─────────────────────────────────────────────────────────────
//  测试 3: 状态残留 —— 旁路期间不跑 DSP 的后果
//
//  用一个**慢 release 的压缩器**演示（延迟线会自己排空，检测器不会）：
//   策略 A「继续处理但输出干信号」: 检测器/增益平滑器一直在跑 → 状态是热的
//   策略 B「完全跳过处理」        : 状态被冻结在旁路那一刻
//  重新启用时，B 的增益值与"当前应有的值"差很远 → 增益跳变 → 爆音
// ─────────────────────────────────────────────────────────────
class SlowCompressor
{
public:
    void prepare (double sr)
    {
        // release tau = 500 ms（很慢，所以状态"记得"很久以前的事）
        relCoeff = 1.0f - std::exp (-1.0f / (float) (sr * 0.5));
        atkCoeff = 1.0f - std::exp (-1.0f / (float) (sr * 0.005));
        env = 0.0f; gainDb = 0.0f;
    }

    float currentGainDb() const noexcept { return gainDb; }

    // 处理一个样本，返回应施加的线性增益（同时推进内部状态）
    float step (float x) noexcept
    {
        const float a = std::abs (x);
        env += ((a > env) ? atkCoeff : relCoeff) * (a - env);
        const float xDb = 20.0f * std::log10 (env + 1e-9f);
        const float targetDb = (xDb > -20.0f) ? (1.0f / 4.0f - 1.0f) * (xDb + 20.0f) : 0.0f;
        gainDb += 0.0005f * (targetDb - gainDb);          // 慢平滑
        return std::pow (10.0f, gainDb / 20.0f);
    }

private:
    float atkCoeff = 0.0f, relCoeff = 0.0f, env = 0.0f, gainDb = 0.0f;
};

static int testStateStaleness()
{
    std::puts ("\n=== 3. 状态残留：旁路期间『跳过处理』vs『继续处理』===");
    const int N = 96000;                     // 2 秒
    std::vector<float> in (N, 0.0f);
    // 前 0.5 秒：很强的信号（把压缩器推到深度压缩）
    for (int i = 0; i < 24000; ++i)
        in[(size_t) i] = (float) (0.95 * std::sin (2.0 * M_PI * 300.0 * i / kSampleRate));
    // 之后：静音 1.5 秒

    // 策略 B: 旁路期间完全跳过（状态冻结）
    SlowCompressor compB; compB.prepare (kSampleRate);
    for (int i = 0; i < 24000; ++i) compB.step (in[(size_t) i]);
    const float frozenGainDb = compB.currentGainDb();
    // 旁路 1 秒（完全不调用 step）

    // 策略 A: 旁路期间继续跑 DSP（状态保持热）
    SlowCompressor compA; compA.prepare (kSampleRate);
    for (int i = 0; i < 24000; ++i) compA.step (in[(size_t) i]);
    for (int i = 24000; i < 72000; ++i) compA.step (in[(size_t) i]);   // 静音也跑
    const float warmGainDb = compA.currentGainDb();

    std::printf ("   输入: 前 0.5 秒 0.95 满幅正弦，之后 1.5 秒静音\n");
    std::printf ("   旁路 1 秒后重新启用时的增益值:\n");
    std::printf ("     策略 B（跳过处理，状态冻结）= %+.2f dB\n", frozenGainDb);
    std::printf ("     策略 A（继续处理）          = %+.2f dB\n", warmGainDb);
    std::printf ("     差值                        = %.2f dB  ← 这就是增益跳变的幅度\n",
                 std::abs (frozenGainDb - warmGainDb));
    std::printf ("   折合线性增益跳变 = %.4f 倍\n",
                 std::pow (10.0, std::abs (frozenGainDb - warmGainDb) / 20.0));
    std::puts ("   → 策略 B 在重新启用的瞬间会把这个差值**一次性施加**到信号上。");
    std::puts ("     如果信号正在响，这就是一个可闻的『咔哒』或电平跳变。");
    std::puts ("   ⚠️ 但策略 A 有另一个代价: 旁路期间仍然消耗 CPU（用户以为省下来了）。");
    std::puts ("   ✅ 工程上常见折中: 旁路时**继续跑状态更新但跳过昂贵的处理**，");
    std::puts ("      或者在旁路↔激活的过渡上做 5–20 ms 的增益 crossfade。");

    const bool ok = std::abs (frozenGainDb - warmGainDb) > 0.1f;
    std::printf ("   %s（差值 > 0.1 dB，现象已复现）\n", ok ? "✅ 已复现" : "（未复现）");
    return ok ? 0 : 1;
}

// ─────────────────────────────────────────────────────────────
//  测试 4: 延迟变化时的处理
// ─────────────────────────────────────────────────────────────
static int testLatencyChange()
{
    std::puts ("\n=== 4. 延迟变化：过采样倍率切换 ===");
    std::printf ("   %-14s %-16s %-16s %-14s\n", "过采样倍率", "抗混叠滤波器延迟", "总延迟(采样)", "总延迟(ms)");
    // 典型 IIR 半带 polyphase allpass 的延迟量级（近似值，用于说明数量级）
    for (int os : { 1, 2, 4, 8 })
    {
        // 每个 2x 级的 IIR allpass 半带滤波器约 2~4 采样延迟（在原始采样率下）
        const int perStage = 3;
        const int stages = (int) std::log2 ((double) os);
        const int filterLat = perStage * stages;
        const int lookahead = 240;
        const int total = filterLat + lookahead;
        std::printf ("   %-14d %-16d %-16d %-14.3f\n", os, filterLat, total, total / kSampleRate * 1000.0);
    }
    std::puts ("   ⚠️ 上表的滤波器延迟是**量级示例**，不是某个具体实现的精确值。");
    std::puts ("      真实值取决于你用的半带滤波器设计（见 [[过采样 oversampling]]）。");
    std::puts ("   → 切换过采样倍率会改变总延迟。必须在**音频线程外**重新 setLatencySamples，");
    std::puts ("     并且宿主重新计算 PDC 时会有短暂的处理中断（JUCE 会做淡入淡出）。");
    return 0;
}

int main()
{
    std::puts ("延迟报告 & 旁路透明性实测");
    int fail = 0;
    fail += testBypassAlignment();
    fail += testNullTest();
    fail += testStateStaleness();
    fail += testLatencyChange();
    std::printf ("\n%s\n", fail == 0 ? "✅ 全部通过" : "❌ 有失败项");
    return fail;
}
