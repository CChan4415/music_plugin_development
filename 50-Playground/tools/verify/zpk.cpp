#include <complex>
#include <vector>
#include <cmath>
#include <cstdio>

// ---------- 从差分方程系数直接求极零点（设计期用，不要放在音频线程）----------
// 用 Durand-Kerner 迭代求多项式的复根。
// coeffs 按【降幂】给出：p[0] z^N + p[1] z^(N-1) + ... + p[N]
inline std::vector<std::complex<double>> polynomialRoots (std::vector<double> p)
{
    while (! p.empty() && std::fabs (p.front()) < 1e-300) p.erase (p.begin());
    const int n = (int) p.size() - 1;
    if (n <= 0) return {};
    const double lead = p.front();
    for (double& c : p) c /= lead;

    std::vector<std::complex<double>> r ((size_t) n);
    for (int i = 0; i < n; ++i)
        r[(size_t) i] = std::polar (1.0, 2.0 * M_PI * i / n + 0.4);

    for (int iter = 0; iter < 500; ++iter)
    {
        double maxDelta = 0.0;
        for (int i = 0; i < n; ++i)
        {
            std::complex<double> val = p[0];
            for (int k = 1; k <= n; ++k) val = val * r[(size_t) i] + p[(size_t) k];
            std::complex<double> denom (1.0, 0.0);
            for (int j = 0; j < n; ++j)
                if (j != i) denom *= (r[(size_t) i] - r[(size_t) j]);
            if (std::abs (denom) < 1e-300) continue;
            const std::complex<double> delta = val / denom;
            r[(size_t) i] -= delta;
            maxDelta = std::max (maxDelta, std::abs (delta));
        }
        if (maxDelta < 1e-14) break;
    }
    return r;
}

int main()
{
    // H(z) = (b0 + b1 z^-1) / (1 + a1 z^-1)
    const double b0 = 0.5, b1 = 0.3, a1 = -0.4;
    auto zeros = polynomialRoots ({ b0, b1 });     // 降幂
    auto poles = polynomialRoots ({ 1.0, a1 });
    std::printf ("zero = %.6f  pole = %.6f\n", zeros[0].real(), poles[0].real());
    // 稳定性：所有极点必须在单位圆内
    bool stable = true;
    for (auto& p : poles) stable = stable && (std::abs (p) < 1.0);
    return stable ? 0 : 1;
}
