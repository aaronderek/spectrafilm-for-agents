# Filter curves

These CSVs are the copies already published in upstream spektrafilm. A separate redistribution license for the manufacturer curves was not found. They are included so the default presets run. See the repository `LICENSING.md`. This is not a statement that the curves are GPL.

`neutral_print_filters.json` is calibration data written for this runtime.

`SPEKTRAFILM_FILTER_DIR` replaces a curve when that directory contains the same relative path, for example `heat_absorbing/schott/KG3.csv`. It is not required.

Default negative prints use enlarger illuminant `TH-KG3` (Schott KG3). The default enlarger dichroic is the analytic `custom` model. `TH-KG3-L` also reads `lens_transmission/canon/canon_24_f28_is.csv`.
