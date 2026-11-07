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
| Spectral coefficient LUT and `irradiance_xy_tc.npy` | Default Hanatos 2025 upsampling tables | **Not shipped.** No redistribution grant was established | `utils/spectral_upsampling.py` still has the upstream thanks line. Evidence is below |
| Manufacturer filter CSVs | Thorlabs, Edmund, Durst, Schott KG, Canon 24mm transmission | **Not shipped.** No redistribution grant was established | Provenance URLs remain in `data/filters/**/info.txt` |
| `neutral_print_filters.json` | Enlarger neutral-filter calibration numbers | Treated as runtime data authored with this program | No third-party notice in the file. It is not a manufacturer curve |
| Adobe DNG SDK / `dng_validate` | Not included | Adobe DNG SDK License Agreement in the SDK the user downloads | `adapters/DNG.md` |

`src/CITATION.cff` in this tree names upstream spektrafilm 0.3.4, license `GPL-3.0-only`, and no DOI. Upstream's file on main is different; see below. Do not invent a DOI.

## Code license: GPL-3.0-only

Checked against upstream on 2026-11-07:

- [`pyproject.toml`](https://github.com/andreavolpato/spektrafilm/blob/main/pyproject.toml) sets `license = { text = "GPLv3" }`. The runtime version there is `0.3.4`.
- [`README.md`](https://github.com/andreavolpato/spektrafilm/blob/main/README.md) says "The project is GPLv3 licensed" and does not say "or any later version".
- [`LICENSE`](https://github.com/andreavolpato/spektrafilm/blob/main/LICENSE) is the GPL-3 text. Section 14 gives later versions only when the program says a version "or any later version". Specifying GPLv3 without that phrase is a GPL-3.0-only grant. The same section says that if the program names no version at all, any version may be chosen. This program names GPLv3.
- [`src/spektrafilm/utils/spectral_upsampling.py`](https://github.com/andreavolpato/spektrafilm/blob/main/src/spektrafilm/utils/spectral_upsampling.py) has no copyright header and no "or later" line. The copy in this tree matches that.
- [`CITATION.cff`](https://github.com/andreavolpato/spektrafilm/blob/main/CITATION.cff) says `license: GPL-3.0-or-later`, `version: 0.3.2`, and `doi: "xxxxx"`. That DOI is a placeholder. The version does not match `pyproject.toml`. This file is not treated as the license grant. The copy in this repository drops the placeholder DOI, sets the version to `0.3.4`, and sets the identifier to `GPL-3.0-only`.

## Spectral table: not cleared, not shipped

The default path is `rgb_to_raw_method = "hanatos2025"`. It needs `hanatos_irradiance_xy_coeffs_250304.lut` or the derived `irradiance_xy_tc.npy`.

What was checked:

- The LUT file that was in the candidate archive starts with vkdt's header from [`src/core/lut.h`](https://github.com/hanatos/vkdt/blob/master/src/core/lut.h): magic `1234`, version 2, 4 float channels, 512×512. That shows a format kinship. It does not show that these bytes are a file vkdt licenses for redistribution.
- [`src/tools/spec/mkspectra.c`](https://github.com/hanatos/vkdt/blob/master/src/tools/spec/mkspectra.c) can build an xy→coefficient table. [`readme.md`](https://github.com/hanatos/vkdt/blob/master/readme.md) puts vkdt code under BSD-2-Clause unless a file says otherwise ([`LICENCE.bsd2`](https://github.com/hanatos/vkdt/blob/master/LICENCE.bsd2)). `mkspectra.c` and `lut.h` have no separate GPL marker. BSD-2 covers that source. It was not found to cover this named binary.
- [`filmsim/readme.md`](https://github.com/hanatos/vkdt/blob/master/src/pipe/modules/filmsim/readme.md) says `data/spectra-em.lut` ships with a vkdt installation. That filename is not in the public [`bin/data`](https://github.com/hanatos/vkdt/tree/master/bin/data) listing retrieved on 2026-11-07. The bytes were not compared.
- spektrafilm's own comment is "Thanks to hanatos for providing luts and sample code to develop this." Thanks is not a license.
- [`SPEKTRAFILM_LICENSE.txt`](https://github.com/andreavolpato/spektrafilm/blob/main/SPEKTRAFILM_LICENSE.txt) licenses profiles and direct derivatives of those profiles. This coefficient table is not one of those profiles. The upstream README sentence "JSON profiles and LUTs are CC BY-SA 4.0" is read together with that file, not as a grant over this table.
- A third-party note in [spektrafilm-rs](https://github.com/turbasvin/spektrafilm-rs) says hanatos provided the LUT files. That is provenance, not a grant from hanatos to this repository.
- The table being present in the public spektrafilm repository is not, by itself, a redistribution license.

Set `SPEKTRAFILM_SPECTRAL_LUT_DIR` if you already have a copy you are allowed to use. This repository does not ship the file and does not download it.

## Manufacturer curves: not cleared, not shipped

Default enlarger illuminant is `TH-KG3` (`EnlargerParams.illuminant`). That path reads `heat_absorbing/schott/KG3.csv`. The default dichroic is the analytic `custom` filter, so Thorlabs, Edmund, and Durst CSVs are not required for that path. `TH-KG3-L` also reads the Canon transmission CSV. KG1 and KG5 are not the default illuminant.

What was checked:

- No license file under upstream [`data/filters`](https://github.com/andreavolpato/spektrafilm/tree/main/src/spektrafilm/data/filters).
- Schott `info.txt` names <https://www.newport.com/f/heat-absorbing-glass-filters>. Edmund `info.txt` names <https://www.edmundoptics.com/f/additive-and-subtractive-dichroic-color-filters/11985/>. The Canon note names <https://www.lensrentals.com/blog/2018/03/a-geek-of-many-colors-adventures-in-spectrometry/>.
- The CSVs have no copyright header. Their irregular wavelength samples look like digitized plots. No open-license text was in those files.
- Thorlabs dichroic CSVs had no `info.txt` and no license notice.

Appearance in the public spektrafilm tree is not a grant from Schott, Newport, Edmund Optics, Thorlabs, Canon, or Lensrentals.

Set `SPEKTRAFILM_FILTER_DIR` to a directory you are allowed to read. Negative prints fail clearly without `heat_absorbing/schott/KG3.csv`. This repository does not download the curve.

Finished photographs you make with the tool are yours. The CC BY-SA 4.0 preamble says the same thing for the profiles: share-alike applies to the profile and LUT files, not to a graded picture.

## Not included

- SpektraLab / `spektrafilm_gui` / `spektrafilm_lut_creator`
- Adobe `dng_validate` and the DNG SDK
- Eastman Kodak's ProPhoto RGB ICC (`Copyright (c) Eastman Kodak Company, 1999, all rights reserved`). An earlier adapter build embedded that file. It is not in this repository. Stage-3 TIFFs are tagged with the ImageDescription `ProPhoto RGB` instead
