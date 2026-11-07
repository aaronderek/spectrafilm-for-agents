#!/usr/bin/env python3
"""filmbot: headless CLI for the spektrafilm spectral film engine.

Film modeling powered by spektrafilm (c) Andrea Volpato, GPL-3.0
https://github.com/andreavolpato/spektrafilm
The bundled runtime includes tested CPU and memory optimizations; pipeline
taps support per-frame print balancing. This wrapper is GPL-3.0 as well.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
import warnings
from pathlib import Path

# Always use the bundled, optimized runtime, including non-editable installs.
_SOURCE = Path(__file__).resolve().parent / 'src' / 'src'
if _SOURCE.is_dir():
    sys.path.insert(0, str(_SOURCE))

warnings.filterwarnings("ignore")

RAW_EXT = {".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2", ".pef", ".srw", ".3fr", ".iiq"}
HEIC_EXT = {".heic", ".heif", ".avif"}

# ----------------------------------------------------------------------------
# Presets. Each one only sets spektrafilm parameters; nothing else is done
# to the colours. Keys: film, paper, plus optional parameter overrides.
# ----------------------------------------------------------------------------
PRESETS: dict[str, dict] = {
    "portra400":   dict(film="kodak_portra_400",   paper="kodak_portra_endura",
                        desc="Kodak Portra 400 on Portra Endura: soft contrast, warm natural skin"),
    "portra160":   dict(film="kodak_portra_160",   paper="kodak_portra_endura",
                        desc="Kodak Portra 160: finer grain, slightly cooler than 400"),
    "portra800":   dict(film="kodak_portra_800",   paper="kodak_portra_endura",
                        desc="Kodak Portra 800: more grain, punchier"),
    "ektar100":    dict(film="kodak_ektar_100",    paper="kodak_supra_endura",
                        desc="Kodak Ektar 100 on Supra Endura: saturated, fine grain, landscapes"),
    "gold200":     dict(film="kodak_gold_200",     paper="kodak_supra_endura",
                        desc="Kodak Gold 200 on Supra Endura: warm consumer look"),
    "ultramax400": dict(film="kodak_ultramax_400", paper="kodak_supra_endura",
                        desc="Kodak Ultramax 400: consumer, punchy, grainy"),
    "fuji_c200":   dict(film="fujifilm_c200",      paper="fujifilm_crystal_archive_typeii",
                        desc="Fujifilm C200 on Crystal Archive: cool greens, consumer"),
    "pro400h":     dict(film="fujifilm_pro_400h",  paper="fujifilm_crystal_archive_typeii",
                        desc="Fujifilm Pro 400H on Crystal Archive: pastel, airy"),
    "xtra400":     dict(film="fujifilm_xtra_400",  paper="fujifilm_crystal_archive_typeii",
                        desc="Fujifilm X-Tra/Superia 400: consumer, green-ish shadows"),
    "vision3_500t": dict(film="kodak_vision3_500t", paper="kodak_2383", halation_boost_ev=1.5,
                        desc="Kodak Vision3 500T printed on 2383: cinema look, strong halation on lights"),
    "vision3_250d": dict(film="kodak_vision3_250d", paper="kodak_2383",
                        desc="Kodak Vision3 250D printed on 2383: daylight cinema look"),
    "velvia":      dict(film="fujifilm_velvia_100", paper=None,
                        desc="Fujifilm Velvia 100 slide (scanned directly): very saturated, contrasty"),
    "provia":      dict(film="fujifilm_provia_100f", paper=None,
                        desc="Fujifilm Provia 100F slide (scanned directly): neutral slide film"),
    "ektachrome":  dict(film="kodak_ektachrome_100", paper=None,
                        desc="Kodak Ektachrome E100 slide (scanned directly)"),
    "kodachrome":  dict(film="kodak_kodachrome_64", paper=None,
                        desc="Kodak Kodachrome 64 slide (scanned directly)"),
}
DEFAULT_PAPER = "kodak_portra_endura"
FORMAT_MM = {"35mm": 36.0, "120": 70.0, "6x6": 56.0, "6x7": 70.0, "4x5": 120.0, "half": 24.0}


def die(msg: str, code: int = 2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


# ----------------------------------------------------------------------------
# Input loading -> float32 linear RGB + the colour space name for spektrafilm
# ----------------------------------------------------------------------------
def _named_colorspace(text: str | None) -> str | None:
    """Map a TIFF description or profile name onto a colour-science space."""
    if not text:
        return None
    import colour
    stripped = text.strip()
    if stripped in colour.RGB_COLOURSPACES:
        return stripped
    low = stripped.lower()
    if "prophoto" in low or "romm" in low:
        return "ProPhoto RGB"
    if "display p3" in low or "display-p3" in low:
        return "Display P3"
    if "adobe" in low and "rgb" in low:
        return "Adobe RGB (1998)"
    if "2020" in low:
        return "ITU-R BT.2020"
    if "srgb" in low:
        return "sRGB"
    return None


def _icc_colorspace(icc_bytes: bytes | None) -> str:
    """Map an embedded ICC profile to a colour-science colourspace name."""
    if not icc_bytes:
        return "sRGB"
    try:
        from PIL import ImageCms
        prof = ImageCms.ImageCmsProfile(io.BytesIO(icc_bytes))
        desc = (ImageCms.getProfileDescription(prof) or "").lower()
    except Exception:
        return "sRGB"
    if "p3" in desc:
        return "Display P3"
    if "adobe" in desc and "rgb" in desc:
        return "Adobe RGB (1998)"
    if "prophoto" in desc or "romm" in desc:
        return "ProPhoto RGB"
    if "2020" in desc:
        return "ITU-R BT.2020"
    return "sRGB"


def _decode(arr, space: str):
    """Display-encoded [0,1] -> linear, using the space's own transfer function."""
    import colour
    import numpy as np
    cs = colour.RGB_COLOURSPACES[space]
    from spektrafilm.utils.chunks import map_image_blocks
    return map_image_blocks(arr, cs.cctf_decoding, dtype=np.float32)


