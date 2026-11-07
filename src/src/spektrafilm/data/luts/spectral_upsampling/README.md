# Spectral upsampling tables

`hanatos_irradiance_xy_coeffs_250304.lut` and `irradiance_xy_tc.npy` are not included. See the repository `LICENSING.md`.

Set `SPEKTRAFILM_SPECTRAL_LUT_DIR` to a directory that contains one or both of those filenames. If only the `.lut` is present, the runtime builds the spectra table in memory. This process does not download either file.

Every default preset uses the Hanatos 2025 upsampling path, so a render stops with `FileNotFoundError` until the directory is set.
