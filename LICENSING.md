# Licenses

This repository is a fork-style packaging of public spektrafilm 0.3.4 plus a headless CLI. It is not published by Andrea Volpato and is not an official spektrafilm release. Factual credit is required; the spektrafilm name and the author's name are not a trademark grant.

Components keep their own licenses. The GPL-3.0 text at the repository root covers the program code. It does not relicense the data files listed below.

| Path | What it is | License | Where the notice lives |
|---|---|---|---|
| `film.py`, `run.sh`, `adapters/*.py`, `benchmarks/*.py`, `src/src/spektrafilm/**/*.py` | Program code, including local CPU/memory changes and this CLI | GPL-3.0-only | `LICENSE`, `src/LICENSE`. Upstream states GPLv3: <https://github.com/andreavolpato/spektrafilm> |
| `src/src/spektrafilm/data/profiles/` | Film and paper JSON profiles | CC BY-SA 4.0 | `src/SPEKTRAFILM_LICENSE.txt` (same text as upstream). Also copied under `data/license/` |
| Profile derivatives | The author's preamble covers direct derivatives of those profiles (grade LUTs and the same content in another format) | CC BY-SA 4.0, plus non-binding requests in the preamble | Same file. The preamble says the "no resale" and training requests are not extra legal conditions |
| `src/src/spektrafilm/utils/cam16_compiled.py` | CAM16 / CIECAM02 equations adapted from Colour | BSD-3-Clause | `src/NOTICE` and the file header. Colour: <https://github.com/colour-science/colour> |
| `src/src/spektrafilm/data/icc/ellelstone/` | Elle Stone ICC profiles used by the engine's image writer | CC BY-SA 3.0 Unported | `ellelstone/LICENSE`, and a copyright string inside each `.icc`. <https://github.com/ellelstone/elles_icc_profiles> |
| `src/src/spektrafilm/data/icc/saucecontrol/` | Compact ICC profiles (Display P3, DCI-P3, and the rest of that set) | CC0 1.0 | `saucecontrol/LICENSE`. <https://github.com/saucecontrol/Compact-ICC-Profiles>. Upstream spektrafilm's ICC readme called this MIT; the profile author's repository is CC0 |
| `src/src/spektrafilm/data/luts/spectral_upsampling/hanatos_irradiance_xy_coeffs_250304.lut` and `irradiance_xy_tc.npy` | Coefficient tables for the default `hanatos2025` spectral upsampling path | See residual note | In-source credit in `utils/spectral_upsampling.py`: "Thanks to hanatos for providing luts and sample code" |
| `src/src/spektrafilm/data/filters/` | Dichroic, heat-absorbing, and lens-transmission curves the enlarger model loads | See residual note | `info.txt` files name the public pages the curves were taken from |
| Adobe DNG SDK / `dng_validate` | Not included | Adobe DNG SDK License Agreement in the SDK the user downloads | `adapters/DNG.md` |

`src/CITATION.cff` is upstream citation metadata. It still says version 0.3.2, license `GPL-3.0-or-later`, and `doi: "xxxxx"`. The runtime version in `src/pyproject.toml` is 0.3.4. Do not cite the placeholder DOI. The source files in this tree do not add an "or any later version" grant beyond the GPL-3.0 text.

## Residual license notes

The Hanatos coefficient LUT is required by the default spectral-upsampling path. It is not a film-profile derivative under `SPEKTRAFILM_LICENSE.txt`, which applies to profiles and direct encodings of those profiles. Upstream spektrafilm distributes the same LUT inside the public GPL tree, and the Python comment records that hanatos supplied the tables. No separate license file for that LUT was in this package, and a search for the filename did not find a standalone grant. It is published here because the engine does not run its default path without it, and because upstream already publishes it.

Filter CSVs are likewise engine data from the upstream tree. The `info.txt` files point at Edmund Optics, Schott/Newport, and a Lensrentals spectrometry article. Those pages were not re-licensed in this repository. The curves stay because the enlarger model loads them. If you need a grant beyond upstream's public distribution, treat that as unresolved and do not assume the manufacturer assigned copyright to this project.

Finished photographs you make with the tool are yours. The CC BY-SA 4.0 preamble says the same thing for the profiles: share-alike applies to the profile and LUT files, not to a graded picture.

## Not included

- SpektraLab / `spektrafilm_gui` / `spektrafilm_lut_creator`
- Adobe `dng_validate` and the DNG SDK
- Eastman Kodak's ProPhoto RGB ICC (`Copyright (c) Eastman Kodak Company, 1999, all rights reserved`). An earlier adapter build embedded that file. It is not in this repository. Stage-3 TIFFs are tagged with the ImageDescription `ProPhoto RGB` instead
