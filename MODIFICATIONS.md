# Local changes relative to spektrafilm 0.3.4

Upstream: Andrea Volpato, <https://github.com/andreavolpato/spektrafilm>, version string 0.3.4 in `src/pyproject.toml`. This repository is not an upstream release.

The CPU and memory behavior described in `docs/PERFORMANCE.md` was already in the sources that were packaged. This publication did not retune those kernels. The mechanisms below are the ones named in the current source, not a claim that every line differs from upstream.

- Pipeline intermediates are released after their last consumer (`runtime/topology.py`).
- Spectral integration is fused and does not allocate a full H×W×wavelength tensor (`utils/spectral_integrate.py`).
- CAM16-UCS gamut compression has a compiled float64 path (`utils/cam16_compiled.py`), adapted from Colour under BSD-3-Clause.
- Grain can sample with exact Poisson thinning on parallel row streams (`utils/grain_kernels.py`). The draw is not pixel-identical to the SciPy sampler. `--grain-backend reference` keeps that sampler available.
- Pointwise colour work is chunked (`utils/chunks.py`). Spatial filters are not tiled there.
- The CLI caps the default Numba worker count at 12 when `NUMBA_NUM_THREADS` is unset.

Interface changes made so the public tree runs without a private machine layout:

- `run.sh` selects `FILM_PYTHON`, `.venv/bin/python`, or `python3`.
- `film.py` adds `--no-sharpen` and `--input-space`. Scanner unsharp stays on unless `--no-sharpen` is passed.
- TIFF files with no ICC profile can be identified from ImageDescription.
- The CLI prints output size in bytes and does not enforce a 25 MB cap.
- Adapters do not embed a Kodak ICC profile. Stage-3 and SDK-render TIFFs carry ImageDescription `ProPhoto RGB`.
- The non-portable SDK build script is not included. `adapters/DNG.md` points at Adobe's own download.
- `benchmarks/compare_reference.py` does not name a private RAW file.

Profile JSON files are redistributed with the upstream CC BY-SA 4.0 notice. This publication does not claim they were edited.
