#!/usr/bin/env python3
"""96 MP synthetic default-effects test. Excludes RAW demosaicing and export."""
import argparse
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('NUMBA_NUM_THREADS', str(min(12, os.cpu_count() or 1)))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
os.environ.setdefault('NUMBA_CACHE_DIR', str(ROOT / '.numba_cache'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=12000)
    parser.add_argument('--height', type=int, default=8000)
    parser.add_argument('--report', type=Path, default=ROOT / 'benchmarks/results/stress_96mp.json')
    args = parser.parse_args()
    if min(args.width, args.height) < 1:
        parser.error('dimensions must be positive')
    import film
    import numpy as np
    import numba
    from spektrafilm import Simulator, init_params, digest_params
    started = time.perf_counter()
    image = np.empty((args.height, args.width, 3), dtype=np.float32)
    ramp = np.linspace(0.001, 1.0, args.width, dtype=np.float32)
    for ch in range(3):
        image[..., ch] = ramp ** (1.0 + ch * 0.15)
    image[args.height//2:args.height//2+5, args.width//2:args.width//2+5] = 4.0
    p = init_params('kodak_portra_400', 'kodak_portra_endura')
    p.io.input_cctf_decoding = False
    p.io.output_cctf_encoding = False
    p.settings.use_enlarger_lut = True
    p.settings.use_scanner_lut = True
    p.camera.film_format_mm = 36.0
    p = digest_params(p)
    p.film_render.grain.backend = 'parallel'
    p.film_render.grain.seed = 42
    p.print_render.glare.seed = 42
    sim = Simulator(p)
    density = sim._pipeline.process(image, collect='cmy_film')
    print('Film stage finished', time.perf_counter() - started, flush=True)
    film.auto_print_balance(sim, p, image, 'sRGB', density, scene_referred=True)
    del image
    result = sim._pipeline.process(density, inject='cmy_film')
    del density
    for row in range(0, args.height, 128):
        assert np.isfinite(result[row:row+128]).all()
    report = dict(shape=list(result.shape), megapixels=args.width * args.height / 1e6,
                  elapsed_s=time.perf_counter() - started,
                  peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024),
                  finite=True, numba_workers=numba.get_num_threads(),
                  color_backend=os.environ.get('FILMSIM_COLOR_BACKEND', 'compiled'),
                  microstructure_applied=bool(p.film_render.grain.micro_structure[1] * 0.001
                                               / sim._pipeline._resize_service.pixel_size_um > 0.05),
                  features='grain, halation, DIR diffusion, auto exposure, print balance, glare, CAM16, unsharp',
                  input='synthetic linear RGB; excludes RAW decode and file export')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
