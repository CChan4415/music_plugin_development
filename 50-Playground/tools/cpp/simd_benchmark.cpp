#include <cstdio>
#include <chrono>
#include <cmath>
#include <vector>
static double ns_now(){ return std::chrono::duration<double,std::nano>(
    std::chrono::steady_clock::now().time_since_epoch()).count(); }

// 计算密集：每个样本多次运算（模拟 biquad 级联）
void process_scalar(float* d, int n, float g){
    for(int i=0;i<n;i++){
        float v = d[i];
        v = v*g + 0.1f;  v = v*g + 0.1f;  v = v*g + 0.1f;  v = v*g + 0.1f;
        v = v*g + 0.1f;  v = v*g + 0.1f;  v = v*g + 0.1f;  v = v*g + 0.1f;
        d[i] = v;
    }
}
// 带分支（模拟非线性/条件处理）
void process_branchy(float* d, int n, float g){
    for(int i=0;i<n;i++){
        float v = d[i];
        for(int k=0;k<8;k++){
            v = v*g + 0.1f;
            if(v > 1.0f) v = 1.0f;         // 饱和
            else if(v < -1.0f) v = -1.0f;
        }
        d[i] = v;
    }
}
template<typename F>
void bench(const char* name, F f, int n, int reps){
    std::vector<float> buf(n);
    for(int i=0;i<n;i++) buf[i] = std::sin(i*0.001f)*0.3f;
    double sink=0;
    f(buf.data(), n, 0.99f);
    for(int i=0;i<n;i++) sink += buf[i];
    double t0=ns_now();
    for(int r=0;r<reps;r++) f(buf.data(), n, 0.99f);
    double ns=(ns_now()-t0)/((double)reps*n);
    for(int i=0;i<n;i++) sink += buf[i];
    printf("  %-26s %8.4f ns/样本  (sink=%.0f)\n", name, ns, sink);
}
int main(){
    const int N=1<<14, R=5000;
    printf("=== 计算密集型（每样本 8 次乘加）× %d 次 ===\n\n", R);
    bench("无分支（可向量化）", process_scalar, N, R);
    bench("带饱和分支", process_branchy, N, R);
    printf("\n  48kHz 预算 = 20.83 ns/样本\n");
    return 0;
}