def load_image(path: Path, raw_wb: str, raw_half_size: bool = False, input_space: str | None = None):
    import numpy as np
    ext = path.suffix.lower()
    if ext in RAW_EXT:
        if input_space:
            die("--input-space applies to rendered JPEG, TIFF, and HEIF files. "
                "LibRaw RAW files are decoded to linear ProPhoto RGB.")
        from spektrafilm.utils.raw_file_processor import load_and_process_raw_file
        # rawpy demosaic -> linear ACES -> linear ProPhoto (scene referred, wide gamut)
        rgb = load_and_process_raw_file(str(path), white_balance=raw_wb,
                                        output_colorspace="ProPhoto RGB", output_cctf_encoding=False,
                                        half_size=raw_half_size)
        return np.ascontiguousarray(rgb, dtype=np.float32), "ProPhoto RGB", "libraw"

    from PIL import Image, ImageOps
    if ext in HEIC_EXT:
        import pillow_heif
        pillow_heif.register_heif_opener()

    img = Image.open(path)
    icc = img.info.get("icc_profile")
    img = ImageOps.exif_transpose(img)
    tiff_desc = None
    mode = img.mode
    if mode in ("I;16", "I;16B", "I;16L", "I"):
        arr = np.asarray(img, dtype=np.float32) / (65535.0 if mode.startswith("I;16") else max(1.0, float(np.max(img))))
        arr = np.repeat(arr[..., None], 3, axis=2)
    elif ext in (".tif", ".tiff", ".png"):
        # 16-bit / float RGB files: Pillow can't hold them, use tifffile/OIIO
        arr = None
        try:
            if ext in (".tif", ".tiff"):
                import tifffile
                with tifffile.TiffFile(str(path)) as tiff:
                    a = tiff.asarray()
                    tiff_desc = tiff.pages[0].description or ""
            else:
                import OpenImageIO as oiio
                a = oiio.ImageInput.open(str(path)).read_image()
            a = np.asarray(a)
            if a.ndim == 3 and a.shape[-1] >= 3 and a.dtype != np.uint8:
                if a.dtype == np.uint16:
                    arr = a[..., :3].astype(np.float32) / 65535.0
                elif a.dtype.kind == "f":
                    arr = a[..., :3].astype(np.float32)
        except Exception:
            arr = None
        if arr is None:
            arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
        else:
            # undo the exif rotation skip: tifffile path ignores orientation (rare for TIFF)
            pass
    else:
        arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    if input_space:
        space = input_space
    elif icc:
        space = _icc_colorspace(icc)
    else:
        space = _named_colorspace(tiff_desc) or "sRGB"
    lin = _decode(np.clip(arr, 0.0, None), space)
    return np.ascontiguousarray(lin), space, "display"


