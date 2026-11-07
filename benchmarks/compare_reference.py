#!/usr/bin/env python3
"""Compare fresh outputs from two runtimes, independently of stale upstream snapshots."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


def render(root, output):
    sys.path[:0] = [str(root), str(root / 'src/src')]
    import numpy as np
    import film
    from spektrafilm import Simulator
    from spektrafilm.utils.raw_file_processor import load_and_process_raw_file
    rng = np.random.default_rng(81)
    image = rng.uniform(0.001, 1.5, (73, 91, 3))
    image[:9, :11] = [2.0, 0.01, 0.02]
    image[-9:, -11:] = [0.01, 0.04, 2.0]
    image[36, 45] = 6.0
    outputs = {}
    for preset, recipe in film.PRESETS.items():
        for accurate in (False, True):
            args = SimpleNamespace(
                film=recipe['film'], paper=recipe['paper'], scan_negative=False,
                no_auto_exposure=False, metering='center_weighted', ev=0.0,
                format='35mm', print_exposure=1.0, y_shift=0.0, m_shift=0.0,
                grain='off', halation='on', halation_boost=None,
                _preset_boost=recipe.get('halation_boost_ev'), accurate=accurate,
                grain_backend='reference', seed=None,
            )
            params, _, slide = film.build_params(args, 'sRGB')
            params.print_render.glare.active = False
            simulator = Simulator(params)
            if slide:
                film.auto_slide_exposure(simulator, params, image, 'sRGB')
                result = simulator.process(image)
            else:
                density = simulator._pipeline.process(image, collect='cmy_film')
                film.auto_print_balance(simulator, params, image, 'sRGB', density)
                result = simulator._pipeline.process(density, inject='cmy_film')
            outputs[f'{preset}_{"spectral" if accurate else "lut"}'] = result
    # Preserve the reference sampler pixel-for-pixel, including actual sublayers.
    args.film, args.paper = 'kodak_portra_400', 'kodak_portra_endura'
    args.grain, args.accurate = 'on', False
    args._preset_boost = None
    params, _, _ = film.build_params(args, 'sRGB')
    params.film_render.grain.micro_structure = (0.0, 0.0)
    params.print_render.glare.active = False
    outputs['reference_grain'] = Simulator(params).process(image)
    # Actual ARW loading with all CLI white-balance modes; compare float32, which
    # is what the original wrapper hands to its pipeline.
    raw_env = os.environ.get('FILM_COMPARE_RAW')
    raw_path = Path(raw_env) if raw_env else None
    if raw_path is not None and raw_path.exists():
        for wb in ('as_shot', 'daylight', 'tungsten'):
            raw = load_and_process_raw_file(raw_path, white_balance=wb, output_colorspace='ProPhoto RGB')
            outputs[f'raw_{wb}'] = np.asarray(raw[::37, ::41], dtype=np.float32)
            del raw
    np.savez(output, **outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=Path('.bench/reference'))
    parser.add_argument('--candidate', type=Path, default=Path('.'))
    parser.add_argument('--report', type=Path, default=Path('benchmarks/results/numerical_parity.json'))
    parser.add_argument('--worker', nargs=2, metavar=('ROOT', 'OUTPUT'))
    args = parser.parse_args()
    if args.worker:
        render(Path(args.worker[0]).resolve(), Path(args.worker[1]))
        return
    os.environ.setdefault('MPLCONFIGDIR', str(Path('.cache/matplotlib').resolve()))
    os.environ.setdefault('NUMBA_CACHE_DIR', str(Path('.numba_cache').resolve()))
    os.environ.setdefault('NUMBA_NUM_THREADS', '8')
    # Force boundaries even for small test pictures.
    os.environ['FILMSIM_CHUNK_PIXELS'] = '1024'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for name, root in [('reference', args.reference), ('candidate', args.candidate)]:
        path = args.report.parent / f'{name}_parity.npz'
        subprocess.run([sys.executable, __file__, '--worker', str(root.resolve()), str(path.resolve())], check=True)
        files.append(path)
    import numpy as np
    reports = {}
    with np.load(files[0]) as reference, np.load(files[1]) as candidate:
        for name in reference.files:
            a, b = reference[name], candidate[name]
            difference = np.abs(a - b)
            tolerance = 2e-7 if name.startswith('raw_') else 2e-10
            reports[name] = dict(max_abs=float(difference.max()), mean_abs=float(difference.mean()),
                                 passed=bool(np.allclose(a, b, rtol=tolerance, atol=tolerance)))
    args.report.write_text(json.dumps(reports, indent=2) + '\n')
    print(json.dumps(reports, indent=2))
    if not all(r['passed'] for r in reports.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
