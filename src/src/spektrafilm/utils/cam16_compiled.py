"""Fused float64 CAM16-UCS gamut compression with the original Cmax table.

Scalar adaptation of Colour's CAM16/CIECAM02 and CAM02-UCS equations.
Copyright 2013 Colour Developers; BSD-3-Clause, see NOTICE.
No fastmath, alternative colour model, or extra lookup approximation is used.
"""
from functools import lru_cache
import colour
import numpy as np
from numba import njit, prange


@njit(inline='always')
def _spow(x, p):
    return np.sign(x) * abs(x) ** p


@njit(inline='always')
def _sdiv(x, y):
    value = x / y if y != 0 else 0.0
    return value if np.isfinite(value) else 0.0


@njit(inline='always')
def _dot(m, row, a, b, c):
    return m[row, 0] * a + m[row, 1] * b + m[row, 2] * c


@njit(inline='always')
def _response(x, fl):
    v = (fl * abs(x) / 100.0) ** 0.42
    return 400.0 * np.sign(x) * v / (27.13 + v) + 0.1


@njit(inline='always', error_model='numpy')
def _inverse_response(x, fl):
    v = abs(x - 0.1)
    return np.sign(x - 0.1) * 100.0 / fl * _spow(27.13 * v / (400.0 - v), 1.0 / 0.42)


@njit(inline='always')
def _knee(x, params):
    threshold, limit, power = params
    if x <= threshold:
        return x
    scale = limit - threshold
    value = (x - threshold) / scale
    return threshold + scale * value / (1.0 + value ** power) ** (1.0 / power)


@njit(inline='always')
def _lookup(lightness, hue, lgrid, hgrid, table):
    lightness = min(max(lightness, lgrid[0]), lgrid[-1])
    hi = (hue - hgrid[0]) / (hgrid[1] - hgrid[0])
    h0 = int(np.floor(hi)) % len(hgrid)
    h1 = (h0 + 1) % len(hgrid)
    hf = hi - np.floor(hi)
    li = (lightness - lgrid[0]) / (lgrid[-1] - lgrid[0]) * (len(lgrid) - 1)
    l0 = min(max(int(np.floor(li)), 0), len(lgrid) - 2)
    lf = li - l0
    return (table[l0, h0] * (1 - lf) * (1 - hf)
            + table[l0, h1] * (1 - lf) * hf
            + table[l0 + 1, h0] * lf * (1 - hf)
            + table[l0 + 1, h1] * lf * hf)


