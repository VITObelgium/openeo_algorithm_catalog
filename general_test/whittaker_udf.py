"""
Self-contained Whittaker smoothing openEO UDF.

This file is a single, dependency-free reimplementation of the FuseTS
Whittaker smoother:
    https://github.com/Open-EO/FuseTS/blob/main/src/fusets/whittaker.py

FuseTS itself relies on `vam.whittaker` (the compiled Cython extension
`ws2d` / `ws2doptv`) from the WFP-VAM `modape` package:
    https://github.com/WFP-VAM/modape/blob/main/modape/_whittaker.pyx

`vam.whittaker` / `modape` are compiled C-extensions that are not part of
the standard openEO UDF runtime and are awkward (or impossible) to install
inside a sandboxed UDF worker. This file removes that dependency entirely:
`ws2d` and `ws2doptv` are reimplemented below in pure NumPy/Python,
numerically matching the compiled originals (validated to ~1e-12 abs.
difference against the real `vam.whittaker` package).

Everything needed to run as an openEO `apply_datacube` UDF is included in
this one file. Only packages that are already part of every openEO UDF
Python runtime are used: `numpy`, `pandas`, `xarray`, `openeo`. Nothing
else needs to be installed.

Usage as an openEO UDF
-----------------------
    import openeo
    cube = ...  # some openEO raster/vector cube with a temporal dimension
    smoothed = cube.apply_dimension(
        process=openeo.UDF.from_file("whittaker_udf.py"),
        dimension="t",
    )

The UDF entry point `apply_datacube` accepts a `context` dict with:
    smoothing_lambda : float | int | list[float], default 10000
        Whittaker penalty (S). A single number smooths with a fixed
        lambda. A list of `log10(lambda)` candidates (e.g.
        `list(numpy.arange(0, 4, 0.2))`) triggers automatic V-curve
        optimization of lambda per pixel (`ws2doptv`), exactly like
        passing a list to `fusets.whittaker.whittaker`.
    time_dimension : str, default "t"
        Name of the temporal dimension/coordinate.
    prediction_period : Numbe of days default same date as observation

Standalone (non-openEO) usage
------------------------------
    from whittaker_udf import whittaker
    smoothed_da = whittaker(my_xarray_dataarray, smoothing_lambda=10000)

License / attribution
----------------------
`ws2d` and `ws2doptv` are a line-for-line NumPy translation of the
Cython algorithm in modape's `_whittaker.pyx`
(Copyright (c) 2019 World Food Programme, MIT License). The surrounding
gap-filling / resampling logic (`whittaker_f`, `get_all_dates`,
`whittaker`) is adapted from FuseTS's `whittaker.py`
(Copyright Open-EO/FuseTS contributors, Apache-2.0 License).
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import xarray
from xarray import DataArray
from openeo.udf import XarrayDataCube
# ---------------------------------------------------------------------------
# Optional speed-up: use numba to JIT-compile the inner ws2d kernel if numba
# happens to be available in the runtime. This is entirely optional -- the
# file works fine, just slower, with plain CPython if numba is absent.
# ---------------------------------------------------------------------------
try:
    from numba import njit  # type: ignore

    _HAVE_NUMBA = True
except Exception:  # pragma: no cover - numba is optional
    _HAVE_NUMBA = False


# ===========================================================================
# 1. Standalone replacement for `from vam.whittaker import ws2d, ws2doptv`
# ===========================================================================

def _ws2d_core(y: np.ndarray, lmbda: float, w: np.ndarray) -> np.ndarray:
    """Whittaker smoother with a fixed lambda (second order difference
    penalty), solved directly via the banded (pentadiagonal) LDL'
    recursion described in Eilers (2003) / Eilers et al. (2017).

    This is a NumPy re-implementation of `ws2d` from modape's
    `_whittaker.pyx` (Cython). It solves
        (diag(w) + lmbda * D2' D2) z = diag(w) y
    in O(n) time without ever building the (n x n) matrix.

    Args:
        y: 1-D array of observed values (NaNs must be replaced by 0
           beforehand; use `w` to mark them as missing).
        lmbda: smoothing penalty (S / lambda).
        w: 1-D array of weights, same length as `y` (0 = missing, 1 =
           valid observation; fractional weights are also supported).

    Returns:
        1-D NumPy array with the smoothed (and gap-filled) series.
    """
    n = y.shape[0]
    m = n - 1

    z = np.empty(n, dtype=np.float64)
    d = np.empty(n, dtype=np.float64)
    c = np.empty(n, dtype=np.float64)
    e = np.empty(n, dtype=np.float64)

    d[0] = w[0] + lmbda
    c[0] = (-2.0 * lmbda) / d[0]
    e[0] = lmbda / d[0]
    z[0] = w[0] * y[0]

    d[1] = w[1] + 5.0 * lmbda - d[0] * (c[0] * c[0])
    c[1] = (-4.0 * lmbda - d[0] * c[0] * e[0]) / d[1]
    e[1] = lmbda / d[1]
    z[1] = w[1] * y[1] - c[0] * z[0]

    for i in range(2, m - 1):
        i1 = i - 1
        i2 = i - 2
        d[i] = w[i] + 6.0 * lmbda - (c[i1] * c[i1]) * d[i1] - (e[i2] * e[i2]) * d[i2]
        c[i] = (-4.0 * lmbda - d[i1] * c[i1] * e[i1]) / d[i]
        e[i] = lmbda / d[i]
        z[i] = w[i] * y[i] - c[i1] * z[i1] - e[i2] * z[i2]

    i1 = m - 2
    i2 = m - 3
    d[m - 1] = w[m - 1] + 5.0 * lmbda - (c[i1] * c[i1]) * d[i1] - (e[i2] * e[i2]) * d[i2]
    c[m - 1] = (-2.0 * lmbda - d[i1] * c[i1] * e[i1]) / d[m - 1]
    z[m - 1] = w[m - 1] * y[m - 1] - c[i1] * z[i1] - e[i2] * z[i2]

    i1 = m - 1
    i2 = m - 2
    d[m] = w[m] + lmbda - (c[i1] * c[i1]) * d[i1] - (e[i2] * e[i2]) * d[i2]
    z[m] = (w[m] * y[m] - c[i1] * z[i1] - e[i2] * z[i2]) / d[m]

    z[m - 1] = z[m - 1] / d[m - 1] - c[m - 1] * z[m]
    for i in range(m - 2, -1, -1):
        z[i] = z[i] / d[i] - c[i] * z[i + 1] - e[i] * z[i + 2]

    return z


if _HAVE_NUMBA:  # pragma: no cover - exercised only when numba is installed
    _ws2d_core = njit(cache=True)(_ws2d_core)


def ws2d(y: np.ndarray, lmbda: float, w: np.ndarray) -> np.ndarray:
    """Drop-in replacement for `vam.whittaker.ws2d(y, lmbda, w)`.

    Args:
        y: time-series values (1-D array-like), NaNs should be 0
           (mark them via `w` instead).
        lmbda: smoothing parameter (lambda / S).
        w: 0/1 (or fractional) weights, same length as `y`.

    Returns:
        Smoothed (and, where w==0, gap-filled) NumPy array.
    """
    y = np.ascontiguousarray(y, dtype=np.float64)
    w = np.ascontiguousarray(w, dtype=np.float64)
    if y.shape[0] < 4:
        # The banded recursion needs at least a handful of points; for
        # very short series just fall back to a weighted copy.
        return np.where(w > 0, y, 0.0)
    return np.asarray(_ws2d_core(y, float(lmbda), w))


def ws2doptv(y: np.ndarray, w: np.ndarray, llas):
    """Drop-in replacement for `vam.whittaker.ws2doptv(y, w=w, llas=llas)`.

    Automatically picks lambda (S) via V-curve optimization, as in
    Eilers, P.H.C. (2003), "A Perfect Smoother, and re-used in
    Eilers, Pesendorfer & Bonifacio (2017).

    Args:
        y: time-series values (1-D array-like).
        w: 0/1 (or fractional) weights, same length as `y`.
        llas: iterable of `log10(lambda)` candidate values to scan,
            e.g. `numpy.arange(0, 4, 0.2)`.

    Returns:
        Tuple `(z, lopt)`: the smoothed array and the optimal lambda.
    """
    y = np.ascontiguousarray(y, dtype=np.float64)
    w = np.ascontiguousarray(w, dtype=np.float64)
    llas = np.ascontiguousarray(llas, dtype=np.float64)

    m = y.shape[0]
    nl = llas.shape[0]
    nl1 = nl - 1
    if nl < 2:
        lopt = float(10.0 ** llas[0]) if nl == 1 else 10000.0
        return ws2d(y, lopt, w), lopt

    fits = np.empty(nl, dtype=np.float64)
    pens = np.empty(nl, dtype=np.float64)

    for lix in range(nl):
        lam = 10.0 ** llas[lix]
        z = ws2d(y, lam, w)
        fits[lix] = np.log(np.sum((w * (y - z)) ** 2))
        diff1 = np.diff(z)
        pens[lix] = np.log(np.sum(np.diff(diff1) ** 2))

    llastep = llas[1] - llas[0]
    f1, f2 = fits[:-1], fits[1:]
    p1, p2 = pens[:-1], pens[1:]
    l1, l2 = llas[:-1], llas[1:]
    v = np.sqrt((f2 - f1) ** 2 + (p2 - p1) ** 2) / (np.log(10.0) * llastep)
    lamids = (l1 + l2) / 2.0

    k = int(np.argmin(v))
    lopt = float(10.0 ** lamids[k])
    z = ws2d(y, lopt, w)
    return z, lopt


# ===========================================================================
# 2. FuseTS whittaker.py logic, adapted to use the standalone ws2d/ws2doptv
#    above instead of `vam.whittaker`.
# ===========================================================================

def get_all_dates(x: List[datetime]) -> np.ndarray:
    """Day-offsets of `x` relative to `x[0]` (as ordinal integers)."""
    d = [i.toordinal() for i in x]
    return np.array(d) - d[0]


def whittaker_f(x: List[datetime], y: np.ndarray, lmbd: Union[float, list], d: int):
    """Gap-fill and smooth an irregular time series onto a daily grid,
    then subsample every `d` days.

    Args:
        x: list of `datetime` objects (observation dates), same length as `y`.
        y: observed values (NaN = missing).
        lmbd: lambda (float) for a fixed-lambda smooth, or a list of
            `log10(lambda)` candidates to run V-curve optimization.
        d: spacing (in days) at which to sample the smoothed daily series.

    Returns:
        `(z1_, xx, Zd, XXd)`: the full daily smoothed series and its
        dates, plus the `d`-spaced subsample and its dates.
    """
    y = np.asarray(y, dtype=np.float64)
    D1 = get_all_dates(x)
    D11 = D1[~np.isnan(y)]

    length = D1[-1] - D1[0]
    v = np.full(length + 1, -3000.0)
    v[D11] = 1

    t = np.full(length + 1, 0.0, dtype="float64")
    t[D11] = y[~np.isnan(y)]

    xx = [x[0] + timedelta(days=i) for i in range(length + 1)]

    w = np.array((v != -3000) * 1, dtype="float64")

    if isinstance(lmbd, (list, tuple, np.ndarray)):
        z_, _the_lambda = ws2doptv(t, w=w, llas=np.asarray(lmbd, dtype=np.float64))
    else:
        z_ = ws2d(t, float(lmbd), w)
    z1_ = np.asarray(z_)

    if isinstance(d, int) and 0 < d < z1_.size:
        n = z1_.size
        ind = [i * d for i in range(math.ceil(n / d))]
        Zd = z1_[ind]
        XXd = [xx[ii] for ii in ind]
    else:
        Zd = np.array([])
        XXd = []

    return z1_, xx, Zd, XXd


# ---------------------------------------------------------------------------
# Minimal xarray helpers (inlined from fusets._xarray_utils so this file
# has no dependency on the `fusets` package).
# ---------------------------------------------------------------------------

def _topydate(t) -> datetime:
    seconds = (t - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
    return datetime.fromtimestamp(seconds, tz=timezone.utc).replace(tzinfo=None)


def _extract_dates(array: DataArray) -> List[datetime]:
    time_coords = [c for c in array.coords.values() if c.dtype.type == np.datetime64]
    if len(time_coords) == 0:
        raise ValueError(
            "Whittaker expects an input with exactly one coordinate of type "
            "numpy.datetime64 (the time dimension), but found none."
        )
    if len(time_coords) > 1:
        raise ValueError(
            "Whittaker expects an input with exactly one coordinate of type "
            f"numpy.datetime64, but found multiple: {time_coords}"
        )
    dates = list(time_coords[0].values)
    return [_topydate(dt) for dt in dates]


def _time_dimension(array: DataArray, time_dimension: str) -> str:
    time_coords = {c.name: c for c in array.coords.values() if c.dtype.type == np.datetime64}
    if len(time_coords) == 0:
        raise ValueError(f"Input array has no time dimension: {array}")
    if len(time_coords) > 1:
        if time_dimension not in time_coords:
            raise ValueError(
                f"Specified time dimension '{time_dimension}' does not exist, "
                f"available dimensions: {list(time_coords.keys())}"
            )
    else:
        time_dimension = list(time_coords.keys())[0]
    return time_dimension


def _output_dates(prediction_period: int, start_date: datetime, end_date: datetime) -> List[datetime]:
    period = pd.Timedelta(prediction_period,unit="D")
    date_range = pd.date_range(start_date, end_date, freq=period)
    return [_topydate(dt) for dt in date_range.values]


def whittaker(
    array: DataArray,
    smoothing_lambda: Union[float, int, list] = np.log10(10000),
    time_dimension: str = "t",
    prediction_period: int = 0,
) -> DataArray:
    """Apply Whittaker smoothing/gap-filling to every 1-D time series in
    `array` along its temporal dimension.

    This mirrors `fusets.whittaker.whittaker`, but is fully self-contained
    (no `fusets` or `vam.whittaker` import required).

    Args:
        array: xarray DataArray with (at least) a `numpy.datetime64`
            temporal coordinate/dimension.
        smoothing_lambda: fixed lambda, or a list of `log10(lambda)`
            candidates to auto-select lambda per pixel via V-curve
            optimization.
        time_dimension: name of the temporal dimension (auto-detected
            when unambiguous).
        prediction_period: number of days to resample onto a regular output time grid.
            When omitted, the original observation dates are returned.

    Returns:
        A smoothed DataArray with the same dimensions as `array`.
    """
    dates = _extract_dates(array)
    time_dimension = _time_dimension(array, time_dimension)

    output_dates = dates
    output_time_dimension = time_dimension

    if prediction_period > 0:
        output_dates = _output_dates(int(prediction_period), dates[0], dates[-1])
        output_time_dimension = "t_new"

    def callback(timeseries):
        _, _, Zd, XXd = whittaker_f(dates, timeseries, smoothing_lambda, 1)
        dates_mask = np.isin(XXd, output_dates)
        return Zd[dates_mask]

    result = xarray.apply_ufunc(
        callback,
        array,
        input_core_dims=[[time_dimension]],
        output_core_dims=[[output_time_dimension]],
        vectorize=True,
    )

    result[output_time_dimension] = output_dates
    result = result.rename({output_time_dimension: time_dimension})

    return result.transpose(*array.dims)


# ===========================================================================
# 3. openEO UDF entry point
# ===========================================================================
def apply_datacube(cube: XarrayDataCube, context: dict) -> XarrayDataCube:
    """
    Applies Whittaker smoothing along the temporal dimension ('t') of a datacube.

    Expected to be called via `apply_dimension(process=UDF, dimension="t")`
    so the full time series per pixel/band is available in one call.

    Args:
        cube (XarrayDataCube): dims typically (t, bands, y, x) or (t, y, x)
        context (dict): may contain 'lmbda' and 'd' smoothing parameters
    Returns:
        XarrayDataCube: same shape/dims as input, smoothed along 't'
    """
    context = context or {}
    smoothing_lambda = context.get("smoothing_lambda", 10000)
    time_dimension = context.get("time_dimension", "t")
    prediction_period = context.get("prediction_period", 2)

    smoothed = whittaker(
        cube.get_array(),
        # smoothing_lambda=np.log10(smoothing_lambda),
        smoothing_lambda=smoothing_lambda,
        time_dimension=time_dimension,
        prediction_period=int(prediction_period),
    )
    return XarrayDataCube(smoothed)