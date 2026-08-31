# /// script
# dependencies = [
#   "scipy",
# ]
# ///

import functools
import xarray
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from openeo.udf import inspect


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

    E = sparse.eye(m, format="csc")
    D = E.copy()
    for _ in range(d):
        D = D[1:] - D[:-1]

    W = sparse.diags(weights, 0)
    Z = W + lmbda * (D.T @ D)
    z = spsolve(Z.tocsc(), W @ y_filled)
    return z



def apply_datacube(cube: xarray.DataArray, context: dict) -> xarray.DataArray:
    """
    Applies Whittaker smoothing along the temporal dimension ('t') of a datacube.

    Expected to be called via `apply_dimension(process=UDF, dimension="t")`
    so the full time series per pixel/band is available in one call.

    Args:
        cube (xarray.DataArray): dims typically (t, bands, y, x) or (t, y, x)
        context (dict): may contain 'lmbda' and 'd' smoothing parameters
    Returns:
        xarray.DataArray: same shape/dims as input, smoothed along 't'
    """
    lmbda = context.get("lmbda", 10)
    d = context.get("d", 2)

    inspect(message=f"Whittaker smoothing: lmbda={lmbda}, d={d}, dims={cube.dims}")

    smoothed = xarray.apply_ufunc(
        functools.partial(whittaker_1d, lmbda=lmbda, d=d),
        cube,
        input_core_dims=[["t"]],
        output_core_dims=[["t"]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[float],
    )

    # apply_ufunc preserves dim order except moves 't' to the end; restore original order
    smoothed = smoothed.transpose(*cube.dims)
    smoothed = smoothed.assign_coords(cube.coords)

    return smoothed