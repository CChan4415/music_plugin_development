#include <cstdio>
#include <cmath>
#include <cstdint>
#include <cstring>
// 一个对浮点结合律敏感的累加
double sum_forward(const double* x, int n){ double s=0; for(int i=0;i<n;i++) s+=x[i]; return s; }
double sum_backward(const double* x, int n){ double s=0; for(int i=n-1;i>=0;i--) s+=x[i]; return s; }
// 有 FMA 机会的表达式
float a_b_c(float a,float b,float c){ return a*b+c; }
int main(int argc, char** argv){
    int mode = (argc>1)? argv[1][0]-'0' : 0;
    if (mode == 0) {
        // 结合律：不同求和顺序
        const int N = 100000;
        static double x[N];
        for (int i=0;i<N;i++) x[i] = 1.0/(i+1.0);
        double f = sum_forward(x,N), b = sum_backward(x,N);
        printf("  正序和   = %.17g\n", f);
        printf("  逆序和   = %.17g\n", b);
        printf("  差异     = %.3e  (相对 %.3e)\n", f-b, std::fabs(f-b)/std::fabs(f));
    } else if (mode == 1) {
        // float vs double 累加
        const int N = 1000000;
        float sf=0; double sd=0;
        for (int i=0;i<N;i++){ float v = 1.0f/(i+1.0f); sf+=v; sd+=v; }
        printf("  float 累加  = %.10g\n", (double)sf);
        printf("  double 累加 = %.17g\n", sd);
        printf("  差异        = %.3e\n", (double)sd-(double)sf);
    } else {
        // 位模式：-0.0 vs 0.0，NaN
        float pz = 0.0f, nz = -0.0f;
        uint32_t bp, bn; std::memcpy(&bp,&pz,4); std::memcpy(&bn,&nz,4);
        printf("  +0.0f 位模式 = 0x%08x\n", bp);
        printf("  -0.0f 位模式 = 0x%08x\n", bn);
        printf("  +0.0f == -0.0f ? %s\n", (pz==nz)?"true":"false");
        printf("  memcmp 相同 ? %s\n", (std::memcmp(&pz,&nz,4)==0)?"true":"false");
        float nan1 = std::nanf(""), nan2 = std::nanf("");
        printf("  NaN == NaN ? %s\n", (nan1==nan2)?"true":"false");
    }
    return 0;
}
