"""
This script generates an OpenEO User Defined Process (UDP) for fusing Sentinel-1 and Sentinel-2 time series data
using multi-output Gaussian Process Regression (MOGPR).
Implemented by https://open-eo.github.io/FuseTS/
Contact: marketplace@terrascope.be

"""

import json
from pathlib import Path
from typing import Union, Sequence

import openeo
from openeo.api.process import Parameter
from openeo.processes import ProcessBuilder, apply_neighborhood
from openeo.rest.udp import build_process_dict

from fusets.openeo import load_mogpr_udf

from helper_functions import load_s1_collection, load_s2_collection

connection = openeo.connect("openeofed.dataspace.copernicus.eu")


def get_mogpr_s1_s2(
    polygon: Union[Parameter, dict] = None,
    date: Union[Sequence[str], Parameter] = None,
    s1_collection: Union[str, Parameter] = None,
    s2_collection: Union[str, Parameter] = None,
) -> ProcessBuilder:
    """
    Create a process graph for fusing Sentinel-1 and Sentinel-2 time series data using MOGPR.
    :param polygon: Spatial extent for data loading.
    :param date: Temporal extent for data loading.
    :param s1_collection: Sentinel-1 data collection to use.
    :param s2_collection: Sentinel-2 data collection to use.
    :return: ProcessBuilder representing the MOGPR fusion process graph.
    """
    s1_input_cube = load_s1_collection(connection, s1_collection, polygon, date)
    s2_input_cube = load_s2_collection(connection, s2_collection, polygon, date)

    # Merge the inputs to a single datacube
    merged_cube = s2_input_cube.merge_cubes(s1_input_cube)

    return apply_neighborhood(
        merged_cube,
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


def generate() -> dict:
    # define parameters
    polygon = Parameter.spatial_extent(
        name="spatial_extent",
        description="Limits the data to process to the specified bounding box or polygons.\\n\\nFor raster data, the process loads the pixel into the data cube if the point at the pixel center intersects with the bounding box or any of the polygons (as defined in the Simple Features standard by the OGC).\\nFor vector data, the process loads the geometry into the data cube if the geometry is fully within the bounding box or any of the polygons (as defined in the Simple Features standard by the OGC). Empty geometries may only be in the data cube if no spatial extent has been provided.\\n\\nEmpty geometries are ignored.\\nSet this parameter to null to set no limit for the spatial extent.",
    )
    date = Parameter.temporal_interval(
        name="temporal_extent",
        description="Temporal extent specified as two-element array with start and end date/date-time. \nThis is date range for which to apply the data fusion",
    )
    s1_collection = Parameter.string(
        name="s1_collection",
        description="S1 data collection to use for fusing the data.",
        default="RVI",
        values=["RVI", "GRD"],
    )
    s2_collection = Parameter.string(
        name="s2_collection",
        description="S2 data collection to use for fusing the data.",
        default="NDVI",
        values=["NDVI", "FAPAR", "LAI", "FCOVER", "EVI", "CCC", "CWC"],
    )

    # build the process graph for MOGPR S1-S2 fusion
    mogpr = get_mogpr_s1_s2(
        polygon=polygon,
        date=date,
        s1_collection=s1_collection,
        s2_collection=s2_collection,
    )

    return build_process_dict(
        process_graph=mogpr,
        process_id="mogpr_s1s2",
        summary="Integrate S1 and S2 timeseries using multi-output gaussian process regression",
        description=(Path(__file__).parent / "readme.md").read_text(),
        parameters=[polygon, date, s1_collection, s2_collection],
    )


if __name__ == "__main__":
    # save the generated process to a file
    with open("mogpr_s1s2.json", "w") as f:
        json.dump(generate(), f, indent=2)
        print("UDP 'mogpr_s1s2.json' generated.")
