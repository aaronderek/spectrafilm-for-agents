"""Contract tests for the public CLI. Synthetic data only.

These tests do not render a camera file and do not measure speed.
A full film render needs user-supplied spectral data that this tree does not ship.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "src"))
sys.path.insert(0, str(ROOT))

import film  # noqa: E402


def _run(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged.pop("SPEKTRAFILM_SPECTRAL_LUT_DIR", None)
    merged.pop("SPEKTRAFILM_FILTER_DIR", None)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / "film.py"), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


class CliContract(unittest.TestCase):
    def test_help_documents_sharpening_and_quality_defaults(self):
        result = _run(["--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout
        self.assertIn("--no-sharpen", text)
        self.assertIn("sigma 0.7, amount 0.7", text)
        self.assertIn("default 95", text)
        self.assertIn("Does not cap file", text)

    def test_list_presets(self):
        result = _run(["--list"])
        self.assertEqual(result.returncode, 0, result.stderr)
        for token in ("portra400", "kodachrome", "vision3_500t", "kodak_2383", "kodak_kodachrome_64"):
            self.assertIn(token, result.stdout)

    def test_render_without_spectral_table_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "gradient.jpg"
            image = np.zeros((8, 8, 3), np.uint8)
            image[..., 0] = 180
            image[..., 1] = 100
            image[..., 2] = 60
            from PIL import Image
            Image.fromarray(image, mode="RGB").save(source)
            result = _run([
                str(source), "-p", "portra400", "-o", str(Path(tmp) / "out.jpg"),
                "--accurate", "--no-sharpen", "--max-size", "8", "--quality", "92",
            ])
        self.assertNotEqual(result.returncode, 0)
        combined = result.stderr + result.stdout
        self.assertIn("SPEKTRAFILM_SPECTRAL_LUT_DIR", combined)
        self.assertIn("LICENSING.md", combined)
        self.assertNotIn("wrote ", combined)


class DecodeContract(unittest.TestCase):
    def test_prophoto_description_is_one_prophoto_decode(self):
        import colour
        import tifffile
        encoded = np.full((4, 4, 3), 0.5, np.float32)
        pixels = np.round(encoded * 65535.0).astype(np.uint16)
        normalized = pixels.astype(np.float32) / 65535.0
        prophoto = np.asarray(
            colour.RGB_COLOURSPACES["ProPhoto RGB"].cctf_decoding(normalized),
            dtype=np.float32,
        )
        srgb = np.asarray(
            colour.RGB_COLOURSPACES["sRGB"].cctf_decoding(normalized),
            dtype=np.float32,
        )
        with tempfile.TemporaryDirectory() as tmp:
            prophoto_path = Path(tmp) / "prophoto.tif"
            srgb_path = Path(tmp) / "srgb.tif"
            tifffile.imwrite(prophoto_path, pixels, photometric="rgb", description="ProPhoto RGB")
            tifffile.imwrite(srgb_path, pixels, photometric="rgb", description="sRGB")
            decoded, space, kind = film.load_image(prophoto_path, "as_shot")
            decoded_srgb, space_s, _ = film.load_image(srgb_path, "as_shot")
        self.assertEqual(kind, "display")
        self.assertEqual(space, "ProPhoto RGB")
        self.assertEqual(space_s, "sRGB")
        self.assertTrue(np.allclose(decoded, prophoto, atol=1e-5))
        self.assertTrue(np.allclose(decoded_srgb, srgb, atol=1e-5))
        self.assertFalse(np.allclose(decoded, decoded_srgb, atol=1e-3))
        # A second ProPhoto decode of the linear result is a different image.
        twice = np.asarray(
            colour.RGB_COLOURSPACES["ProPhoto RGB"].cctf_decoding(decoded),
            dtype=np.float32,
        )
        self.assertFalse(np.allclose(decoded, twice, atol=1e-3))

    def test_input_space_override_beats_srgb_description(self):
        import colour
        import tifffile
        pixels = np.full((2, 2, 3), 40000, np.uint16)
        normalized = pixels.astype(np.float32) / 65535.0
        expected = np.asarray(
            colour.RGB_COLOURSPACES["ProPhoto RGB"].cctf_decoding(normalized),
            dtype=np.float32,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tagged-srgb.tif"
            tifffile.imwrite(path, pixels, photometric="rgb", description="sRGB")
            decoded, space, _ = film.load_image(path, "as_shot", input_space="ProPhoto RGB")
        self.assertEqual(space, "ProPhoto RGB")
        self.assertTrue(np.allclose(decoded, expected, atol=1e-5))


class AssetHooks(unittest.TestCase):
    def test_daylight_illuminant_does_not_need_schott_curve(self):
        from spektrafilm.model.illuminants import standard_illuminant
        values = np.asarray(standard_illuminant("D55"), dtype=float)
        self.assertTrue(np.isfinite(values).all())
        self.assertGreater(values.max(), 0)

    def test_default_print_illuminant_requires_user_curve(self):
        from spektrafilm.model.illuminants import standard_illuminant
        with self.assertRaises(FileNotFoundError) as caught:
            standard_illuminant("TH-KG3")
        message = str(caught.exception)
        self.assertIn("heat_absorbing/schott/KG3.csv", message)
        self.assertIn("SPEKTRAFILM_FILTER_DIR", message)

    def test_user_supplied_curve_is_what_th_kg3_applies(self):
        from spektrafilm.model.illuminants import standard_illuminant
        with tempfile.TemporaryDirectory() as tmp:
            curve = Path(tmp) / "heat_absorbing" / "schott"
            curve.mkdir(parents=True)
            wavelengths = np.linspace(300, 800, 12)
            # Flat 50% so the result cannot be the unfiltered blackbody.
            data = np.column_stack([wavelengths, np.full_like(wavelengths, 0.5)])
            np.savetxt(curve / "KG3.csv", data, delimiter=",")
            os.environ["SPEKTRAFILM_FILTER_DIR"] = tmp
            try:
                filtered = np.asarray(standard_illuminant("TH-KG3"), dtype=float)
            finally:
                os.environ.pop("SPEKTRAFILM_FILTER_DIR", None)
                # Drop the module-level filter cache from the failed/previous call.
                from spektrafilm.model.color_filters import schott_kg3_heat_filter
                schott_kg3_heat_filter._transmittance = None
        self.assertTrue(np.isfinite(filtered).all())

    def test_user_supplied_coeff_header_is_read(self):
        from spektrafilm.utils.spectral_upsampling import _load_coeffs_lut
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hanatos_irradiance_xy_coeffs_250304.lut"
            width = height = 2
            # vkdt lut.h layout: magic u32, version u16, channels u8, datatype u8, wd u32, ht u32
            header = struct.pack("<IHBBII", 1234, 2, 4, 1, width, height)
            pixels = np.zeros((width, height, 4), np.float32)
            pixels[..., 1] = 1
            path.write_bytes(header + pixels.tobytes())
            os.environ["SPEKTRAFILM_SPECTRAL_LUT_DIR"] = tmp
            try:
                loaded = _load_coeffs_lut()
            finally:
                os.environ.pop("SPEKTRAFILM_SPECTRAL_LUT_DIR", None)
        self.assertEqual(loaded.shape, (2, 2, 4))
        self.assertTrue(np.allclose(loaded[..., 1], 1))


if __name__ == "__main__":
    unittest.main()
