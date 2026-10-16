#include <cstdio>
struct Biquad { float x[4] = {}; float y[4] = {}; 
  float process(float in){ 
    for(int i=3;i>0;--i){ x[i]=x[i-1]; y[i]=y[i-1]; }
    x[0]=in; 
    float out = 0.5f*x[0] + 0.5f*x[1];
    y[0]=out; return out; } };
int main(){
    Biquad bq;
    float* buf = new float[8];
    for(int i=0;i<8;i++) buf[i] = (float)i*0.1f;
    // ⚠️ 故意越界写（模拟 AI 常见错误）
    for(int i=0;i<12;i++) buf[i] = bq.process(buf[i]);   // 越界！
    printf("done, buf[0]=%.3f\n", buf[0]);
    delete[] buf;
    return 0;
}
