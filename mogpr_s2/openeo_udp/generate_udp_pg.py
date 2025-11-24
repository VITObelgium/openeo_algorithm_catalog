"""
This script generates an OpenEO User Defined Process (UDP) that uses Sentinel-2 L2A to calculate NDVI calculates
time series data using multi-output Gaussian Process Regression (MOGPR).
Implemented by https://open-eo.github.io/FuseTS/
Contact: marketplace@terrascope.be

"""

import json
from pathlib import Path

import openeo
from openeo.api.process import Parameter
from openeo.processes import apply_neighborhood
from openeo.rest.udp import build_process_dict

from fusets.openeo import load_mogpr_udf


def generate() -> dict:
    print("Generating UDP for MOGPR...")
    connection = openeo.connect("openeofed.dataspace.copernicus.eu")
    print("Defining parameters...")
    spatial_extent = Parameter.spatial_extent(
        name="spatial_extent",
        description="Limits the data to process to the specified bounding box or polygons.\\n\\nFor raster data, the process loads the pixel into the data cube if the point at the pixel center intersects with the bounding box or any of the polygons (as defined in the Simple Features standard by the OGC).\\nFor vector data, the process loads the geometry into the data cube if the geometry is fully within the bounding box or any of the polygons (as defined in the Simple Features standard by the OGC). Empty geometries may only be in the data cube if no spatial extent has been provided.\\n\\nEmpty geometries are ignored.\\nSet this parameter to null to set no limit for the spatial extent.",
    )
    temporal_extent = Parameter.temporal_interval(
        name="temporal_extent",
        description="Temporal extent specified as two-element array with start and end date/date-time.",
    )

    print("Loading data...")
    cube = connection.load_collection(
        "SENTINEL2_L2A",
        temporal_extent=temporal_extent,
        spatial_extent=spatial_extent,
        bands=[
            "B04",
            "B08",
        ],
    )
    scl = connection.load_collection(
        "SENTINEL2_L2A",
        temporal_extent=temporal_extent,
        spatial_extent=spatial_extent,
        bands=["SCL"],
    )
    print("Applying cloud masking and calculating NDVI...")
    # Apply cloud masking
    mask = scl.process("to_scl_dilation_mask", data=scl)
    cube = cube.mask(mask=mask)
    print("Calculating NDVI...")
    base_ndvi = cube.ndvi(red="B04", nir="B08")

    # build the process graph for MOGPR S1-S2 fusion
    mogpr = apply_neighborhood(
        base_ndvi,
        lambda data: data.run_udf(
            udf=(
                Path(__file__).parent.parent.parent / "utils" / "set_dependency_path.py"
            ).read_text()
            + "\n"
            + load_mogpr_udf(),
            runtime="Python",
            version="3.8",
            context=dict(),
        ),
        size=[
            {"dimension": "x", "value": 32, "unit": "px"},
            {"dimension": "y", "value": 32, "unit": "px"},
        ],
        overlap=[],
    )

    mogpr_ndvi = mogpr.aggregate_spatial(spatial_extent, reducer='mean')

    return build_process_dict(
        process_graph=mogpr_ndvi,
        process_id="mogpr_s2",
        summary="Using Sentinel L2 timeseries using multi-output gaussian process regression",
        description=(Path(__file__).parent / "readme.md").read_text(),
        parameters=[
            spatial_extent,
            temporal_extent,
        ],
    )


if __name__ == "__main__":
    # save the generated process to a file
    with open("mogpr_s2.json", "w") as f:
        json.dump(generate(), f, indent=2)
        print("UDP 'mogpr_s2.json' generated.")
