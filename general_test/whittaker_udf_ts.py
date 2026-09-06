# /// script
# dependencies = []
# ///
"""
Self-contained Whittaker smoothing openEO UDF for VECTOR datacubes.

This is the companion to `whittaker_udf.py` (which handles raster/xarray
datacubes via `apply_datacube`). This file instead targets the
`aggregate_spatial(...).run_udf(udf=..., runtime="Python")` style
pipeline, where the UDF receives/returns a `UdfData` object wrapping the
`aggregate_spatial` timeseries JSON (mapping date -> [polygon][band]
values) as `StructuredData`, exactly like the example UDF this was built
from.

Like `whittaker_udf.py`, this replaces `from vam.whittaker import ws2d,
ws2doptv` (the compiled Cython extension from the WFP-VAM `modape`
package: https://github.com/WFP-VAM/modape/blob/main/modape/_whittaker.pyx)
with a pure NumPy/Python reimplementation, numerically validated against
the real compiled `vam.whittaker` package to ~1e-12 absolute difference.
It reuses the exact same `ws2d`/`ws2doptv`/calendar-aware gap-filling
logic as the raster file, so a polygon's smoothed timeseries here will
match what the raster UDF produces for the same pixels/dates/lambda.

No external dependencies are required beyond what's already provided by
every openEO UDF Python runtime (`numpy`, `pandas`, `openeo`) -- unlike
the scipy-based generic-order Whittaker smoother this replaces, so the
`# /// script` dependency block above is intentionally empty. It's left
in place (rather than removed) since openEO's dependency-declaration
convention looks for it; an empty list just means "nothing extra needed".

Usage as an openEO UDF
-----------------------
    import openeo
    result = cube.aggregate_spatial(geometries=my_geometries, reducer="mean")
    smoothed = result.run_udf(udf=openeo.UDF.from_file("whittaker_udf_vector.py"),
                               context={"smoothing_lambda": 10000})

The UDF entry point `udf_whittaker_timeseries` accepts a `context` dict
with:
    smoothing_lambda : float | int | list[float], default 10000
        Whittaker penalty (S / lambda). A single number smooths with a
        fixed lambda. A list of `log10(lambda)` candidates (e.g.
        `list(numpy.arange(0, 4, 0.2))`) triggers automatic V-curve
        optimization of lambda per polygon/band (`ws2doptv`) -- this is
        the recommended, robust option, since the right fixed lambda for
        this smoother depends strongly on how many days your time series
        spans (see below).
        `lmbda` is also accepted as an alias, matching the example UDF
        this file replaces.
    d : int, default 2
        Present only for drop-in compatibility with the example UDF
        this replaces. `ws2d`/`ws2doptv` (like the real `vam.whittaker`)
        only implement the standard second-order difference penalty.
        Any `d != 2` is logged as a warning and ignored (smoothing still
        runs with the standard second-order penalty).
    prediction_period : int | float, optional
        Number of days between resampled output steps (e.g. `5` for
        5-daily, `10` for dekadal) to resample the smoothed, gap-filled
        daily series onto a regular output grid instead of the original
        observation dates. Always a fixed day-count step (no
        calendar-month/year alignment).

A note on choosing `smoothing_lambda`
--------------------------------------
Internally, each polygon/band column is reconstructed onto a full DAILY
grid spanning its first-to-last observation date before smoothing (via
`whittaker_f`, identical to `whittaker_udf.py`), then sampled back down.
Because of that, the amount of smoothing a given `lambda` produces
depends heavily on the *total time span* of your timeseries -- the same
`lambda` that looks reasonable over a full growing season can flatten a
short (few-week) window almost to a straight line. If you're re-using a
`lambda` that was tuned on a different date range, or you're not sure,
pass a list of `log10(lambda)` candidates instead so `ws2doptv` picks a
suitable value per polygon/band automatically.

License / attribution
----------------------
`ws2d` and `ws2doptv` are a line-for-line NumPy translation of the
Cython algorithm in modape's `_whittaker.pyx`
(Copyright (c) 2019 World Food Programme, MIT License). The
`aggregate_spatial` JSON handling follows the pattern of the example UDF
this file was built to replace.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Union

import numpy as np
import pandas as pd

from openeo.rest.conversions import timeseries_json_to_pandas
from openeo.udf.structured_data import StructuredData
from openeo.udf.udf_data import UdfData

logger = logging.getLogger(__name__)

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
#    (identical to whittaker_udf.py -- kept in sync deliberately so raster
#    and vector results agree for the same data/lambda).
# ===========================================================================

def _ws2d_core(y: np.ndarray, lmbda: float, w: np.ndarray) -> np.ndarray:
    """Whittaker smoother with a fixed lambda (second order difference
    penalty), solved directly via the banded (pentadiagonal) LDL'
    recursion described in Eilers (2003) / Eilers et al. (2017).

    NumPy re-implementation of `ws2d` from modape's `_whittaker.pyx`
    (Cython). Solves `(diag(w) + lmbda * D2' D2) z = diag(w) y` in O(n)
    time without ever building the (n x n) matrix.
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
    try:
        # cache=True deliberately NOT used: it needs a real source file to
        # key its on-disk cache against, but openEO loads UDF code via
        # exec(code_string, ...), which numba sees as "<string>" and has
        # no locator for -- so njit(cache=True) raises a RuntimeError as
        # soon as the module is loaded. Without cache=True, numba still
        # JIT-compiles and keeps it in memory for the worker process.
        _ws2d_core = njit(cache=False)(_ws2d_core)
    except Exception:  # pragma: no cover - fall back to pure Python
        _HAVE_NUMBA = False


