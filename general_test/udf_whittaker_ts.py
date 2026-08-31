# /// script
# dependencies = [
#   "scipy",
# ]
# ///

import logging

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve

from openeo.rest.conversions import timeseries_json_to_pandas
from openeo.udf.structured_data import StructuredData
from openeo.udf.udf_data import UdfData

logger = logging.getLogger(__name__)


def whittaker_1d(y, lmbda=10, d=2, weights=None):
    """
    Whittaker smoother for a 1D series (handles NaNs as zero-weight gaps).
    """
    y = np.asarray(y, dtype=float)
    m = len(y)

    if m < d + 1:
        # too short to smooth meaningfully, return as-is
        return y

    if weights is None:
        weights = np.ones(m)
    else:
        weights = np.asarray(weights, dtype=float).copy()
    weights[np.isnan(y)] = 0
    y_filled = np.where(np.isnan(y), 0, y)

    if weights.sum() < d + 1:
        # not enough valid observations to constrain the fit
        return np.full(m, np.nan)

    E = sparse.eye(m, format="csc")
    D = E.copy()
    for _ in range(d):
        D = D[1:] - D[:-1]

    W = sparse.diags(weights, 0)
    Z = W + lmbda * (D.T @ D)
    z = spsolve(Z.tocsc(), W @ y_filled)
    return z


def udf_whittaker_timeseries(udf_data: UdfData) -> UdfData:
    """
    Applies Whittaker smoothing along the temporal axis of a vector datacube.

    Expected to be called via `aggregate_spatial(...).run_udf(udf=..., runtime="Python")`,
    where the incoming structured data is the aggregate_spatial timeseries JSON
    (mapping date -> [feature][band] values).

    Context keys:
        lmbda: smoothing strength (default 10)
        d: order of the difference penalty (default 2)
    """
    context = udf_data.user_context or {}
    lmbda = context.get("lmbda", 10)
    d = context.get("d", 2)

    timeseries_dict = udf_data.get_structured_data_list()[0].data
    if not timeseries_dict:
        logger.error("Received an empty timeseries dict in the Whittaker UDF! Recheck input datacube")
        return udf_data

    df = timeseries_json_to_pandas(timeseries_dict)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()

    # single-polygon input comes back with a flat column index
    if not isinstance(df.columns, pd.MultiIndex):
        df.columns = pd.MultiIndex.from_product([[0], df.columns])

    logger.info(f"Whittaker smoothing: lmbda={lmbda}, d={d}, shape={df.shape}")

    smoothed = df.apply(lambda col: whittaker_1d(col.values, lmbda=lmbda, d=d), axis=0, result_type="broadcast")
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