def downscale(lin, max_size: int):
    """Lanczos downscale in linear light (per channel, float)."""
    import numpy as np
    from PIL import Image
    h, w = lin.shape[:2]
    long_edge = max(h, w)
    if not max_size or long_edge <= max_size:
        return lin
    s = max_size / long_edge
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    result = np.empty((nh, nw, 3), dtype=np.float32)
    for c in range(3):
        result[..., c] = np.asarray(Image.fromarray(np.ascontiguousarray(lin[..., c])).resize((nw, nh), Image.LANCZOS))
    np.maximum(result, 0, out=result)
    return result


# ----------------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------------
def build_params(args, input_space: str):
    from spektrafilm import init_params, digest_params

    film = args.film
    film_is_slide = film in {"fujifilm_velvia_100", "fujifilm_provia_100f",
                             "kodak_ektachrome_100", "kodak_kodachrome_64"}
    paper = args.paper or DEFAULT_PAPER
    p = init_params(film_profile=film, print_profile=paper)

    # IO: we hand the engine linear RGB in a named space and take linear sRGB back,
    # then apply the sRGB curve ourselves (so 16-bit TIFF and JPEG match).
    p.io.input_color_space = input_space
    p.io.input_cctf_decoding = False
    p.io.output_color_space = "sRGB"
    p.io.output_cctf_encoding = False
    p.io.scan_film = film_is_slide or args.scan_negative

    # camera / exposure
    p.camera.auto_exposure = not args.no_auto_exposure
    p.camera.auto_exposure_method = args.metering
    p.camera.exposure_compensation_ev = args.ev
    p.camera.film_format_mm = FORMAT_MM[args.format]

    # print: auto print exposure + database neutral filters (print auto-balance)
    p.enlarger.print_exposure_compensation = True
    p.settings.neutral_print_filters_from_database = True
    p.enlarger.print_exposure = args.print_exposure
    p.enlarger.y_filter_shift = args.y_shift
    p.enlarger.m_filter_shift = args.m_shift

    # grain
    g = args.grain
    if g in ("off", "0", "none", "false"):
        p.film_render.grain.active = False
    else:
        p.film_render.grain.active = True
        strength = 1.0 if g in ("on", "true") else float(g)
        if strength <= 0:
            p.film_render.grain.active = False
        else:
            # grain noise std ~ sqrt(particle area) -> area scales with strength^2
            p.film_render.grain.particle_area_um2 *= strength ** 2

    p = digest_params(p)  # applies stock-specific couplers/halation presets + neutral filters
    p.film_render.grain.backend = args.grain_backend
    p.film_render.grain.seed = args.seed
    p.print_render.glare.seed = args.seed
    if args.seed is None and args.grain_backend == 'parallel':
        import numpy as np
        p.film_render.grain.seed = int(np.random.randint(0, 2**32, dtype=np.uint32))

    # halation (set after digest so the stock's physical preset is kept)
    h = p.film_render.halation
    if args.halation == "off":
        h.active = False
    else:
        h.active = True
        try:
            amt = 1.0 if args.halation == "on" else float(args.halation)
        except ValueError:
            die("--halation must be on, off or a number")
        h.halation_amount = amt
        if args.halation_boost is not None:
            h.boost_ev = args.halation_boost
        elif args._preset_boost is not None:
            h.boost_ev = args._preset_boost
    if not args.accurate:
        p.settings.use_enlarger_lut = True
        p.settings.use_scanner_lut = True
    # Schema default is scanner unsharp (0.7, 0.7). Opt out explicitly.
    if getattr(args, "no_sharpen", False):
        p.scanner.unsharp_mask = (0.0, 0.0)
    return p, paper, film_is_slide



