"""
Implement sth

"""

# import necessary modules
import json
from pathlib import Path

import openeo
from openeo.api.process import Parameter
from openeo.rest.udp import build_process_dict


def generate() -> dict:
    print("Generating UDP for  hbdbh...")
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
    cropsar = connection.datacube_from_process(
          "CropSAR", 
          namespace="vito",
          polygon=spatial_extent,
          date=temporal_extent, 
          biopar_type="FAPAR"
          )

    return build_process_dict(
        process_graph=cropsar,
        process_id="CropSAR_testprivate",
        # description=(Path(__file__).parent / "readme.md").read_text(),
        description="CropSAR test private UDP",
        summary="CropSAR test private UDP",
        parameters=[
            spatial_extent,
            temporal_extent,
        ],
    )


if __name__ == "__main__":
    with open("CropSAR_testprivate.json", "w") as f:
        json.dump(generate(), f, indent=2)
    print("UDP 'CropSAR_testprivate.json' generated.")