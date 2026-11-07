"""Exact-distribution grain samplers, with reproducible row-local RNG streams."""
import numpy as np
from numba import njit, prange


@njit(inline='always')
def _row_seed(seed, row):
    # Integer avalanche; independent of scheduling and the number of workers.
    value = (seed + row * 0x9E3779B9) & 0xFFFFFFFF
    value = ((value ^ (value >> 16)) * 0x85EBCA6B) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 0xC2B2AE35) & 0xFFFFFFFF
    return (value ^ (value >> 16)) & 0xFFFFFFFF


@njit(parallel=True, cache=True)
def particle_grain(density, density_max, particles, uniformity, seed):
    """Exact Poisson thinning: Binomial(Poisson(lambda), p) = Poisson(lambda*p).

    Only the developed particle count is consumed by the model, so this
    eliminates the latent count and binomial draw without approximating its
    distribution. The particular random realization differs from SciPy.
    """
    out = np.empty(density.shape, dtype=np.float64)
    optical_density = density_max / particles
    for row in prange(density.shape[0]):
        np.random.seed(_row_seed(seed, row))
        for col in range(density.shape[1]):
            p = min(max(density[row, col] / density_max, 1e-6), 1.0 - 1e-6)
            saturation = 1.0 - p * uniformity * (1.0 - 1e-6)
            developed = np.random.poisson(particles / saturation * p)
            out[row, col] = developed * optical_density * saturation
    return out


@njit(parallel=True, cache=True)
def _lognormal_constant(shape, mean, std, seed):
    result = np.empty(shape, dtype=np.float64)
    flat = result.reshape(shape[0], -1)
    variance = np.log(1.0 + (std * std) / (mean * mean)) if mean > 0 else 0.0
    sigma = np.sqrt(variance)
    mu = np.log(mean) - variance / 2.0 if mean > 0 else 0.0
    for row in prange(shape[0]):
        np.random.seed(_row_seed(seed, row))
        for col in range(flat.shape[1]):
            z = np.random.randn() if sigma >= 1e-6 else 0.0
            flat[row, col] = np.exp(mu + sigma * z)
    return result


def lognormal_constant(shape, mean, std, seed=None):
    if seed is None:
        seed = int(np.random.randint(0, 2**32, dtype=np.uint32))
    return _lognormal_constant(shape, float(mean), float(std), int(seed) & 0xFFFFFFFF)
