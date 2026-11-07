"""Fused full-spectrum integration: O(pixels * 3) memory, all wavelengths retained."""
import numpy as np
from numba import njit, prange


@njit(parallel=True, cache=True, error_model='numpy')
def _integrate(density, dyes, base, illuminant, response):
    h, w, _ = density.shape
    output = np.empty((h, w, 3), dtype=np.float64)
    for row in prange(h):
        for col in range(w):
            c, m, y = density[row, col, 0], density[row, col, 1], density[row, col, 2]
            r0, r1, r2 = 0.0, 0.0, 0.0
            for k in range(dyes.shape[0]):
                d = c * dyes[k, 0] + m * dyes[k, 1] + y * dyes[k, 2] + base[k]
                light = 10.0 ** (-d) * illuminant[k]
                # density_to_light's NaN handling, including NaNs in stock spectra.
                if np.isnan(light):
                    light = 0.0
                r0 += light * response[k, 0]
                r1 += light * response[k, 1]
                r2 += light * response[k, 2]
            output[row, col, 0] = r0
            output[row, col, 1] = r1
            output[row, col, 2] = r2
    return output


def integrate_density(density, channel_density, base_density, illuminant, response):
    """Equivalent to density -> spectral transmittance -> three-channel integral.

    No fastmath or wavelength subsampling. Only the small spectral tables are
    converted to contiguous float64; strided image inputs are supported.
    """
    dyes = np.ascontiguousarray(channel_density, dtype=np.float64)
    base = np.zeros(dyes.shape[0]) if base_density is None else np.asarray(base_density, dtype=np.float64)
    return _integrate(np.asarray(density), dyes, base,
                      np.asarray(illuminant, dtype=np.float64),
                      np.ascontiguousarray(response, dtype=np.float64))