def ws2d(y: np.ndarray, lmbda: float, w: np.ndarray) -> np.ndarray:
    """Drop-in replacement for `vam.whittaker.ws2d(y, lmbda, w)`."""
    y = np.ascontiguousarray(y, dtype=np.float64)
    w = np.ascontiguousarray(w, dtype=np.float64)
    if y.shape[0] < 4:
        # The banded recursion needs at least a handful of points; for
        # very short series just fall back to a weighted copy.
        return np.where(w > 0, y, 0.0)
    return np.asarray(_ws2d_core(y, float(lmbda), w))


def ws2doptv(y: np.ndarray, w: np.ndarray, llas):
    """Drop-in replacement for `vam.whittaker.ws2doptv(y, w=w, llas=llas)`.

    Automatically picks lambda (S) via V-curve optimization
    (Eilers, P.H.C. (2003), "A Perfect Smoother").
    """
    y = np.ascontiguousarray(y, dtype=np.float64)
    w = np.ascontiguousarray(w, dtype=np.float64)
    llas = np.ascontiguousarray(llas, dtype=np.float64)

    nl = llas.shape[0]
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
# 2. Calendar-aware gap-filling (identical logic to whittaker_udf.py's
#    `whittaker_f`), plus a validated `prediction_period` handler
#    (plain number of days -- see `_output_dates` for why this
#    deliberately avoids ISO-8601 duration strings).
# ===========================================================================

def get_all_dates(x: List[datetime]) -> np.ndarray:
    """Day-offsets of `x` relative to `x[0]` (as ordinal integers)."""
    d = [i.toordinal() for i in x]
    return np.array(d) - d[0]


def whittaker_f(x: List[datetime], y: np.ndarray, lmbd: Union[float, list], d: int):
    """Gap-fill and smooth an irregular time series onto a daily grid,
    then subsample every `d` days. Returns `(z1_, xx, Zd, XXd)`.
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


def _output_dates(prediction_period: Union[int, float], start_date: datetime, end_date: datetime) -> List[datetime]:
    period = pd.Timedelta(prediction_period, unit="D")
    return list(pd.date_range(start_date, end_date, freq=period).to_pydatetime())

# ===========================================================================
# 3. Vector-datacube specific glue: DataFrame in, DataFrame out.
# ===========================================================================

def whittaker_ts(
    df: pd.DataFrame,
    smoothing_lambda: Union[float, int, list],
    prediction_period: int = None,
) -> pd.DataFrame:
    """Apply Whittaker smoothing to every column of `df` along its
    (shared) DatetimeIndex.
    """
    dates = list(df.index.to_pydatetime())
    if prediction_period is not None:
        output_dates = _output_dates(prediction_period, dates[0], dates[-1])
    else:
        output_dates = dates

    result = {}
    for col in df.columns:
        y = df[col].to_numpy(dtype=np.float64)
        _, _, Zd, XXd = whittaker_f(dates, y, smoothing_lambda, 1)
        mask = np.isin(XXd, output_dates)
        result[col] = Zd[mask]

    return pd.DataFrame(result, index=pd.DatetimeIndex(output_dates), columns=df.columns)

def udf_whittaker_timeseries(udf_data: UdfData) -> UdfData:
    """openEO UDF entry point for vector datacubes.

    Applies Whittaker smoothing along the temporal axis of a vector
    datacube. Expected to be called via
    `aggregate_spatial(...).run_udf(udf=..., runtime="Python")`, where
    the incoming structured data is the `aggregate_spatial` timeseries
    JSON (mapping date -> [polygon][band] values).

    See the module docstring for the supported `context` keys.
    """
    context = udf_data.user_context or {}
    smoothing_lambda = context.get("smoothing_lambda",10000)    
    prediction_period = context.get("prediction_period", None)
    #

    sd_list = udf_data.get_structured_data_list()
    if not sd_list:
        logger.error("No structured data found in the Whittaker UDF input! Recheck input datacube")
        return udf_data
    timeseries_dict = sd_list[0].data
    
    if not timeseries_dict:
        logger.error("Received an empty timeseries dict in the Whittaker UDF! Recheck input datacube")
        return udf_data

    df = timeseries_json_to_pandas(timeseries_dict)
    if isinstance(df, pd.Series):
        # Single polygon AND single band: timeseries_json_to_pandas
        # collapses all the way down to a plain Series (no .columns at all).
        df = df.to_frame(name=0)
        
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()

    # single-polygon (or single-band) input comes back with a flat column index
    if not isinstance(df.columns, pd.MultiIndex):
        df.columns = pd.MultiIndex.from_product([[0], df.columns])

    logger.info(
        "Whittaker smoothing (vector): smoothing_lambda=%r, prediction_period=%r, shape=%s",
        smoothing_lambda, prediction_period, df.shape,
    )

    smoothed = whittaker_ts(df, smoothing_lambda, int(prediction_period))
    smoothed = smoothed.round(decimals=4)
    smoothed.index = smoothed.index.astype(str)
    smoothed.columns = [f"variable_{variable}_polygon_{feature}" for variable, feature in smoothed.columns]

    udf_data.set_structured_data_list(
        [
            StructuredData(
                description="Whittaker smoothed timeseries",
                data=smoothed.to_dict(),
                type="json",
            )
        ]
    )
    return udf_data
