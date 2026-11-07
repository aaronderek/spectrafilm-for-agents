#!/usr/bin/env python3
"""Run the public contract tests. Synthetic data only. Not a speed benchmark."""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tests.test_public_contract as contract  # noqa: E402


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(contract)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
