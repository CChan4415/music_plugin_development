# 工具脚本

跨实验复用的脚本。用 Python（numpy/scipy/matplotlib）。

| 脚本 | 用途 | 状态 |
|---|---|---|
| `audio_io.py` | 读写 WAV、测量、测试信号、null test、频响验证 | ✅ 已实现 |
| `vault_health.py` | 知识库健康检查（断链→待写队列、lint） | ✅ 已实现 |
| `check_crossplatform.sh` | 找"到 Windows/Linux 会炸"的代码 | ✅ 已实现 |
| `check_env.sh` | 环境依赖检查（在 `exp-000` 下） | ✅ 已实现 |
| （待添加）`sweep.py` | 生成对数扫频信号 | ⬜ |
| （待添加）`analyze.py` | 读 wav，算 THD / 频率响应，画图 | ⬜ |

> [!note] 让 Agent 写这些脚本
> 这是 AI 辅助开发**性价比最高**的用法：脚本逻辑明确、容易验证、省你大量时间。
> 但**DSP 本身你自己写**。

## 子目录

| 目录 | 说明 |
|---|---|
| `cpp/` | [[C++ 工具]] — 音频线程分配检测器 |
