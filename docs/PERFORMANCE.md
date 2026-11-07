# 历史性能记录（2026-11-02）

这些数字是 **2026-11-02** 在一台 Apple Silicon 机器上的测量转写：18 个逻辑处理器，48 GiB 内存。原始 JSON、cProfile 和测试日志 **没有** 放进本仓库（其中包含本机路径和原始文件名）。因此下表是历史记录，不是本仓库冒烟测试的结果，也不能当成其他硬件上的速度承诺。

那次测量用的光谱系数表和 Schott KG3 曲线，本仓库随后没有再分发。这里的安装检查只覆盖 `--help`、`--list`、色彩解码和缺文件时的报错，不重复那些计时。

实现基于 spektrafilm v0.3.4 运行时和同版本 CLI。优化改动留在本仓库源码里；上游作者 Andrea Volpato 没有为本仓库背书。

# FilmSim 性能与兼容性报告

日期：2026-11-02。实现基于本目录的 spektrafilm v0.3.4 和原 CLI。

已落地的是 **float64 Numba 多核 CPU 加速、计算融合和中间数组内存优化**。
Rust、Metal/CUDA 和磁盘外存处理目前属于研究路线，尚未接入。所有原 CLI
选项和预设均保留；完整分辨率与精确光谱模式也保留。

## 使用

```bash
cd .

# 完整分辨率，保留默认颗粒、光晕、自动曝光和自动印相校色
./run.sh PATH/TO/YOUR.arw --max-size 0 --seed 42 --timings \
  -o outbox/full.jpg

# 全波长积分，并额外保存 16 位 TIFF
./run.sh PATH/TO/YOUR.arw --max-size 0 --accurate --tiff --seed 42 \
  -o outbox/full_spectral.jpg

# 主动选择降低 RAW 解码分辨率的预览；会改变细节，不属于等价优化
./run.sh PATH/TO/YOUR.arw --raw-half-size --max-size 2400 \
  -o outbox/preview.jpg
```

默认使用最多 12 个 Numba 工作线程；`--threads` 可以覆盖，已有的
`NUMBA_NUM_THREADS` 环境变量优先于默认值。`--chunk-pixels` 默认 262144，
控制逐像素操作的临时分块大小，**不是进程的内存上限**。其他库可能有独立线程池。

`--grain-backend reference` 保留 SciPy 粒子采样，`--color-backend reference`
保留分块 Colour 色彩计算，便于比较和诊断。它们不会撤销其他内存优化。

## 实测方法与结果

机器：Apple Silicon / arm64，18 个 CPU 逻辑处理器，48 GiB 内存。
Python 3.13.18；原版和优化版使用同一个虚拟环境和输入文件。

真实 RAW：`PATH/TO/YOUR.arw`，4024×6024，24.24 MP。
胶片/相纸：Portra 400 / Portra Endura；默认效果开启；seed 42。
全尺寸测试显式设置 `--max-size 0`，没有启用 `--raw-half-size`。

时间由独立进程计时，包含 Python 导入、RAW 解码、模拟、自动印相和 JPEG 导出。
先预热 Numba 缓存再测量；原版最终对照设置 `NUMBA_NUM_THREADS=12`，
两次取中位数；优化版线程扫描每个配置两次，交替顺序。
峰值内存来自 `resource.getrusage().ru_maxrss`，macOS 上按字节换算为 GiB。
它受到系统内存压缩和其他负载影响，不是所有机器的保证值。

| 场景 | 原版时间 | 优化版时间 | 原版 / 优化版峰值 RSS |
|---|---:|---:|---:|
| 全尺寸 24.24 MP RAW → JPEG | 37.86 s | 12.86 s | 18.95 / 4.79 GiB |
| 同一 RAW → 长边 2400 JPEG | 8.42 s | 4.21 s | 4.78 / 1.93 GiB |
| 精确光谱 → 长边 2400 JPEG | 11.99 s | 4.25 s | 11.75 / 1.93 GiB |
| 精确光谱 → 全尺寸 JPEG | 未运行 | 16.13 s | 未测 / 4.79 GiB |

前两行优化版为 12 线程扫描的两次中位数；精确光谱优化版为单次复测，
原版均为最终统一 12 线程的两次中位数。每组峰值取相应样本的最大值。
另一次最终全尺寸独立验证为 **12.48 s / 4.79 GiB**。
全尺寸默认处理约 **2.94 倍速、峰值 RSS 下降 74.7%**；精确光谱 2400 的
峰值 RSS 下降约 83.6%。这些比例不是其他图片或硬件的保证。

