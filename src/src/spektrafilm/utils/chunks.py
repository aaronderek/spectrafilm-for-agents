"""Bound temporary memory for pointwise operations, without tiling spatial effects."""
from __future__ import annotations

import os
import numpy as np


def chunk_pixels() -> int:
    value = int(os.environ.get('FILMSIM_CHUNK_PIXELS', '262144'))
    if value < 1:
        raise ValueError('FILMSIM_CHUNK_PIXELS must be positive')
    return value


def map_image_blocks(image, function, *, dtype=None):
    """Map an HWC image in row strips. Never divide a spatial filter here.

    The callable must be pointwise, preserve shape, and not mutate its input.
    A single unusually wide row can exceed the pixel target.
    """
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[0] * image.shape[1] <= chunk_pixels():
        result = function(image)
        return np.asarray(result, dtype=dtype) if dtype is not None else result
    rows = max(1, chunk_pixels() // image.shape[1])
    first = np.asarray(function(image[:rows]), dtype=dtype)
    result = np.empty(image.shape[:2] + first.shape[2:], dtype=first.dtype)
    result[:rows] = first
    del first
    for start in range(rows, image.shape[0], rows):
        result[start:start + rows] = function(image[start:start + rows])
    return result