@njit(parallel=True, cache=True, error_model='numpy')
def _compress(image, rgb_xyz, xyz_rgb, m16, inv16, adaptation, constants,
              lgrid, hgrid, table, knee, lightness_knee, compress_lightness):
    fl, nbb, z, aw, n, white_jp = constants
    chroma_factor = (1.64 - 0.29 ** n) ** 0.73
    fl_quarter = fl ** 0.25
    out = np.empty(image.shape, dtype=np.float64)
    for row in prange(image.shape[0]):
        for col in range(image.shape[1]):
            r, g, b = image[row, col, 0], image[row, col, 1], image[row, col, 2]
            x = _dot(rgb_xyz, 0, r, g, b) * 100.0
            y = _dot(rgb_xyz, 1, r, g, b) * 100.0
            zz = _dot(rgb_xyz, 2, r, g, b) * 100.0
            ra = _response(adaptation[0] * _dot(m16, 0, x, y, zz), fl)
            ga = _response(adaptation[1] * _dot(m16, 1, x, y, zz), fl)
            ba = _response(adaptation[2] * _dot(m16, 2, x, y, zz), fl)
            a = ra - 12.0 * ga / 11.0 + ba / 11.0
            b = (ra + ga - 2.0 * ba) / 9.0
            hue = np.radians(np.degrees(np.arctan2(b, a)) % 360.0)
            et = (np.cos(hue + 2.0) + 3.8) / 4.0
            achromatic = (2.0 * ra + ga + ba / 20.0 - 0.305) * nbb
            j = 100.0 * _spow(_sdiv(achromatic, aw), 0.69 * z)
            t = 50000.0 / 13.0 * nbb * _sdiv(et * np.sqrt(a*a + b*b), ra + ga + 21.0 * ba / 20.0)
            chroma = _spow(t, 0.9) * _spow(j / 100.0, 0.5) * chroma_factor
            mp = np.log1p(0.0228 * chroma * fl_quarter) / 0.0228
            jp = 1.7 * j / (1.0 + 0.007 * j)
            ap, bp = mp * np.cos(hue), mp * np.sin(hue)
            cp, hp = np.hypot(ap, bp), np.arctan2(bp, ap)
            if compress_lightness:
                jp = _knee(jp / white_jp, lightness_knee) * white_jp
            if not np.isfinite(jp):
                out[row, col, :] = np.nan
                continue
            # Colour's inverse initializes opponent a/b to zero when hue is
            # NaN (both branch masks are false). Preserve that achromatic
            # result for out-of-domain negative RGB, rather than spreading NaN.
            if not (np.isfinite(cp) and np.isfinite(hp)):
                cp, hp = 0.0, 0.0
            maximum = max(_lookup(jp, hp, lgrid, hgrid, table), 1e-9)
            cp_new = _knee(cp / maximum, knee) * maximum
            ap, bp = cp_new * np.cos(hp), cp_new * np.sin(hp)
            mp = np.hypot(ap, bp)
            hue = np.radians(np.degrees(np.arctan2(bp, ap)) % 360.0)
            j = -jp / (0.007 * jp - 1.0 - 100.0 * 0.007)
            colourfulness = np.expm1(mp / (1.0 / 0.0228)) / 0.0228
            chroma = colourfulness / fl_quarter
            t = _spow(chroma / (np.sqrt(max(j, 2.220446049250313e-16) / 100.0) * chroma_factor), 1.0 / 0.9)
            et = (np.cos(hue + 2.0) + 3.8) / 4.0
            achromatic = aw * _spow(j / 100.0, 1.0 / (0.69 * z))
            p1 = _sdiv(50000.0 / 13.0 * nbb * et, t)
            p2, p3 = achromatic / nbb + 0.305, 21.0 / 20.0
            sn, co = np.sin(hue), np.cos(hue)
            numerator = p2 * (2.0 + p3) * (460.0 / 1403.0)
            if t == 0:
                a, b = 0.0, 0.0
            elif abs(sn) >= abs(co):
                b = numerator / (p1/sn + (2.0+p3)*(220.0/1403.0)*co/sn - 27.0/1403.0 + p3*(6300.0/1403.0))
                a = b * co / sn
            else:
                a = numerator / (p1/co + (2.0+p3)*(220.0/1403.0) - (27.0/1403.0 - p3*(6300.0/1403.0))*sn/co)
                b = a * sn / co
            ra = (460.0*p2 + 451.0*a + 288.0*b) / 1403.0
            ga = (460.0*p2 - 891.0*a - 261.0*b) / 1403.0
            ba = (460.0*p2 - 220.0*a - 6300.0*b) / 1403.0
            r = _inverse_response(ra, fl) / adaptation[0]
            g = _inverse_response(ga, fl) / adaptation[1]
            b = _inverse_response(ba, fl) / adaptation[2]
            x = _dot(inv16, 0, r, g, b) / 100.0
            y = _dot(inv16, 1, r, g, b) / 100.0
            zz = _dot(inv16, 2, r, g, b) / 100.0
            for channel in range(3):
                out[row, col, channel] = _dot(xyz_rgb, channel, x, y, zz)
    return out


@lru_cache(maxsize=16)
def _parameters(output_color_space):
    from colour.appearance.cam16 import MATRIX_16, MATRIX_INVERSE_16
    from colour.appearance.ciecam02 import (
        viewing_conditions_dependent_parameters, degree_of_adaptation,
        post_adaptation_non_linear_response_compression_forward, achromatic_response_forward,
    )
    cs = colour.RGB_COLOURSPACES[output_color_space]
    white = np.asarray(colour.xy_to_XYZ(cs.whitepoint)) * 100.0
    rgb_white = MATRIX_16 @ white
    d = np.clip(degree_of_adaptation(1.0, 64.0), 0.0, 1.0)
    n, fl, nbb, _, z = viewing_conditions_dependent_parameters(20.0, white[1], 64.0)
    adaptation = d * white[1] / rgb_white + 1.0 - d
    aw = achromatic_response_forward(
        post_adaptation_non_linear_response_compression_forward(adaptation * rgb_white, fl), nbb)
    white_jp = colour.XYZ_to_CAM16UCS(white / 100.0, XYZ_w=white / 100.0, L_A=64.0, Y_b=20.0)[0]
    return (np.asarray(cs.matrix_RGB_to_XYZ), np.asarray(cs.matrix_XYZ_to_RGB),
            MATRIX_16, MATRIX_INVERSE_16, adaptation,
            np.array([fl, nbb, z, aw, n, white_jp]))


def compress_cam16(rgb, spec, output_color_space, cmax):
    lightness = spec.lightness_compression
    return _compress(np.asarray(rgb), *_parameters(output_color_space), *cmax,
                     np.asarray(spec.knee), np.asarray(lightness if lightness is not None else (0.0, 1.0, 1.0)),
                     lightness is not None)
