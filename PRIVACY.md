# Privacy check for this publication

This file records what was inspected before the first public push of the film CLI. It is not a guarantee that every possible personal trace is absent.

Date of the check: 2026-11-07. The candidate archive was extracted outside the git work tree, reviewed, and not committed.

## What was included

Optimized `spektrafilm` 0.3.4 runtime sources, stock JSON, ICC profiles, spectral LUT data, the headless CLI, license texts, the historical performance write-up, benchmark scripts, and optional adapter scripts.

## What was left out

- User photographs and camera RAW files
- Virtualenvs, Numba caches, Python caches, macOS AppleDouble files
- GUI and LUT-creator applications
- The Adobe `dng_validate` binary and any SDK toolchain
- A Kodak ProPhoto RGB ICC profile whose copyright line is "all rights reserved"
- Raw benchmark JSON, profiles, and logs that contained machine paths and private RAW filenames
- Agent checkpoints, install logs, and backup archives
- The candidate archive itself

## What was scanned

- Every filename and relative path in the candidate tree
- Text of Python, Markdown, TOML, shell, JSON, and license files for home-directory prefixes, cloud account names, private keys, and token shapes
- Printable strings in the large LUT, the `.npy` table, and ICC profiles
- A search for image payloads (JPEG, PNG, HEIC, DNG, ARW). None were in the tree

Hits in the candidate write-up were internal staging paths and the words used to say that secrets were absent. Those staging notes were not published. Upstream author emails that already appear in the public spektrafilm `CITATION.cff` and license preamble are still present, because they are part of the upstream notices.

Benchmark scripts no longer contain a dated private RAW filename. `benchmarks/compare_reference.py` reads a RAW path only from the `FILM_COMPARE_RAW` environment variable.

Output JPEGs from the CLI are new files with an sRGB ICC profile. The writer does not copy source EXIF.

## Still your responsibility

Do not put pictures into `inbox/` or `outbox/` and commit them. Local benchmark JSON can contain absolute paths; those directories are gitignored, and a later `git add -f` would bypass that. This review did not examine machines other than the candidate tree.