# ----------------------------------------------------------------------------
# Auto print balance ("lab tech" step)
# ----------------------------------------------------------------------------
def _block_mean(a, target=256):
    import numpy as np
    f = max(1, max(a.shape[:2]) // target)
    h, w = (a.shape[0] // f) * f, (a.shape[1] // f) * f
    return a[:h, :w].reshape(h // f, f, w // f, f, a.shape[2]).mean(axis=(1, 3))


def _stats(rgb, mask):
    """[log(R/G), log(B/G)] of the masked mean (gray-world) + log2 median luminance."""
    import numpy as np
    m = np.clip(rgb[mask].mean(axis=0), 1e-6, None)
    lum = np.clip(rgb @ np.array([0.2126, 0.7152, 0.0722]), 1e-6, None)
    return np.array([np.log(m[0] / m[1]), np.log(m[2] / m[1]), np.log2(np.median(lum))])


def auto_print_balance(sim, params, lin, input_space, cmy_film, color_strength=1.0,
                       match_density=True, scene_referred=False, iters=4):
    """Per-frame printing, like a lab operator does it.

    The engine's neutral filters (from its database) and print exposure are
    calibrated for an 18% grey under the reference light. A phone JPEG is
    already white-balanced and tone-mapped, so here we adjust only the
    enlarger's Y/M dichroic filters and the print exposure until the print's
    gray-world colour balance (color_strength: 1 = same as the input, 0 = engine
    default) and median brightness (if match_density) match the input photo.
    The engine still renders everything else (curves, dye spectra, couplers,
    grain, halation). Runs on a ~256px copy of the developed negative: <1 s.
    """
    import numpy as np
    import colour
    pl = sim._pipeline  # Simulator.process() does not expose pipeline taps; the pipeline does
    small_cmy = _block_mean(cmy_film)
    ref = _block_mean(lin)
    if input_space != "sRGB":
        ref = colour.RGB_to_RGB(ref, colour.RGB_COLOURSPACES[input_space], colour.RGB_COLOURSPACES["sRGB"])
    ref = np.clip(ref, 0, None)
    if scene_referred:   # RAW: no display brightness to match, aim for a normal mid-grey
        ref = ref * (0.184 / max(np.median(ref @ np.array([0.2126, 0.7152, 0.0722])), 1e-6))
    lum = ref @ np.array([0.2126, 0.7152, 0.0722])
    lo, hi = np.percentile(lum, [3, 97])
    mask = (lum >= lo) & (lum <= hi) & (ref.min(axis=-1) > 0) & (ref.max(axis=-1) < 0.98)
    if mask.sum() < 50:
        mask = np.ones(lum.shape, bool)

    y0, m0, pe0 = params.enlarger.y_filter_neutral, params.enlarger.m_filter_neutral, params.enlarger.print_exposure

    def apply(x):
        sim.soft_update(y_filter_neutral=y0 + x[0], m_filter_neutral=m0 + x[1], print_exposure=pe0 * 2.0 ** x[2])

    def render(x):
        apply(x)
        return _stats(pl.process(small_cmy, inject="cmy_film"), mask)

    s_in = _stats(ref, mask)
    x = np.zeros(3)
    s0 = render(x)
    target = s0.copy()
    target[:2] += color_strength * (s_in[:2] - s0[:2])
    free = [0, 1] if color_strength > 0 else []
    if match_density:
        target[2] = s_in[2]
        free.append(2)
    if not free:
        apply(x)
        return x
    deltas = np.array([4.0, 4.0, 0.25])
    J = np.zeros((3, 3))
    for j in free:
        e = np.zeros(3); e[j] = deltas[j]
        J[:, j] = (render(e) - s0) / deltas[j]
    lims = np.array([40.0, 40.0, 2.0])
    s = s0
    for _ in range(iters):
        step = np.zeros(3)
        step[free] = np.linalg.lstsq(J[np.ix_(free, free)], (target - s)[free], rcond=None)[0]
        x = np.clip(x + step, -lims, lims)
        s = render(x)
        if np.max(np.abs((target - s)[free])) < 0.01:
            break
    apply(x)
    return x

def auto_slide_exposure(sim, params, lin, input_space, scene_referred=False, iters=4):
    """Slides have no print stage, so match brightness with the camera exposure
    instead (like bracketing a slide): fit exposure_compensation_ev on a ~320px
    copy until the scan's median luminance matches the input's."""
    import numpy as np
    import colour
    small = downscale(lin, 320)
    ref = small
    if input_space != "sRGB":
        ref = colour.RGB_to_RGB(ref, colour.RGB_COLOURSPACES[input_space], colour.RGB_COLOURSPACES["sRGB"])
    w = np.array([0.2126, 0.7152, 0.0722])
    if scene_referred:   # RAW: no display brightness to match, aim for a normal mid-grey
        target = np.log2(0.184)
    else:
        target = np.log2(max(np.median(np.clip(ref, 0, None) @ w), 1e-6))
    ev0 = params.camera.exposure_compensation_ev

    def med(ev):
        sim.soft_update(exposure_compensation_ev=ev)
        return np.log2(max(np.median(np.clip(sim.process(small), 1e-6, None) @ w), 1e-6))

    ev, m = ev0, med(ev0)
    slope = 1.0
    for _ in range(iters):
        if abs(target - m) < 0.03:
            break
        new_ev = float(np.clip(ev + (target - m) / max(slope, 0.2), ev0 - 3, ev0 + 3))
        new_m = med(new_ev)
        if abs(new_ev - ev) > 1e-3:
            slope = (new_m - m) / (new_ev - ev)
        ev, m = new_ev, new_m
    sim.soft_update(exposure_compensation_ev=ev)
    return ev - ev0


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------
def encode_srgb(lin):
    import numpy as np
    import colour
    from spektrafilm.utils.chunks import map_image_blocks
    def encode(block):
        block = np.nan_to_num(block, nan=0.0)
        np.clip(block, 0.0, 1.0, out=block)
        result = colour.models.eotf_inverse_sRGB(block)
        np.clip(result, 0.0, 1.0, out=result)
        return result
    return map_image_blocks(lin, encode)


def save_outputs(enc, out_path: Path, quality: int, tiff: bool):
    import numpy as np
    from PIL import Image, ImageCms
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    from spektrafilm.utils.chunks import map_image_blocks
    img8 = Image.fromarray(map_image_blocks(enc, lambda block: (block * 255.0 + 0.5).astype(np.uint8)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img8.save(out_path, quality=quality, subsampling=0, optimize=True, icc_profile=icc)
    img8.close()
    written = [out_path]
    if tiff:
        import tifffile
        tpath = out_path.with_suffix(".tif")
        tifffile.imwrite(str(tpath), map_image_blocks(enc, lambda block: (block * 65535.0 + 0.5).astype(np.uint16)),
                         photometric="rgb", compression="zlib", iccprofile=icc)
        written.append(tpath)
    return written


def list_stocks():
    from spektrafilm.model.stocks import FilmStocks, PrintPapers
    print("Film stocks (--film):")
    for s in FilmStocks:
        kind = "slide/positive" if s.value in {"fujifilm_velvia_100", "fujifilm_provia_100f",
                                               "kodak_ektachrome_100", "kodak_kodachrome_64"} else "negative"
        print(f"  {s.value:28s} {kind}")
    print("\nPrint papers (--paper):  [default: %s]" % DEFAULT_PAPER)
    for s in PrintPapers:
        note = {"kodak_2383": "cinema print film", "kodak_2393": "cinema print film",
                "kodak_ultra_endura": "flagged 'problematic' upstream"}.get(s.value, "")
        print(f"  {s.value:32s} {note}")
    print("\nPresets (--preset):")
    for k, v in PRESETS.items():
        print(f"  {k:13s} film={v['film']}, paper={v['paper'] or '(slide: direct scan)'}\n                {v['desc']}")
    print("\nNo black & white stock exists in spektrafilm yet (color only).")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="film.py",
        description="Spectrafilm for Agents: headless spektrafilm CLI (negative -> print -> scan).",
        epilog="Film modeling powered by spektrafilm (Andrea Volpato, GPL-3.0). Not an official upstream release.")
    ap.add_argument("input", nargs="?", help="input image (JPEG/PNG/TIFF/HEIC or RAW: DNG/CR2/CR3/NEF/ARW/RAF/...)")
    ap.add_argument("-o", "--output", help="output JPEG path (default: <input>_<preset|film>.jpg)")
    ap.add_argument("-p", "--preset", choices=sorted(PRESETS), help="named look (sets film+paper)")
    ap.add_argument("--film", help="film stock (default kodak_portra_400)")
    ap.add_argument("--paper", help=f"print paper (default {DEFAULT_PAPER}; ignored for slide films)")
    ap.add_argument("--grain", default="on", help="on | off | strength multiplier (e.g. 0.5, 1.5). default on")
    ap.add_argument("--halation", default="on", help="on | off | amount multiplier. default on")
    ap.add_argument("--halation-boost", type=float, default=None,
                    help="EV of highlight reconstruction before halation (makes lights glow; 0-3)")
    ap.add_argument("--format", choices=sorted(FORMAT_MM), default="35mm",
                    help="film frame size; bigger = finer grain/halation relative to the image. default 35mm")
    ap.add_argument("--max-size", type=int, default=2400,
                    help="downscale long edge to this many px before simulation (0 = no limit). default 2400")
    ap.add_argument("--ev", type=float, default=0.0, help="camera exposure compensation in stops (default 0)")
    ap.add_argument("--no-auto-exposure", action="store_true", help="disable auto exposure of the negative")
    ap.add_argument("--metering", default="center_weighted",
                    choices=["center_weighted", "average", "median", "partial", "matrix", "multi_zone", "highlight_weighted"],
                    help="auto-exposure metering (default center_weighted)")
    ap.add_argument("--print-exposure", type=float, default=1.0, help="print exposure multiplier (default 1.0)")
    ap.add_argument("--y-shift", type=float, default=0.0, help="enlarger yellow filter shift (+ = bluer→warmer fix)")
    ap.add_argument("--m-shift", type=float, default=0.0, help="enlarger magenta filter shift")
    ap.add_argument("--balance", default="auto",
                    help="auto print balance: auto (=1.0, keep the photo's white balance) | off (engine's "
                         "fixed neutral filters, more film colour cast) | 0..1 partial. default auto")
    ap.add_argument("--no-auto-print-exposure", action="store_true",
                    help="keep the engine's fixed print exposure instead of matching the photo's brightness "
                         "(for slides: skip the brightness-matching exposure fit)")
    ap.add_argument("--scan-negative", action="store_true", help="output a scan of the negative itself (orange mask)")
    ap.add_argument("--raw-wb", default="as_shot", choices=["as_shot", "daylight", "tungsten"],
                    help="white balance for RAW files (default as_shot)")
    ap.add_argument("--tiff", action="store_true", help="also write a 16-bit sRGB TIFF next to the JPEG")
    ap.add_argument("--quality", type=int, default=95, help="JPEG quality 1-100 (default 95). Does not cap file bytes.")
    ap.add_argument("--no-sharpen", action="store_true",
                    help="disable the scanner unsharp mask (schema default is sigma 0.7, amount 0.7)")
    ap.add_argument("--input-space", default=None,
                    help="colour-science RGB space for rendered JPEG/TIFF/HEIF "
                         "(overrides ICC; TIFF ImageDescription is used when no ICC is embedded)")
    ap.add_argument("--accurate", action="store_true",
                    help="full per-pixel spectral enlarger/scanner using the fused CPU kernel (all wavelengths)")
    ap.add_argument("--grain-backend", choices=['parallel', 'reference'], default='parallel',
                    help="parallel exact Poisson/binomial sampling (default), or original SciPy sampling")
    ap.add_argument("--color-backend", choices=['compiled', 'reference'], default='compiled',
                    help="compiled float64 CAM16 (default), or the chunked colour-science implementation")
    ap.add_argument("--threads", type=int, default=None,
                    help="Numba CPU worker count (default: NUMBA_NUM_THREADS, otherwise up to 12)")
    ap.add_argument("--chunk-pixels", type=int, default=262144,
                    help="target pixels per block for pointwise color operations; smaller uses less scratch RAM")
    ap.add_argument("--raw-half-size", action='store_true',
                    help="opt in to half-resolution RAW demosaicing for previews; changes input detail")
    ap.add_argument("--seed", type=int, default=None, help="random seed for grain (reproducible output)")
    ap.add_argument("--timings", action="store_true", help="print per-stage engine timings")
    ap.add_argument("--list", action="store_true", help="list film stocks, papers and presets, then exit")
    args = ap.parse_args(argv)
    if args.max_size < 0 or args.chunk_pixels < 1:
        ap.error('--max-size must be >= 0 and --chunk-pixels must be > 0')
    if not 1 <= args.quality <= 100:
        ap.error('--quality must be between 1 and 100')
    if args.seed is not None and not 0 <= args.seed < 2**32:
        ap.error('--seed must be in 0..4294967295')
    if args.threads is not None and args.threads < 1:
        ap.error('--threads must be positive')
    os.environ['FILMSIM_CHUNK_PIXELS'] = str(args.chunk_pixels)
    os.environ['FILMSIM_COLOR_BACKEND'] = args.color_backend
    if 'numba' in sys.modules:
        import numba
        if args.threads is not None:
            try:
                numba.set_num_threads(args.threads)
            except ValueError as exc:
                ap.error(str(exc))
    elif args.threads is not None:
        os.environ['NUMBA_NUM_THREADS'] = str(args.threads)
    else:
        os.environ.setdefault('NUMBA_NUM_THREADS', str(min(12, os.cpu_count() or 1)))
    cache = Path(__file__).resolve().parent / '.cache'
    os.environ.setdefault('MPLCONFIGDIR', str(cache / 'matplotlib'))
    os.environ.setdefault('NUMBA_CACHE_DIR', str(Path(__file__).resolve().parent / '.numba_cache'))

    if args.list:
        list_stocks()
        return 0
    if not args.input:
        ap.error("INPUT is required (or use --list)")

    in_path = Path(args.input)
    if not in_path.exists():
        die(f"input not found: {in_path}")

    # resolve preset / film / paper
    args._preset_boost = None
    tag = None
    if args.preset:
        pr = PRESETS[args.preset]
        args.film = args.film or pr["film"]
        if args.paper is None:
            args.paper = pr["paper"]
        args._preset_boost = pr.get("halation_boost_ev")
        tag = args.preset
    args.film = args.film or "kodak_portra_400"
    from spektrafilm.model.stocks import FilmStocks, PrintPapers
    films = {s.value for s in FilmStocks}
    papers = {s.value for s in PrintPapers}
    if args.film not in films:
        die(f"unknown film '{args.film}'. Use --list.")
    if args.paper is not None and args.paper not in papers:
        die(f"unknown paper '{args.paper}'. Use --list.")
    tag = tag or args.film

    out_path = Path(args.output) if args.output else in_path.with_name(f"{in_path.stem}_{tag}.jpg")
    if out_path.suffix.lower() not in (".jpg", ".jpeg"):
        out_path = out_path.with_suffix(".jpg")

    if args.seed is not None:
        import numpy as np
        np.random.seed(args.seed)

    if args.input_space:
        import colour
        if args.input_space not in colour.RGB_COLOURSPACES:
            die(f"unknown --input-space '{args.input_space}'.")
    t0 = time.perf_counter()
    lin, space, kind = load_image(in_path, args.raw_wb, args.raw_half_size, args.input_space)
    h0, w0 = lin.shape[:2]
    lin = downscale(lin, args.max_size)
    h, w = lin.shape[:2]
    t_load = time.perf_counter() - t0

    try:
        from spektrafilm import Simulator
        params, paper, slide = build_params(args, space)
    except FileNotFoundError as exc:
        die(str(exc))
    t1 = time.perf_counter()
    try:
        sim = Simulator(params)
        bal_note = "off"
        if slide and not args.no_auto_print_exposure and not args.no_auto_exposure:
            dev = auto_slide_exposure(sim, params, lin, space, scene_referred=(kind == "raw"))
            bal_note = f"slide: no enlarger; brightness matched with camera exposure {dev:+.2f} EV"
        if (args.balance != "off" or not args.no_auto_print_exposure) and not args.scan_negative:
            strength = {"auto": 1.0, "off": 0.0}.get(args.balance)
            strength = float(args.balance) if strength is None else strength
            cmy = sim._pipeline.process(lin, collect="cmy_film")      # film stage (exposure, grain, halation)
            film_timings = dict(sim.get_timings())
            if not slide and (strength > 0 or not args.no_auto_print_exposure):
                x = auto_print_balance(sim, params, lin, space, cmy, strength,
                                       match_density=not args.no_auto_print_exposure,
                                       scene_referred=(kind == "raw"))
                bal_note = (f"Y{x[0]:+.1f} M{x[1]:+.1f} CC (color strength {strength:g}), "
                            f"print exposure {2 ** x[2]:.2f}x")
            out = sim._pipeline.process(cmy, inject="cmy_film")        # print + scan
            del cmy
            if args.timings:
                for k, v in film_timings.items():
                    print(f"  {k:44s} {v:7.2f} s")
                sim.print_timings()
        else:
            out = sim.process(lin)
            if args.timings:
                sim.print_timings()
    except FileNotFoundError as exc:
        die(str(exc))
    t_sim = time.perf_counter() - t1

    del lin
    enc = encode_srgb(out)
    del out
    written = save_outputs(enc, out_path, args.quality, args.tiff)
    total = time.perf_counter() - t0

    print(f"[filmbot] {in_path.name} ({w0}x{h0} {kind}, {space}) -> {w}x{h}")
    if kind == "libraw":
        print("[filmbot] input path: LibRaw/rawpy demosaic to linear ProPhoto RGB. "
              "Scene-linear DNG stage 3 is the separate adapters/dng_linear.py step.")
    elif in_path.suffix.lower() in HEIC_EXT:
        print("[filmbot] input path: display-referred HEIF/AVIF, inverse-encoded before the film model.")
    else:
        print(f"[filmbot] input path: display-referred file, decoded as {space}.")
    print(f"[filmbot] film={args.film} {'(slide, direct scan)' if slide else 'paper=' + paper} "
          f"format={args.format} grain={args.grain} halation={args.halation}")
    print(f"[filmbot] auto print balance: {bal_note}")
    print(f"[filmbot] load {t_load:.1f}s | simulate {t_sim:.1f}s | total {total:.1f}s")
    if args.timings:
        import numba
        try:
            import resource
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_note = f'peak RSS {rss / (1024**2 if sys.platform == "darwin" else 1024):.0f} MiB | '
        except ImportError:
            memory_note = ''
        print(f'[filmbot] {memory_note}workers {numba.get_num_threads()} | grain {args.grain_backend} | color {args.color_backend}')
    for p_ in written:
        nbytes = p_.stat().st_size
        extra = ""
        if nbytes > 25 * 1024 * 1024:
            extra = "; larger than 25 MiB. This CLI does not enforce a byte cap; lower --max-size or --quality"
        print(f"[filmbot] wrote {p_} ({nbytes} bytes{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
