"""Bundled spectral and filter data, with optional local overrides.

The default presets read the tables shipped in this package. Set
SPEKTRAFILM_SPECTRAL_LUT_DIR or SPEKTRAFILM_FILTER_DIR only to replace a
file. This module does not download anything.

Those bundled bytes are the copies already distributed with upstream
spektrafilm. A separate redistribution grant for the Hanatos coefficient
table and the manufacturer curves was not established. See LICENSING.md.
That notice is not a claim that the files are absent, and it is not a
claim that they are all GPL.
"""
from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

SPECTRAL_LUT_DIR_ENV = "SPEKTRAFILM_SPECTRAL_LUT_DIR"
FILTER_DIR_ENV = "SPEKTRAFILM_FILTER_DIR"
COEFFS_LUT_NAME = "hanatos_irradiance_xy_coeffs_250304.lut"
SPECTRA_NPY_NAME = "irradiance_xy_tc.npy"


def _env_dir(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    return Path(raw).expanduser()


def spectral_override(name: str) -> Path | None:
    directory = _env_dir(SPECTRAL_LUT_DIR_ENV)
    if directory is None:
        return None
    path = directory / name
    return path if path.is_file() else None


def packaged_spectral(name: str):
    resource = files("spektrafilm.data.luts.spectral_upsampling").joinpath(name)
    try:
        if resource.is_file():
            return resource
    except (FileNotFoundError, OSError, TypeError):
        return None
    return None


def open_spectral(name: str):
    override = spectral_override(name)
    if override is not None:
        return override.open("rb")
    packaged = packaged_spectral(name)
    if packaged is not None:
        return packaged.open("rb")
    raise FileNotFoundError(
        f"Required spectral table {name} is not in this installation and "
        f"{SPECTRAL_LUT_DIR_ENV} does not point at a copy. "
        "A normal install includes the upstream spektrafilm table. See LICENSING.md."
    )


def filter_override(relative: str) -> Path | None:
    directory = _env_dir(FILTER_DIR_ENV)
    if directory is None:
        return None
    path = directory / relative
    return path if path.is_file() else None


def missing_filter_curve(relative: str) -> FileNotFoundError:
    return FileNotFoundError(
        f"Filter curve {relative} is not in this installation and "
        f"{FILTER_DIR_ENV} does not point at a copy. "
        "A normal install includes the upstream spektrafilm curves used by the "
        "default presets. See LICENSING.md."
    )
