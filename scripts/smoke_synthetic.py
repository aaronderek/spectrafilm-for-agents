#!/usr/bin/env python3
"""Run the CLI on generated gradients. Not a speed benchmark."""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms


ROOT = Path(__file__).resolve().parents[1]


def gradient(path: Path, size=(96, 64)) -> None:
    h, w = size[1], size[0]
    x = np.linspace(0.05, 0.95, w, dtype=np.float32)
    y = np.linspace(0.15, 0.85, h, dtype=np.float32)
    rgb = np.empty((h, w, 3), dtype=np.float32)
    rgb[..., 0] = x[None, :]
    rgb[..., 1] = y[:, None]
    rgb[..., 2] = 0.5 * x[None, :] + 0.25
    image = Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8), mode="RGB")
    image.save(path, quality=95, subsampling=0)


def run(args: list[str]) -> str:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "film.py"), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def assert_jpeg(path: Path) -> None:
    with Image.open(path) as image:
        icc = image.info.get("icc_profile")
        if not icc:
            raise SystemExit(f"missing ICC: {path}")
        description = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))) or ""
        if "sRGB" not in description and "srgb" not in description.lower():
            raise SystemExit(f"unexpected ICC description {description!r} for {path}")
        exif = list(image.getexif())
        if exif:
            raise SystemExit(f"output carried EXIF tags: {exif}")
        print(f"ok {path.name} {image.size} icc={description!r} bytes={path.stat().st_size}")


def main() -> None:
    listing = run(["--list"])
    for token in ("portra400", "kodachrome", "vision3_500t", "kodak_2383", "kodak_kodachrome_64"):
        if token not in listing:
            raise SystemExit(f"--list missing {token}")
    run(["--help"])
    with tempfile.TemporaryDirectory(prefix="spectrafilm-smoke-") as tmp:
        folder = Path(tmp)
        source = folder / "gradient.jpg"
        gradient(source)
        common = [
            "--accurate", "--no-sharpen", "--halation", "3", "--halation-boost", "2.5",
            "--quality", "92", "--max-size", "64", "--seed", "7",
        ]
        negative = folder / "portra.jpg"
        reversal = folder / "kodachrome.jpg"
        run([str(source), "-p", "portra400", "-o", str(negative), *common])
        run([str(source), "-p", "kodachrome", "-o", str(reversal), *common])
        assert_jpeg(negative)
        assert_jpeg(reversal)
    print("smoke ok")


if __name__ == "__main__":
    main()
