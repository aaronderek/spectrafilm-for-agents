"""Locations for data this repository does not redistribute.

The spectral coefficient table and the manufacturer filter curves are not
bundled. Callers pass a directory they are allowed to read. This module does
not download anything.
"""
from __future__ import annotations

import os
from pathlib import Path

SPECTRAL_LUT_DIR_ENV = "SPEKTRAFILM_SPECTRAL_LUT_DIR"
FILTER_DIR_ENV = "SPEKTRAFILM_FILTER_DIR"
COEFFS_LUT_NAME = "hanatos_irradiance_xy_coeffs_250304.lut"
SPECTRA_NPY_NAME = "irradiance_xy_tc.npy"


def spectral_lut_dir() -> Path | None:
    raw = os.environ.get(SPECTRAL_LUT_DIR_ENV)
    if not raw:
        return None
    return Path(raw).expanduser()


def filter_dir() -> Path | None:
    raw = os.environ.get(FILTER_DIR_ENV)
    if not raw:
        return None
    return Path(raw).expanduser()


def spectral_file(name: str) -> Path | None:
    directory = spectral_lut_dir()
    if directory is None:
        return None
    path = directory / name
    return path if path.is_file() else None


def missing_spectral_table(name: str) -> FileNotFoundError:
    return FileNotFoundError(
        f"Required spectral table {name} is not in this installation. "
        f"Set {SPECTRAL_LUT_DIR_ENV} to a directory that contains "
        f"{COEFFS_LUT_NAME} and/or {SPECTRA_NPY_NAME}. "
        "Those files are not distributed here because a redistribution license "
        "was not established. See LICENSING.md. This process does not download them."
    )


def filter_override(relative: str) -> Path | None:
    directory = filter_dir()
    if directory is None:
        return None
    path = directory / relative
    return path if path.is_file() else None


def missing_filter_curve(relative: str) -> FileNotFoundError:
    return FileNotFoundError(
        f"Filter curve {relative} is not in this installation. "
        f"Set {FILTER_DIR_ENV} to a directory that contains that relative path. "
        "Manufacturer spectra are not distributed here because a redistribution "
        "license was not established. See LICENSING.md. This process does not download them."
    )
