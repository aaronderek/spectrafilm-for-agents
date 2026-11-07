#!/usr/bin/env python3
"""Decode a DNG (incl. Adobe Project Indigo DNG 1.7 files) with Adobe's own
DNG SDK renderer (dng_validate) and write a 16-bit ProPhoto RGB TIFF that
filmbot/film.py reads losslessly as wide-gamut input.

Why: LibRaw/rawpy ignores the profile's RGBTables (Indigo's colour look) and
ProfileGainTableMap2 (its local tone/gain map). dng_validate 1.7.1 applies
the full camera profile: AsShotNeutral WB, ColorMatrix/ForwardMatrix
interpolation, RGBTables, ProfileGainTableMap2, ProfileToneCurve,
BaselineExposure(+Offset), opcode lens corrections, DefaultCrop, Orientation.

Modes
  sdr (default)  the DNG's default 'SDR' profile, exactly as Adobe renders it
                 (gain map tuned for SDR, highlights already rolled off < 1.0).
  hdr            the DNG's 'HDR' extra profile (linear, overrange up to ~4-8x
                 SDR white), exposure-matched to the SDR render's median, then
                 a hue-preserving soft shoulder folds the overrange into [0,1]
                 so film.py's 16-bit reader keeps highlight gradation.
"""
from __future__ import annotations
import argparse, os, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
DNG_VALIDATE = Path(os.environ["DNG_VALIDATE"]) if os.environ.get("DNG_VALIDATE") else HERE / "bin" / "dng_validate"
DESCRIPTION = "ProPhoto RGB"  # film.py reads this when the TIFF has no ICC profile
PP_Y = np.array([0.2880402, 0.7118741, 0.0000857], np.float32)  # ProPhoto (D50) luminance row


def list_profiles(dng: Path) -> list[str]:
    out = subprocess.run([str(DNG_VALIDATE), "-v", "-d", "1", str(dng)], capture_output=True, text=True).stdout
    return [l.split('"')[1] for l in out.splitlines() if l.startswith("ProfileName:") and '"' in l]


def render(dng: Path, tmp: Path, tag: str, profile: str | None) -> np.ndarray:
    """Adobe final render -> float32 linear ProPhoto RGB (H, W, 3), oriented + cropped."""
    import tifffile
    base = tmp / tag
    cmd = [str(DNG_VALIDATE), "-32", "-cs3"]
    if profile:
        cmd += ["-profile", profile]
    cmd += ["-tif", str(base), str(dng)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    tif = base.with_suffix(".tif")
    if r.returncode != 0 or not tif.exists():
        sys.exit(f"dng_validate failed ({r.returncode}):\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    with tifffile.TiffFile(str(tif)) as t:
        page = t.pages[0]
        a = page.asarray()
        icc = page.tags.get(34675)
        desc = icc_description(icc.value) if icc else ""
    tif.unlink()
    a = np.ascontiguousarray(a[..., :3], dtype=np.float32)
    if "linear" not in desc.lower():
        # SDR profiles come back display-encoded even at -32: Adobe's ProPhoto ICC is a pure 1.8 gamma
        np.power(np.clip(a, 0, None), 1.8, out=a)
    return a


def icc_description(icc: bytes) -> str:
    import io
    from PIL import ImageCms
    try:
        return ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))) or ""
    except Exception:
        return ""


def downscale(lin: np.ndarray, max_size: int) -> np.ndarray:
    """Lanczos in linear light (same method film.py uses)."""
    from PIL import Image
    h, w = lin.shape[:2]
    if not max_size or max(h, w) <= max_size:
        return lin
    s = max_size / max(h, w)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    ch = [np.asarray(Image.fromarray(np.ascontiguousarray(lin[..., c])).resize((nw, nh), Image.LANCZOS))
          for c in range(3)]
    return np.clip(np.stack(ch, axis=-1), 0, None).astype(np.float32)


