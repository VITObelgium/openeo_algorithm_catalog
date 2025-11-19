"""
Implementation of Normalized Difference Water Index (NDWI) from Sentinel-2 L2A for the Copernicus Dataspace Ecosystem Marketplace.
The Principal Investigator for this algorithm is the Terrascope Team of VITO Remote Sensing.
Implementation originally based on nextland_services/vegetationwaterindices.py from nextland project
Contact: marketplace@terrascope.be

"""

# import necessary modules
import json
from pathlib import Path

import openeo
from openeo.api.process import Parameter
from openeo.rest.udp import build_process_dict


def generate() -> dict:
    print("Generating UDP for NDWI...")
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
        bands=["B08", "B12"],
    )
    scl = connection.load_collection(
        "SENTINEL2_L2A",
        temporal_extent=temporal_extent,
        spatial_extent=spatial_extent,
        bands=["SCL"],
    )
    print("Applying cloud masking and calculating NDWI...")
    # Apply cloud masking
    mask = scl.process("to_scl_dilation_mask", data=scl)
    cube = cube.mask(mask=mask)
    print("Calculating NDWI...")
    # calculate ndwi
    b08 = cube.band(0)
    b12 = cube.band(1)
    ndwi = (b08 - b12) / (b08 + b12)

    print("NDWI calculation complete.")

    return build_process_dict(
        process_graph=ndwi,
        process_id="ndwi",
        description=(Path(__file__).parent / "readme.md").read_text(),
        parameters=[
            spatial_extent,
            temporal_extent,
        ],
    )


if __name__ == "__main__":
    with open("ndwi.json", "w") as f:
        json.dump(generate(), f, indent=2)
    print("UDP 'ndwi.json' generated.")
