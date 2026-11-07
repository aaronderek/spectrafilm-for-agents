# Agents

Spectrafilm for Agents is a headless CLI around the `spektrafilm` 0.3.4 runtime. Use the commands below. Do not assume a GUI, a bundled `dng_validate`, or a 25 MB output cap.

## Setup

From the repository root:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e ./src
./run.sh --help
./run.sh --list
```

`./run.sh` uses `FILM_PYTHON`, then `.venv/bin/python`, then `python3`. Paths are relative to the repository. There is no hardcoded home directory.

## Preferred render

Sequential: one image per process.

```bash
./run.sh INPUT.jpg -p portra400 -o out.jpg \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 \
  --quality 92 --max-size 2400 --seed 42
```

Same flags work with `-p kodachrome` (reversal, no paper) and `-p vision3_500t` (Vision3 500T on paper 2383).

`--quality 92` and `--max-size 2400` do not guarantee a file under 25 MB. The CLI prints the byte size and, above 25 MiB, a reminder. Lower `--max-size` or `--quality` yourself. `--chunk-pixels` only bounds pointwise scratch buffers. `--max-size 0` keeps full resolution and can use several GiB.

Defaults if you omit flags: max edge 2400, JPEG quality 95, scanner unsharp 0.7/0.7, LUT enlarger/scanner (not `--accurate`).

## Which input you have

- JPEG or 8-bit TIFF/PNG: display-referred. Embedded ICC selects the decode. No ICC means sRGB.
- 16-bit TIFF: encoded in the ICC space, or in the TIFF ImageDescription when no ICC is embedded (`ProPhoto RGB` is recognized). Override with `--input-space "ProPhoto RGB"`.
- HEIF/AVIF: display-referred decode via pillow-heif. Not scene-linear.
- RAW passed straight to `./run.sh`: LibRaw demosaic to linear ProPhoto RGB. Log line says `libraw`. This path is not Adobe stage 3 and does not claim every DNG.
- DNG stage 3: install your own SDK binary (see `adapters/DNG.md`), then:

```bash
export DNG_VALIDATE=/path/to/dng_validate
python adapters/dng_linear.py input.dng stage3.tif
./run.sh stage3.tif -p portra400 -o out.jpg --input-space "ProPhoto RGB" \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 --quality 92
```

`adapters/indigo_dng.py` is the SDK final `-tif` render, not stage 3.

Output JPEG embeds an sRGB ICC profile and does not copy source EXIF.

## Do not commit

Photos, RAW files, `.venv`, `.numba_cache`, `adapters/bin/dng_validate`, or benchmark JSON. `inbox/` and `outbox/` are empty placeholders.
