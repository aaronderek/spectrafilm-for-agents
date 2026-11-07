# Adapters

Optional helpers. They do not change the film engine. None of them ship an Adobe binary.

## Stage-3 DNG (`dng_linear.py`)

For a DNG where you want Adobe's **stage-3** linear dump (`dng_validate -3`), converted with `ColorMatrix2` into a ProPhoto-encoded TIFF:

```bash
export DNG_VALIDATE=/path/to/your/dng_validate
python adapters/dng_linear.py input.dng stage3.tif
./run.sh stage3.tif -p portra400 -o out.jpg --input-space "ProPhoto RGB" \
  --accurate --no-sharpen --halation 3 --halation-boost 2.5 --quality 92
```

`EV` and `SAT` are optional positional arguments after the output path (default `0` and `1`). The TIFF has no embedded ICC profile. Its ImageDescription is `ProPhoto RGB`, which `film.py` uses when no ICC is present. `--input-space` makes that explicit.

Download and license: [`DNG.md`](DNG.md). This path is not universal DNG support.

## SDK final render (`indigo_dng.py`)

```bash
export DNG_VALIDATE=/path/to/your/dng_validate
python adapters/indigo_dng.py input.dng rendered.tif --mode sdr
```

This calls `dng_validate -tif` (Adobe's rendered output, including profile tables the SDK applies). It is a different file from stage 3. The TIFF is ProPhoto-encoded and tagged `ProPhoto RGB` in ImageDescription.

## Other helpers

- `dehaze_rows.py` — optional LibRaw preprocess for a linear RAW, then a row-wise dehaze. Not the default, and not stage 3. Positional arguments are exposure, warmth, and the dehaze controls the script expects.
- `splittone_grade.py` — optional sRGB split-tone applied **after** the film JPEG. Not part of the spectral model.

```bash
python adapters/splittone_grade.py film.jpg graded.jpg
```