def shoulder(lin: np.ndarray, knee: float = 0.6) -> np.ndarray:
    """Hue-preserving soft shoulder on max(R,G,B): identity below `knee`,
    extended-Reinhard above it, with the frame's 99.99th-pct peak mapped to 1.0."""
    m = lin.max(axis=-1)
    peak = float(max(np.percentile(m, 99.99), 1.0))
    if peak <= 1.0 and m.max() <= 1.0:
        return lin
    peak = max(peak, float(m.max()) * 0.999, knee + 1e-3)
    u = np.maximum(m - knee, 0) / (1 - knee)
    W = (peak - knee) / (1 - knee)
    f = u * (1 + u / (W * W)) / (1 + u)
    m2 = np.where(m > knee, knee + (1 - knee) * f, m)
    scale = np.where(m > 1e-8, m2 / np.maximum(m, 1e-8), 1.0).astype(np.float32)
    return np.clip(lin * scale[..., None], 0, 1)


def encode_prophoto(lin: np.ndarray) -> np.ndarray:
    import colour
    enc = colour.RGB_COLOURSPACES["ProPhoto RGB"].cctf_encoding(np.clip(lin, 0, 1))
    return (np.asarray(enc) * 65535.0 + 0.5).astype(np.uint16)


def save_preview(lin: np.ndarray, path: Path, long_edge: int = 1600):
    import colour
    from PIL import Image, ImageCms
    small = downscale(lin, long_edge)
    srgb = colour.RGB_to_RGB(small, colour.RGB_COLOURSPACES["ProPhoto RGB"], colour.RGB_COLOURSPACES["sRGB"],
                             chromatic_adaptation_transform="Bradford")
    enc = colour.cctf_encoding(np.clip(srgb, 0, 1), function="sRGB")
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    Image.fromarray((enc * 255 + 0.5).astype(np.uint8)).save(path, quality=92, subsampling=0, icc_profile=icc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output", help="16-bit ProPhoto RGB TIFF to write")
    ap.add_argument("--mode", choices=["sdr", "hdr"], default="sdr")
    ap.add_argument("--max-size", type=int, default=2400)
    ap.add_argument("--knee", type=float, default=0.6, help="hdr mode: shoulder start (linear, SDR white = 1)")
    ap.add_argument("--preview", help="also write an sRGB JPEG preview of the decoded image")
    a = ap.parse_args()
    t0 = time.perf_counter()
    dng = Path(a.input)
    profiles = list_profiles(dng)
    hdr_prof = next((p for p in profiles if p.upper().endswith("HDR")), None)
    with tempfile.TemporaryDirectory(prefix="film-dng-") as td:
        td = Path(td)
        lin = downscale(render(dng, td, "sdr", None), a.max_size)    # default (SDR) profile
        note = f"profile={profiles[-1] if profiles else 'default'}"
        if a.mode == "hdr":
            if not hdr_prof:
                print("[film-dng] no HDR profile in this DNG; using the SDR render", file=sys.stderr)
            else:
                hdr = downscale(render(dng, td, "hdr", hdr_prof), a.max_size)
                g = float(np.median(lin @ PP_Y) / max(np.median(hdr @ PP_Y), 1e-6))
                over = float((hdr * g > 1).mean())
                lin = shoulder(hdr * g, a.knee)
                del hdr
                note = f"profile={hdr_prof}, exposure x{g:.2f}, {over*100:.2f}% overrange folded by shoulder"
    clip = float((lin >= 0.9999).any(axis=-1).mean())
    import tifffile
    tifffile.imwrite(a.output, encode_prophoto(lin), photometric="rgb", compression="zlib", description=DESCRIPTION)
    if a.preview:
        save_preview(lin, Path(a.preview))
    h, w = lin.shape[:2]
    print(f"[film-dng] Adobe DNG SDK render, {note}; {w}x{h}; pixels at 1.0: {clip*100:.3f}%; "
          f"{time.perf_counter()-t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
