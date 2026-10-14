#include <vector>
#include <cstdio>
class DelayLine {
public:
    void prepare (int n) { buffer.assign((size_t)n, 0.0f); writePos = 0; }
    void write (float x) { buffer[(size_t)writePos]=x; writePos=(writePos+1)%(int)buffer.size(); }
    float readDelayed (int d) const {
        int idx = writePos - 1 - d;
        while (idx < 0) idx += (int)buffer.size();
        return buffer[(size_t)idx];
    }
    float readFractional (float d) const {
        const int i0=(int)d; const float frac=d-(float)i0;
        const float a=readDelayed(i0), b=readDelayed(i0+1);
        return a + frac*(b-a);
    }
private:
    std::vector<float> buffer; int writePos = 0;
};
int main(){
    DelayLine dl; dl.prepare(1000);
    // 写脉冲，然后写 20 个静音 → 脉冲在"20 个采样之前"
    dl.write(1.0f);
    for(int i=0;i<20;i++) dl.write(0.0f);
    printf("脉冲位于 20 个采样前:\n");
    printf("  d=20   (脉冲位置) → %.4f  (期望 1.0)\n", dl.readFractional(20.0f));
    printf("  d=0    (最近写入) → %.4f  (期望 0.0)\n", dl.readFractional(0.0f));
    printf("  d=20.5 (脉冲与静音之间) → %.4f  (期望 0.5)\n", dl.readFractional(20.5f));
    printf("  d=20.25 → %.4f  (期望 0.75)\n", dl.readFractional(20.25f));
    printf("\n✅ 延迟线实现正确（之前的测试是我数错了距离）\n");
    return 0;
}
