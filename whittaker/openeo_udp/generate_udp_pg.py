""" "
This script generates the OpenEO UDP for the Whittaker algorithm.
Implemented by https://open-eo.github.io/FuseTS/
Contact: marketplace@terrascope.be
"""

from pathlib import Path
import json

import openeo
from fusets.openeo import load_whittakker_udf
from openeo.api.process import Parameter
from openeo.processes import apply_dimension
from openeo.rest.udp import build_process_dict


def generate() -> dict:
    print("Generating UDP for Whittaker...")
    connection = openeo.connect("openeo.dataspace.copernicus.eu")
    print("Defining parameters...")
    spatial_extent = Parameter.spatial_extent(
        name="spatial_extent",
        description="Limits the data to process to the specified bounding box or polygons.\\n\\nFor raster data, the process loads the pixel into the data cube if the point at the pixel center intersects with the bounding box or any of the polygons (as defined in the Simple Features standard by the OGC).\\nFor vector data, the process loads the geometry into the data cube if the geometry is fully within the bounding box or any of the polygons (as defined in the Simple Features standard by the OGC). Empty geometries may only be in the data cube if no spatial extent has been provided.\\n\\nEmpty geometries are ignored.\\nSet this parameter to null to set no limit for the spatial extent.",
    )
    temporal_extent = Parameter.temporal_interval(
        name="temporal_extent",
        description="Temporal extent specified as two-element array with start and end date/date-time.",
    )
    smoothing_lambda = Parameter.integer(
        name="smoothing_lambda",
        description="Smoothing parameter for the Whittaker smoother. Higher values result in a smoother time series. Typical values are between 10 and 100000.",
        default=10000,
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

    whittaker_cube = apply_dimension(
        base_ndvi,
        process=lambda x: x.run_udf(
            udf=(
                Path(__file__).parent.parent.parent / "utils" / "set_dependency_path.py"
            ).read_text()
            + "\n"
            + load_whittakker_udf(),
            runtime="Python",
            version="3.8",
            context={"smoothing_lambda": smoothing_lambda},
        ),
        dimension="t",
    )
    print("Applying Whittaker smoothing...")

    # Calculate the average time series value for the given area of interest
    whittaker = whittaker_cube.aggregate_spatial(spatial_extent, reducer="mean")

    return build_process_dict(
        process_graph=whittaker,
        process_id="whittaker",
        summary="Calculate Whittaker smoothing from Sentinel-2 NDVI",
        description=(Path(__file__).parent / "readme.md").read_text(),
        parameters=[
            spatial_extent,
            temporal_extent,
        ],
    )


if __name__ == "__main__":
    # save the generated process to a file
    with open("whittaker.json", "w") as f:
        json.dump(generate(), f, indent=2)
        print("UDP 'whittaker.json' generated.")
