#!/usr/bin/env python3
"""Measure one CLI run in a fresh process; use the same arguments for both roots."""
import argparse
import cProfile
import hashlib
import importlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--capture', type=Path, help='Save encoded floating-point output for quality comparisons')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    root = args.root.resolve()
    os.environ.setdefault('MPLCONFIGDIR', str(Path('.cache/matplotlib').resolve()))
    os.environ.setdefault('NUMBA_CACHE_DIR', str(Path('.numba_cache').resolve()))
    sys.path[:0] = [str(root), str(root / 'src/src')]
    cli_args = args.args[1:] if args.args[:1] == ['--'] else args.args
    started = time.perf_counter()
    film = importlib.import_module('film')
    if args.capture:
        save = film.save_outputs
        def capture(enc, *a, **kw):
            import numpy as np
            args.capture.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.capture, enc)
            return save(enc, *a, **kw)
        film.save_outputs = capture
    profiler = cProfile.Profile() if args.profile else None
    if profiler:
        profiler.enable()
    code = film.main(cli_args)
    elapsed = time.perf_counter() - started
    if profiler:
        profiler.disable()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    report = dict(root=str(root), args=cli_args, elapsed_s=elapsed,
                  peak_rss_mib=usage.ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024),
                  user_s=usage.ru_utime, system_s=usage.ru_stime, exit_code=code,
                  python=sys.version, platform=sys.platform,
                  threads={k: os.getenv(k) for k in ('NUMBA_NUM_THREADS', 'OMP_NUM_THREADS',
                                                    'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')})
    # Make reports auditable even when the working tree changes between runs.
    sources = [root / 'film.py', *sorted((root / 'src/src/spektrafilm').rglob('*.py'))]
    source_hash = hashlib.sha256()
    for path in sources:
        source_hash.update(str(path.relative_to(root)).encode())
        source_hash.update(path.read_bytes())
    report['source_sha256'] = source_hash.hexdigest()
    report['color_backend'] = os.getenv('FILMSIM_COLOR_BACKEND', 'original')
    if 'numba' in sys.modules:
        import numba
        report['numba_workers'] = numba.get_num_threads()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    if profiler:
        profiler.dump_stats(str(args.report.with_suffix('.prof')))
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
