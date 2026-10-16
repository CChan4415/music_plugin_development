#include <cstdio>
#include <cmath>
// 累加 a[i]*b[i] —— 经典的 FMA/向量化差异场景
double dot(const float* a, const float* b, int n){
    double s = 0.0;
    for (int i=0;i<n;i++) s += (double)a[i] * (double)b[i];
    return s;
}
int main(){
    const int N = 100000;
    static float a[N], b[N];
    for (int i=0;i<N;i++){ a[i] = 1.0f/(i+1.0f); b[i] = 1.0f/(i+2.0f); }
    printf("  dot = %.17g\n", dot(a,b,N));
    return 0;
}
