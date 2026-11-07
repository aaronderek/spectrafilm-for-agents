#!/usr/bin/env bash
# Headless wrapper for film.py. Resolves Python next to this script.
# usage: ./run.sh INPUT [-p portra400] [-o out.jpg] [options]   |   ./run.sh --list
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-$HERE/.numba_cache}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$HERE/.cache/matplotlib}"
if [[ -n "${FILM_PYTHON:-}" ]]; then
  PY="$FILM_PYTHON"
elif [[ -x "$HERE/.venv/bin/python" ]]; then
  PY="$HERE/.venv/bin/python"
else
  PY="$(command -v python3)"
fi
exec "$PY" "$HERE/film.py" "$@"
