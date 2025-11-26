""""
This script generates the OpenEO UDP for the PeakValley algorithm.
Implemented by https://open-eo.github.io/FuseTS/
Contact: marketplace@terrascope.be
"""


import json
from pathlib import Path
from typing import Union

import openeo
from fusets.openeo.peakvalley_udf import load_peakvalley_udf
from openeo import DataCube
from openeo.api.process import Parameter
from openeo.processes import ProcessBuilder, apply_dimension
from openeo.rest.udp import build_process_dict


def create_context_param(label: str, param: Union[Parameter, any]):
    if isinstance(param, Parameter):
        return {label: {"from_parameter": param.name}}
    else:
        return {label: param}


def get_peakvalley(
    input_cube: Union[DataCube, Parameter],
    drop_param: Union[float, Parameter],
    rec_param: Union[float, Parameter],
    slope_param: Union[float, Parameter],
) -> ProcessBuilder:
    context = {}
    context.update(create_context_param("drop_thr", drop_param))
    context.update(create_context_param("rec_r", rec_param))
    context.update(create_context_param("slope_thr", slope_param))

    return apply_dimension(
        input_cube,
        process=lambda x: x.run_udf(
            udf=(
                Path(__file__).parent.parent.parent / "utils" / "set_dependency_path.py"
            ).read_text()
            + "\n"
            + load_peakvalley_udf(), runtime="Python",version="3.8", context=context
        ),
        dimension="t",
    )


def generate() -> dict:
    print("Generating UDP for PeakValley...")
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
    drop_param = Parameter.number(
        name="drop_threshold",
        description="Threshold value for the amplitude of the drop in the input feature",
        default=0.15,
    )
    rec_param = Parameter.number(
        name="recovery_ratio",
        description="Threshold value for the amplitude of the recovery, relative to the `drop_delta`",
        default=1.0,
    )
    slope_param = Parameter.number(
        name="slope_threshold",
        description="Threshold value for the slope where the peak should start",
        default=-0.007,
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

    peakvalley = get_peakvalley(
        input_cube=base_ndvi,
        drop_param=drop_param,
        rec_param=rec_param,
        slope_param=slope_param,
    )

    return build_process_dict(
        process_graph=peakvalley,
        process_id="peakvalley",
        summary="Detect peaks and valleys in a time series",
        description=(Path(__file__).parent / "readme.md").read_text(),
        parameters=[
            spatial_extent,
            temporal_extent,
            drop_param,
            rec_param,
            slope_param,
        ],
    )


if __name__ == "__main__":
    # save the generated process to a file
    with open("peakvalley.json", "w") as f:
        json.dump(generate(), f, indent=2)
        print("UDP 'peakvalley.json' generated.")