主动开启半尺寸 RAW 预览后，长边 2400 JPEG + 16 位 TIFF 实测 **2.99 s /
1.23 GiB**。这项会改变输入细节，单独列示，不计入等价优化的加速比。

最终 **96 MP 合成管线：45.29 s / 18.62 GiB**，12 线程、编译 CAM16，
全图 finite 检查通过，报告为 `benchmarks/results/final_stress_96mp.json`。
计时从合成输入分配开始，包含模拟和数值检查，但不包含 Python 导入、RAW 解码或文件导出。

线程扫描结果（两次中位数；完整 RAW 解码保持一致）：

| Numba 线程 | 长边 2400 | 全尺寸 24.24 MP |
|---|---:|---:|
| 4 | 5.04 s | 17.64 s |
| 8 | 4.37 s | 15.19 s |
| 12 | 4.21 s | 12.86 s |
| 18 | 4.10 s | 12.87 s |

12 和 18 线程在这组全尺寸样本中基本相同，因此默认上限设为 12。
其他硬件、胶片和图像可能不同，可运行 `benchmarks/tune_threads.py` 自测。
首次编译另需时间，缓存放在 `.numba_cache/`；计时要区分首次运行与缓存运行。
这是 [Numba 官方指南](https://numba.readthedocs.io/en/stable/user/5minguide.html)
强调的基准条件。报告保留每个子进程的参数、线程数及最终测试的源码 SHA-256。

96 MP 是 **12000×8000 合成线性 RGB 管线压力测试**，不是 96 MP RAW 的端到端测试。
开启默认颗粒、光晕、DIR 扩散、自动曝光、印相校色、glare、CAM16 和锐化，
不含 RAW 解码与文件导出。microstructure 参数保持默认，其原有阈值判断在
这个尺寸下跳过该子效果；另有专门测试强制跨过阈值，验证采样统计与 seed。

## 改动如何减少时间和内存

| 环节 | 原问题 | 已实现 |
|---|---|---|
| 管线调度 | 所有历史节点结果一直存活到管线结束 | 根据最后消费者及时释放，保留分支依赖与 collect/inject 语义 |
| RAW 输入 | LibRaw、16 位 RGB、浮点和色彩变换临时数组重叠 | 尽早关闭 LibRaw，float32 归一化，白平衡和颜色转换分块 |
| 预处理 | 多次复制整幅图 | 保留输入所有权，复制一次后原地曝光 |
| 精确光谱 | 构造 H×W×81 的密度、透射光数组 | 融合所有波长的计算与三通道积分，不生成全幅光谱张量 |
| CAM16-UCS | 一次变换产生大量整图临时数组 | 编译完整 float64 正反变换和原 Cmax 表查找，每像素局部计算 |
| 颗粒 | 一次生成九个子层并串行采样 | 每次只生成一个子层，按行并行精确分布采样 |
| 微结构与 glare | 常数 mean/std 数组及多个中间数组 | 融合 lognormal 参数计算和采样，使用独立随机流 |
| LUT | 先生成整幅归一化坐标 | 将坐标归一化融合进 PCHIP 内核 |
| 空间滤波 | 多个三通道模糊副本重叠 | 按通道处理，IIR 纵向扫描复用缓冲，混合与锐化复用临时数组 |
| 输出 | 全幅传递函数临时数组与量化临时数组 | sRGB 编码和 8/16 位量化分块，及时释放输入与底片 |

以 96 MP 为例，单个 float64 三通道数组约 **2.15 GiB**，81 波长数组约
**57.9 GiB**，还未计算第二份光谱张量和其他中间结果。消除后者比仅仅把
相同数组操作翻译为 Rust 更直接地解决内存问题。

新的粒子采样使用精确恒等式：

```text
N ~ Poisson(lambda)
K | N ~ Binomial(N, p)
=> K ~ Poisson(lambda * p)
```

模型只消费最终显影颗粒 K，因此可以省掉潜在粒子计数 N 和二项分布采样。
这不是正态近似；原来的概率截断、饱和度、粒子尺寸、各子层参数和模糊仍保留。
其他采样方法和原有 fast-stats 选择继续保留各自实现。

空间滤波没有被简单切成独立图块。光晕、DIR 和 IIR 保持完整图像边界，
原算法已有的滤波近似也保留。新光谱和 CAM16 内核没有开启 fastmath；
没有全局改成 float32、缩减波长或用别的色域算法替代 CAM16。

## 功能与数值验证

- 新鲜原版对照 **34/34 通过**：15 个预设 × LUT/精确光谱，含自动印相和反转片曝光拟合；
  另比较原 SciPy 子层颗粒，以及真实 ARW 的 as_shot/daylight/tungsten 白平衡。
  无随机效果的对照最大绝对误差约 **1.65×10⁻¹⁴**；RAW 输入阶段 float32 比较为零差异。
- 新增测试覆盖完整光谱积分、所有六种色域选项、HDR/负值/多色域 CAM16、
  真实后端分发、特殊 Colour 上下文回退、LUT 归一化、随机分布矩与空间相关性、
  seed 跨线程一致性、节点释放、IIR/光晕边界、重复 main、正负片分支、JPEG/TIFF ICC
  及 16 位输入输出精度。
- `--seed 4294967295` 也经过端到端验证；修复了参考采样器中子层偏移越过 uint32 的问题。
- 核心套件结果及已存在的失败见下方最终验证记录。原版的四项失败已单独复现，
  未修改快照掩盖问题。它们是三项 RGB 旧快照和一个引用不存在
  `GrainParams.mult_usm_amount` 的 LUT-mode 测试。
- 本任务验证的是 headless CLI 和核心运行时；没有宣称验证 GUI 和 LUT-creator 应用。

最终核心套件：**231 passed / 4 failed**，日志 `.bench/tests_final.log`。
本次新增的 **42 项优化/CLI 测试全部通过**。
原版同四项失败的复现日志：`.bench/original_known_failures.log`，首行记录了
实际导入的 `.bench/reference` 模块路径。
实际 RAW 生成的全尺寸 JPEG 与预览 JPEG/TIFF 的尺寸、uint16 和 ICC 检查记录在
`benchmarks/results/export_validation.json`。

随机性需要区别对待：新粒子采样与旧采样器**同分布，但颗粒纹理逐像素不同**。
微结构和 glare 也使用新随机流。固定 seed 在相同后端、版本、尺寸与设置下可复现，
已验证 1/4 线程一致；不保证跨算法、版本、尺寸或全部硬件逐位相同。
`--grain-backend reference` 仅恢复原粒子采样器，不能恢复原版所有随机噪声。

## 大图仍有的边界

内存随像素数增长。当前实现仍保留若干完整 RGB/CMY 图和空间滤波缓冲；
没有宣称任意大小 RAW 都可以在固定 2 GiB 内运行。`--chunk-pixels` 只控制
点运算临时内存，一条很宽的扫描行可能超过设定目标。RAW 去马赛克仍需要
LibRaw 自己的全幅缓冲。

处理一批大 RAW 时，应先逐张运行。多个进程会各自保留大数组；盲目增加图片级
并发会抵消内存收益。降低 `--max-size` 或显式 `--raw-half-size` 可以进一步降低
耗时和内存，但会改变分辨率或细节，应按预览需求主动选择。

## Rust、GPU 和进一步优化的判断

以下是工程建议，**不是本次已实现或已测出的加速倍数**。

| 路线 | 适合解决的问题 | 需要完成的工作 |
|---|---|---|
| 长驻进程、顺序批处理 | 小图每次启动/导入及重复 LUT 初始化占比高 | 增加批处理接口，逐帧释放大数组，审查跨帧曝光/校色缓存失效 |
| Rust + PyO3 + Rayon | 去掉首次 JIT、部署为预编译 wheel、更严格的缓冲所有权 | 从热点内核移植，避免 Python↔Rust 整图复制，保留回退和数值对照 |
| Metal/wgpu 常驻管线 | Apple Silicon 上进一步提升大图吞吐 | 将上下游算子和缓冲一起放到 GPU，处理自动曝光/印相全局统计，最后统一读回 |
| CUDA | 迁移到有 NVIDIA GPU 的机器后利用 GPU | 单独后端、设备内存预算、随机采样与色彩精度验证；本机未实现 |
| 更少的内存读写 | CPU 已接近内存带宽上限的阶段 | 更明确的 out 参数、缓冲池、按通道或条带复用；验证所有权，不能覆盖仍被分支使用的数据 |
| 外存/磁盘缓冲 | 100–200 MP 及更大图、物理内存不足 | 全局统计先做一次；将点运算分块；IIR 需要沿扫描方向传递递归状态，FFT/卷积正确保留边界 |
| 可选 float32 路径 | 存储与带宽减半的潜力 | 独立模式，测量每阶段误差、极端高光/阴影、印相收敛和最终色差；保留 float64 默认导出 |
| CPU 向量数学库 | 精确光谱中大量 exp/pow 的成本 | 针对目标硬件测试 SIMD 数学函数，核对精度、线程和调用开销后再决定 |

Numba 已通过 LLVM 编译这些循环为机器码，因此“换成 Rust”本身不是新一轮
数量级提速的保证；AOT 部署、SIMD、缓冲管理和管线布局才是待衡量的收益点。
[Numba 运行机制](https://numba.readthedocs.io/en/stable/user/5minguide.html)
和 [PyO3 并行指南](https://pyo3.rs/main/parallelism) 可作为实现依据。

已经存在 [spektrafilm-rs](https://github.com/turbasvin/spektrafilm-rs)，其公开说明包含
Rust、wgpu/Metal 的 f32 GPU 管线，以及 f64 CPU 导出。README 的数值对照声明针对
上游 v0.3.2 的无随机效果基础链。它可以作为后续移植起点，但尚未在本机构建，
也未验证与这里 v0.3.4、自动印相、RAW 解码和全部参数兼容，不能直接当作等价替代。
没有引用它的另一台机器的速度当作本项目实测。

GPU 全链需要单独验证精度；[WGSL 浮点类型规范](https://www.w3.org/TR/WGSL/#floating-point-types)
不能提供与当前 float64 CPU 路径直接等同的 f64 运算。
若需求是“极限速度、允许有经量化的小误差”，GPU 是值得单独推进的路线；
若需求是“维持当前精确光谱和数值行为”，当前 CPU 路径仍是对照基准。

外存同样不能通过把一处 `np.empty` 改成 `memmap` 就实现固定内存：
下游函数还会分配输出和临时数组，必须整体调整数据流。
[NumPy memmap 文档](https://numpy.org/doc/stable/reference/generated/numpy.memmap.html)
说明了分段访问能力和共享映射的生命周期限制。

## 文件与复现

当时的 `.bench/` 日志、`benchmarks/results/*.json` 和样张 **没有** 放进本仓库。下面的路径是测量时的记录，用来说明数字从哪来；仓库里可以重新运行的是脚本本身。

- CLI：`film.py`、`run.sh`。完整选项：`./run.sh --help`。
- 使用说明：`README.md`。原版备份：`.bench/reference/`，不要覆盖。
- 内核：`src/src/spektrafilm/utils/{spectral_integrate,cam16_compiled,grain_kernels,chunks}.py`。
- 回归：`src/tests/test_memory_optimizations.py`、`src/tests/test_filmbot_cli.py`。
- 数值对照：`benchmarks/compare_reference.py` → `benchmarks/results/numerical_parity.json`。
- 单次基准：`benchmarks/measure.py`；最终对照 JSON 为 `benchmarks/results/final_*.json`。
- 线程扫描：`benchmarks/tune_threads.py` → `benchmarks/results/thread_sweep/summary.json`。
- 压力测试：`benchmarks/stress_large.py` → `benchmarks/results/final_stress_96mp.json`。
- 当时的全尺寸样图没有纳入本仓库。

```bash
# 统一线程设置比较原版与优化版，先各执行一次预热再记录。
NUMBA_NUM_THREADS=12 .venv/bin/python benchmarks/measure.py \
  --root .bench/reference --report .bench/recheck_before.json -- \
  PATH/TO/YOUR.arw --max-size 0 --seed 42 -o .bench/recheck_before.jpg
NUMBA_NUM_THREADS=12 .venv/bin/python benchmarks/measure.py \
  --report .bench/recheck_after.json -- \
  PATH/TO/YOUR.arw --max-size 0 --seed 42 -o .bench/recheck_after.jpg

.venv/bin/python benchmarks/tune_threads.py PATH/TO/YOUR.arw
.venv/bin/python benchmarks/compare_reference.py
.venv/bin/python benchmarks/stress_large.py \
  --report benchmarks/results/final_stress_96mp.json
```

早期测量和中途测试也保留在 `.bench/` 与 `benchmarks/results/`。恢复任务后发现
CAM16 编译内核曾未接入默认分发，已经修复并添加直接验证分发路径的测试。
本报告使用修复后的最终结果；此前带 cProfile、内存压力或未接入内核的结果
不用于最终加速比。许可证沿用 spektrafilm GPL-3.0，Colour 公式的 BSD 声明见 `src/NOTICE`。
