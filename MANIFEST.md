# Package contents

Included:

- `film.py`, `run.sh` — headless CLI
- `src/` — spektrafilm 0.3.4 runtime, profiles, ICC profiles, filter curves, spectral LUT
- `LICENSE` (GPL-3.0-only for the code), `src/SPEKTRAFILM_LICENSE.txt` (CC BY-SA 4.0 for profiles and their direct derivatives), `src/NOTICE` (Colour BSD-3-Clause)
- `LICENSING.md`, `MODIFICATIONS.md`, `PRIVACY.md`, `AGENTS.md`
- `docs/PERFORMANCE.md` — historical 2026-11-02 measurements, raw logs omitted
- `adapters/` — optional DNG and grade helpers, no Adobe binary
- `benchmarks/*.py` — scripts only
- empty `inbox/` and `outbox/`

Not included:

- Photographs, RAW files, virtualenvs, caches
- GUI and LUT-creator applications
- Adobe DNG SDK and `dng_validate`
- Kodak ProPhoto RGB ICC profile
- Benchmark result JSON and private filenames
