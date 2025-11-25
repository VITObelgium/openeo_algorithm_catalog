""" "
This script generates the OpenEO UDP for the PeakValley algorithm.
Implemented by https://open-eo.github.io/FuseTS/
Contact: marketplace@terrascope.be
"""

from typing import Union
from pathlib import Path
import json

import openeo
from fusets.openeo.phenology_udf import load_phenology_udf
from fusets.openeo.services.publish_phenology import phenology_bands
from openeo import DataCube
from openeo.api.process import Parameter
from openeo.processes import apply_dimension, ProcessBuilder
from openeo.rest.udp import build_process_dict


def get_phenology(
    input_cube: Union[DataCube, Parameter],
) -> ProcessBuilder:

    phenology = apply_dimension(
        data=input_cube,
        process=lambda x: x.run_udf(
            udf=(
                Path(__file__).parent.parent.parent / "utils" / "set_dependency_path.py"
            ).read_text()
            + "\n"
            + load_phenology_udf(),
            runtime="Python",
            version="3.8",
        ),
        dimension="t",
        target_dimension="phenology",
    )

    phenology = phenology.add_dimension("var", phenology_bands[0], "bands")
    phenology = phenology.rename_labels(dimension="var", target=phenology_bands)

    return phenology


def generate() -> dict:
    print("Generating UDP for Phenology...")
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

    phenology = apply_dimension(
        data=base_ndvi,
        process=lambda x: x.run_udf(
            udf=(
                Path(__file__).parent.parent.parent / "utils" / "set_dependency_path.py"
            ).read_text()
            + "\n"
            + load_phenology_udf(),
            runtime="Python",
            version="3.8",
        ),
        dimension="t",
        target_dimension="phenology",
    )

    phenology = phenology.add_dimension("var", phenology_bands[0], "bands")
    phenology = phenology.rename_labels(dimension="var", target=phenology_bands)

    return build_process_dict(
        process_graph=phenology,
        process_id="phenology",
        summary="Calculate phenology metrics from Sentinel-2 NDVI",
        description=(Path(__file__).parent / "readme.md").read_text(),
        parameters=[
            spatial_extent,
            temporal_extent,
        ],
    )


if __name__ == "__main__":
    # save the generated process to a file
    with open("phenology.json", "w") as f:
        json.dump(generate(), f, indent=2)
        print("UDP 'phenology.json' generated.")
