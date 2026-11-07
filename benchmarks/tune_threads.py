#!/usr/bin/env python3
"""Serial, fresh-process thread sweep after warming both CLI image sizes."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--threads', nargs='+', type=int, default=[4, 8, 12, 18])
    parser.add_argument('--sizes', nargs='+', type=int, default=[2400, 0])
    parser.add_argument('--repeat', type=int, default=2)
    args = parser.parse_args()
    if args.repeat < 1 or min(args.threads) < 1 or min(args.sizes) < 0:
        parser.error('repeat/threads must be positive and sizes nonnegative')
    reports = ROOT / 'benchmarks/results/thread_sweep'
    reports.mkdir(parents=True, exist_ok=True)
    logs = ROOT / '.bench/thread_sweep'
    logs.mkdir(parents=True, exist_ok=True)
    samples = {}

    def run(size, workers, label):
        report = reports / f'{label}.json'
        with (logs / f'{label}.log').open('w') as log:
            subprocess.run([sys.executable, str(ROOT / 'benchmarks/measure.py'),
                            '--report', str(report), '--', str(args.input.resolve()),
                            '--max-size', str(size), '--threads', str(workers), '--seed', '42',
                            '--timings', '-o', str(logs / 'output.jpg')],
                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = json.loads(report.read_text())
        print(f'{label}: {result["elapsed_s"]:.3f}s, {result["peak_rss_mib"]:.0f} MiB', flush=True)
        return result

    for size in args.sizes:
        run(size, args.threads[0], f'warmup_{size}')
        for repeat in range(args.repeat):
            # Reverse alternating runs to reduce ordering/temperature bias.
            workers_order = args.threads if repeat % 2 == 0 else args.threads[::-1]
            for workers in workers_order:
                sample = run(size, workers, f'size{size}_threads{workers}_run{repeat + 1}')
                samples.setdefault(f'{size}px_{workers}threads', []).append(sample)
    summary = {key: dict(median_s=statistics.median(r['elapsed_s'] for r in rows),
                         max_rss_mib=max(r['peak_rss_mib'] for r in rows),
                         samples=len(rows)) for key, rows in samples.items()}
    (reports / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
