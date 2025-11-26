# Multi output gaussian process regression based on Sentinel-2 data

## Description

This process implements a multi-output Gaussian process regression (MOGPR) on the Sentinel-2 input data to generate an integrated timeseries. While the service is similar to MOGPR based on Sentinel-1 and Sentinel-2 data, this specific implementation focuses solely on Sentinel-2 data.

## Parameters

The `mogpr_s2` service requires the following parameters:


| Name            | Description                                                    | Type    | Default |
| --------------- | -------------------------------------------------------------- | ------- | ------- |
| spatial_extent  | Polygon representing the AOI on which to apply the data fusion | GeoJSON |         |
| temporal_extent | Date range for which to apply the data fusion                  | Array   |         |


## Limitations

To ensure optimal performance and resource management, the spatial extent is limited to a maximum size equal to a Sentinel-2 MGRS tile (100 km x 100 km).

## Dependencies

In addition to various Python libraries, the workflow utilizes the following libraries included in the User-Defined Function (UDF) environment:

* Biopar: The `biopar` package retrieves biophysical parameters like FAPAR, FCOVER, and more, that were passed as the S2_collection. The biopar package is a Python package that calculates biophysical parameters from Sentinel-2 satellite images as described [here](https://step.esa.int/docs/extra/ATBD_S2ToolBox_L2B_V1.1.pdf). The `fusets_mogpr` udp directly uses the biopar udp shared in the APEX Algorithms repository.
* FuseTS: The `fusets` library was developed to facilitate data fusion and time-series analytics using AI/ML to extract insights about land environments. It functions as a Time Series & Data Fusion toolbox integrated with openEO. For additional information, please refer to the [FuseTS documentation](https://open-eo.github.io/FuseTS/installation.html).