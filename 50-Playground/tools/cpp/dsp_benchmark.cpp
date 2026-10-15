// DSP 组件微基准 —— 实测数据见 30-Wiki/Realtime-Engineering/性能剖析.md
// 编译: clang++ -std=c++17 -O2 dsp_benchmark.cpp -o bench && ./bench
//
// 实测（Apple Silicon arm64, clang 21, -O2, 96kHz 预算 10.417 ns/样本）:
//   一阶低通            1.430 ns/样本   13.7% 预算
//   Biquad 直接I型       1.575 ns/样本   15.1% 预算
//   SVF (Chamberlin)    2.666 ns/样本   25.6% 预算
//   Biquad 转置直接II型   3.067 ns/样本   29.4% 预算
//
// ⚠️ 关键：sink 累加防止被编译器优化掉（本库踩过这个坑，测出 0.00 ms）

#include <chrono>
#include <cstdio>
#include <cmath>
#include <vector>
static double now_ms(){
    return std::chrono::duration<double,std::milli>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
struct BiquadDF2 { float b0,b1,b2,a1,a2,z1=0,z2=0;
    float p(float x) noexcept { float y=b0*x+z1; z1=b1*x-a1*y+z2; z2=b2*x-a2*y; return y; } };
struct BiquadDF1 { float b0,b1,b2,a1,a2,x1=0,x2=0,y1=0,y2=0;
    float p(float x) noexcept { float y=b0*x+b1*x1+b2*x2-a1*y1-a2*y2; x2=x1;x1=x;y2=y1;y1=y; return y; } };
struct OnePole { float a,z=0;
    float p(float x) noexcept { z=(1-a)*x+a*z; return z; } };
struct Svf { float f=0.13f,q=1.4f,lp=0,bp=0;
    float p(float x) noexcept { lp+=f*bp; float hp=x-lp-q*bp; bp+=f*hp; return lp; } };

template<typename F>
void bench(const char* name, F f, int N, int reps){
    std::vector<float> buf(N);
    for(int i=0;i<N;i++) buf[i]=std::sin(2*3.14159f*440*i/48000.0f)*0.5f;
    double sink = 0.0;                       // ⚠️ 防止被优化掉
    for(int i=0;i<N;i++) sink += f.p(buf[i]);   // 预热
    double t0=now_ms();
    for(int r=0;r<reps;r++) for(int i=0;i<N;i++) sink += f.p(buf[i]);
    double ms=now_ms()-t0;
    double ns = ms*1e6/((double)reps*N);
    printf("  %-24s %8.2f ms  %6.3f ns/样本  %5.1f%% 预算  %s\n",
           name, ms, ns, ns/10.417*100,
           (std::abs(sink) > 1e-30) ? "" : "⚠️被优化");
}
int main(){
    const int N=48000*10, R=100;
    printf("480000 样本 × %d 次 | @96kHz 单核预算 10.417 ns/样本\n\n", R);
    BiquadDF2 d2; d2.b0=0.003916f; d2.b1=0.007832f; d2.b2=d2.b0; d2.a1=-1.815318f; d2.a2=0.830982f;
    bench("Biquad 转置直接II型", d2, N, R);
    BiquadDF1 d1; d1.b0=0.003916f; d1.b1=0.007832f; d1.b2=d1.b0; d1.a1=-1.815318f; d1.a2=0.830982f;
    bench("Biquad 直接I型", d1, N, R);
    OnePole op; op.a=0.9f;
    bench("一阶低通", op, N, R);
    Svf svf;
    bench("SVF (Chamberlin)", svf, N, R);
    return 0;
}
