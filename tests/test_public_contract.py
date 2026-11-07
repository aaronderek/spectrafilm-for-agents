"""Contract tests for the public CLI. Synthetic data only.

These tests do not render a camera file and do not measure speed.
Default presets use the spectral table and filter curves shipped in the package.
"""
from __future__ import annotations

import io
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

    def test_no_sharpen_is_opt_in(self):
        from types import SimpleNamespace
        fields = dict(
            film="kodak_portra_400", paper="kodak_portra_endura", scan_negative=False,
            no_auto_exposure=False, metering="center_weighted", ev=0.0, format="35mm",
            print_exposure=1.0, y_shift=0.0, m_shift=0.0, grain="off", halation="on",
            halation_boost=None, _preset_boost=None, accurate=True,
            grain_backend="parallel", seed=1, no_sharpen=False,
        )
        default, _, _ = film.build_params(SimpleNamespace(**fields), "sRGB")
        fields["no_sharpen"] = True
        explicit, _, _ = film.build_params(SimpleNamespace(**fields), "sRGB")
        self.assertEqual(tuple(default.scanner.unsharp_mask), (0.7, 0.7))
        self.assertEqual(tuple(explicit.scanner.unsharp_mask), (0.0, 0.0))

    def test_list_presets(self):
        result = _run(["--list"])
        self.assertEqual(result.returncode, 0, result.stderr)
        for token in ("portra400", "kodachrome", "vision3_500t", "kodak_2383", "kodak_kodachrome_64"):
            self.assertIn(token, result.stdout)

    def test_bundled_presets_render_without_external_dirs(self):
        from PIL import Image, ImageCms
        presets = (
            ("portra400", "kodak_portra_endura", False),
            ("kodachrome", "slide, direct scan", True),
            ("vision3_500t", "kodak_2383", False),
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "gradient.jpg"
            height, width = 48, 64
            x = np.linspace(40, 220, width, dtype=np.float32)
            y = np.linspace(30, 180, height, dtype=np.float32)
            rgb = np.empty((height, width, 3), np.float32)
            rgb[..., 0] = x
            rgb[..., 1] = y[:, None]
            rgb[..., 2] = 80
            Image.fromarray(rgb.astype(np.uint8), mode="RGB").save(source, quality=95)
            common = [
                "--accurate", "--no-sharpen", "--halation", "3", "--halation-boost", "2.5",
                "--quality", "92", "--max-size", "32", "--seed", "7",
            ]
            for preset, marker, slide in presets:
                output = Path(tmp) / f"{preset}.jpg"
                result = _run([str(source), "-p", preset, "-o", str(output), *common])
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertIn("halation=3", result.stdout)
                self.assertIn(marker, result.stdout)
                if slide:
                    self.assertIn("direct scan", result.stdout)
                with Image.open(output) as image:
                    icc = image.info.get("icc_profile")
                    self.assertIsNotNone(icc)
                    description = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))) or ""
                    self.assertIn("sRGB", description)
                    self.assertEqual(list(image.getexif()), [])
                    self.assertGreater(output.stat().st_size, 0)


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

    def test_default_print_illuminant_uses_bundled_curve(self):
        from spektrafilm.model.color_filters import schott_kg3_heat_filter
        from spektrafilm.model.illuminants import standard_illuminant
        os.environ.pop("SPEKTRAFILM_FILTER_DIR", None)
        schott_kg3_heat_filter._transmittance = None
        values = np.asarray(standard_illuminant("TH-KG3"), dtype=float)
        self.assertTrue(np.isfinite(values).all())
        self.assertGreater(values.max(), 0)

    def test_user_supplied_curve_is_what_th_kg3_applies(self):
        from spektrafilm.model.color_filters import schott_kg3_heat_filter
        from spektrafilm.model.illuminants import standard_illuminant
        schott_kg3_heat_filter._transmittance = None
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
