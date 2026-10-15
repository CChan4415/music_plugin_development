"""用 unittest 写 DSP 测试（本机无 pytest，用内置 unittest）"""
import unittest
import numpy as np

SR = 48000.0

def biquad_lowpass(fc, Q, sr=SR):
    w0 = 2*np.pi*fc/sr
    cw, al = np.cos(w0), np.sin(w0)/(2*Q)
    a0 = 1 + al
    b = [(1-cw)/2/a0, (1-cw)/a0, (1-cw)/2/a0]
    a = [1.0, -2*cw/a0, (1-al)/a0]
    return np.array(b), np.array(a)

def impulse_response(b, a, n):
    y = np.zeros(n); x = np.zeros(n); x[0] = 1.0
    for i in range(n):
        acc = sum(b[k]*x[i-k] for k in range(len(b)) if i-k >= 0)
        acc -= sum(a[k]*y[i-k] for k in range(1, len(a)) if i-k >= 0)
        y[i] = acc
    return y

class TestBiquad(unittest.TestCase):
    def test_dc_gain_is_unity(self):
        """低通的直流增益应为 1"""
        b, a = biquad_lowpass(1000.0, 0.707)
        self.assertAlmostEqual(np.sum(b)/np.sum(a), 1.0, places=6)

    def test_nyquist_gain_is_zero(self):
        """低通的 Nyquist 增益应接近 0"""
        b, a = biquad_lowpass(1000.0, 0.707)
        zb = sum(bi*((-1)**i) for i, bi in enumerate(b))
        za = sum(ai*((-1)**i) for i, ai in enumerate(a))
        self.assertLess(abs(zb/za), 1e-3)

    def test_minus3db_at_cutoff(self):
        """-3dB 点应落在设计频率附近"""
        b, a = biquad_lowpass(1000.0, 0.707)
        h = impulse_response(b, a, 1 << 14)
        H = np.abs(np.fft.rfft(h)); f = np.fft.rfftfreq(len(h), 1/SR)
        db = 20*np.log10(H + 1e-20)
        f3 = f[np.argmax(db < -3)]
        self.assertLess(abs(f3 - 1000.0), 20.0, f"-3dB 点 {f3:.1f}Hz")

    def test_stable(self):
        """极点必须在单位圆内"""
        b, a = biquad_lowpass(1000.0, 0.707)
        p = np.roots(a)
        self.assertLess(np.max(np.abs(p)), 1.0)

    def test_impulse_decays(self):
        """脉冲响应必须衰减"""
        b, a = biquad_lowpass(1000.0, 0.707)
        y = impulse_response(b, a, 1 << 14)
        self.assertLess(np.max(np.abs(y[len(y)//2:])), 1e-6)

    def test_edge_parameters(self):
        """极端参数下不应崩溃或发散"""
        for fc in [20.0, 20000.0]:
            for Q in [0.1, 10.0]:
                with self.subTest(fc=fc, Q=Q):
                    b, a = biquad_lowpass(fc, Q)
                    p = np.roots(a)
                    self.assertLess(np.max(np.abs(p)), 1.0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
