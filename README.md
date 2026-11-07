# Spectrafilm for Agents

给代理和命令行用的胶片模拟。引擎是 Andrea Volpato 的 [spektrafilm](https://github.com/andreavolpato/spektrafilm) **0.3.4**（包名全小写 `spektrafilm`）。本仓库的名字是 **Spectrafilm for Agents**。这是一份带本地 CPU / 内存改动的 headless 打包，**不是**上游的官方版本，也没有上游背书。

每张图走一条虚拟链路：负片（或反转片）→ 放大机 / 相纸 → 扫描。数据是测量过的彩色胶片和相纸。这套数据里没有黑白胶片。

**现在不能开箱出图。** 默认的 Hanatos 2025 光谱升采样表没有放进仓库：没有找到可以再分发那份表的许可证。负片印相的默认光源 `TH-KG3` 还要一份 Schott KG3 曲线，制造商曲线同样没有放进来。设置 `SPEKTRAFILM_SPECTRAL_LUT_DIR` 和 `SPEKTRAFILM_FILTER_DIR` 指向你有权使用的文件后，渲染才会继续。程序不会自己下载这些文件。缺文件时以非 0 退出，并写明环境变量和 `LICENSING.md`。反转片不走放大机，因此不一定要 KG3，但仍然要光谱表。证据和缺口见 [`LICENSING.md`](LICENSING.md)。

关闭扫描锐化必须写 `--no-sharpen`。不写的时候，扫描锐化仍是参数默认值 sigma `0.7`、amount `0.7`。`--quality` 默认 `95`，不是 92。这两种默认都不会把文件限制在 25MB 以内。

## 许可证

代码是 **GPL-3.0-only**。胶片 / 相纸 JSON 是 **CC BY-SA 4.0**。ICC、光谱 LUT、滤镜曲线各自有来源，不能把整棵树标成同一种许可证。对照表、归属和未决项在 [`LICENSING.md`](LICENSING.md)。

请保留 `LICENSE`、`src/SPEKTRAFILM_LICENSE.txt` 和 `src/NOTICE`。

## 安装

需要 Python **3.13** 和 [uv](https://docs.astral.sh/uv/)。依赖以 `src/pyproject.toml` 为准（`~=` 是兼容版本范围，不是单机锁文件）。

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ./src
chmod +x run.sh film.py
./run.sh --list
./run.sh --help
```

`run.sh` 会按顺序选用 `FILM_PYTHON`、仓库里的 `.venv/bin/python`、或 `PATH` 上的 `python3`。不要把 `.venv` 提交进 git。

2026-11-07 在 Linux x86_64 上，上述命令解析到的版本包括：numpy 2.5.4、scipy 1.18.1、numba 0.68.1、colour-science 0.4.7、OpenImageIO 3.1.19、rawpy 0.26.1、exiv2 0.18.1、lensfunpy 1.18.0、pyfftw 0.15.1、Pillow 12.3.0、pillow-heif 1.8.1、tifffile 2026.10.15、scikit-image 0.26.0、matplotlib 3.11.2。这些数字只说明那一次安装成功，不是跨平台承诺。

本仓库没有 GUI，也没有 LUT 烘焙应用。`pyproject.toml` 里不再列出 PySide6 / napari。

## 推荐命令

下面这组是明确写出来的偏好：**精确光谱、关闭扫描锐化、较大光晕、JPEG 质量 92、一次只处理一张**。默认值并不是这组。

默认是：长边 `--max-size 2400`、`--quality 95`、扫描锐化 sigma/amount `0.7`、放大机/扫描仪 LUT（不加 `--accurate`）、颗粒开启。默认**不会**把文件压到 25MB 以下。`--chunk-pixels`（默认 262144）只限制逐点运算的临时块，**不是**进程内存上限。

```bash
# 负片 + 相纸：Portra 400 / Portra Endura
./run.sh input.jpg -p portra400 -o out.jpg \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 \
  --quality 92 --max-size 2400 --seed 42

# 电影负片 + 2383 相纸
./run.sh input.jpg -p vision3_500t -o night.jpg \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 \
  --quality 92 --max-size 2400 --seed 42

# 反转片：Kodachrome 64，直接扫描，没有相纸
./run.sh input.jpg -p kodachrome -o slide.jpg \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 \
  --quality 92 --max-size 2400 --seed 42
```

JPEG 会嵌入 sRGB ICC，不复制源文件的 EXIF。程序会打印输出字节数。超过 25 MiB 时它只提示，不会自动再压缩。要减小体积或内存：降低 `--max-size`，或降低 `--quality`，或减小 `--chunk-pixels`，并保持一次一个进程。`--max-size 0` 是全分辨率，内存随像素增长。`--raw-half-size` 会改变 RAW 细节，只在你确实要预览时使用。`--threads` 覆盖 Numba 工作线程；未设置时，若环境里没有 `NUMBA_NUM_THREADS`，上限是 12。

TIFF 16 位：加 `--tiff`，会在 JPEG 旁边写同名 `.tif`（sRGB，16 位，zlib）。

## 输入：四条不同的路

| 输入 | 程序实际做的事 |
|---|---|
| JPEG、PNG、普通 TIFF | 按 ICC 或 TIFF 的 ImageDescription 识别色彩空间，再按该空间的传递函数解码。没有标签时按 sRGB。可用 `--input-space` 覆盖 |
| HEIF / AVIF | 同一条显示参考解码，不是场景线性 RAW |
| RAW（`film.py` 直接读 DNG/CR2/NEF/ARW 等） | LibRaw/rawpy 去马赛克，得到线性 ProPhoto RGB。这不是 `dng_validate -3`，也不表示所有 DNG 都能正确打开 |
| DNG stage 3 | 你自己提供 Adobe `dng_validate`，用 `adapters/dng_linear.py` 做 `-3`，再把 TIFF 交给 `./run.sh`。说明见 [`adapters/DNG.md`](adapters/DNG.md) |

`adapters/indigo_dng.py` 走的是 SDK 的最终 `-tif` 渲染，和 stage 3 不是同一个文件。

## 预设

`./run.sh --list` 会打印胶片、相纸和预设。常用预设：

| 预设 | 胶片 | 相纸 |
|---|---|---|
| `portra400` / `portra160` / `portra800` | Portra | Portra Endura |
| `kodachrome` | Kodachrome 64 | 反转片，直接扫描 |
| `vision3_500t` / `vision3_250d` | Vision3 | Kodak 2383 |
| `ektar100`、`gold200`、`ultramax400`、`fuji_c200`、`pro400h`、`xtra400`、`velvia`、`provia`、`ektachrome` | 见 `--list` | 见 `--list` |

## 优化（源码里实际有的）

这些是阅读当前源码和 2026-11-02 测量记录后的说明，不是新跑出来的加速比。

- `runtime/topology.py`：中间全幅数组保留到最后一个消费者，然后释放。
- `utils/spectral_integrate.py`：波长积分融进像素循环，内存是每像素 3 通道，不分配整幅 H×W×81 光谱张量。注释写明没有 fastmath，也没有抽掉波长。
- `utils/cam16_compiled.py`：float64 CAM16-UCS，由 Numba 编译。公式来自 Colour（BSD-3-Clause，见 `src/NOTICE`）。
- `utils/grain_kernels.py`：并行采样，并用恒等式 `Binomial(Poisson(λ), p) = Poisson(λ·p)`。分布与原来的 SciPy 采样一致，逐像素纹理不同。`--grain-backend reference` 仍可走原来的采样器。
- `utils/chunks.py`：逐点色彩运算按行分块。空间滤波（光晕、DIR、IIR）不在这里被切块。

Rust、Metal、CUDA 没有接进这条 CLI。

## 历史速度（不是本次冒烟测试）

测量日 **2026-11-02**，Apple Silicon，18 个逻辑核，48 GiB。同一虚拟环境比较优化前后。原始 JSON 和日志未入库。完整表格、线程扫描和 96 MP 合成测试的口径在 [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md)。

| 场景 | 优化前 | 优化后 | 峰值 RSS 优化前 / 后 |
|---|---:|---:|---:|
| 全幅 24.24 MP RAW → JPEG | 37.86 s | 12.86 s | 18.95 / 4.79 GiB |
| 同一 RAW，长边 2400 | 8.42 s | 4.21 s | 4.78 / 1.93 GiB |
| 精确光谱，长边 2400 | 11.99 s | 4.25 s | 11.75 / 1.93 GiB |
| 精确光谱，全幅 | 未测 | 16.13 s | 未测 / 4.79 GiB |
| 合成 96 MP 管线（不含 RAW 解码和写文件） | 未测 | 45.29 s | 未测 / 18.62 GiB |

全幅默认路径的记录大约是 2.94 倍时间和峰值 RSS 下降约 74.7%。这是那一台机器、那张 RAW、那组设置的结果。

本仓库的安装检查只用合成图确认命令、ICC 和预设能跑通。那种检查**不**测量加速比。可重复测量用 `benchmarks/measure.py`、`benchmarks/tune_threads.py`、`benchmarks/stress_large.py`。`benchmarks/compare_reference.py` 需要你另外提供未优化的源码树；RAW 对照只在设置了 `FILM_COMPARE_RAW` 时读取你指定的文件。结果 JSON 被 `.gitignore` 排除。

## 目录

```text
film.py  run.sh          CLI
src/                     spektrafilm 运行时和数据
adapters/                可选的 DNG / 预处理脚本
benchmarks/              测量脚本
docs/PERFORMANCE.md      历史测量记录
inbox/  outbox/          空目录，不要提交照片
```

## 隐私

发布前检查过文件名、文本、LUT/ICC 二进制里的可打印字符串，并排除了照片、虚拟环境、Adobe 二进制和原始基准 JSON。这不是绝对保证。检查范围写在 [`PRIVACY.md`](PRIVACY.md)。

## English, for agents

Read [`AGENTS.md`](AGENTS.md). Renders need `SPEKTRAFILM_SPECTRAL_LUT_DIR`. Negative prints also need `SPEKTRAFILM_FILTER_DIR` with `heat_absorbing/schott/KG3.csv`. Those files are not in this repository. `--help` and `--list` do not need them.

Short form once you have supplied the tables:

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -e ./src
./run.sh --list
./run.sh input.jpg -p portra400 -o out.jpg \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 --quality 92 --max-size 2400
```

One process per image. Defaults do not enforce a 25 MB output. JPEG/TIFF are display-referred. Direct RAW uses LibRaw. DNG stage 3 needs your own `dng_validate` (`adapters/DNG.md`). Engine spelling is `spektrafilm`. Project name is Spectrafilm for Agents. Licenses are split: see `LICENSING.md`.
