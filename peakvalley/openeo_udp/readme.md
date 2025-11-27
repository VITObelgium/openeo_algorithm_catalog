# Peak Valley Detection

## Overview

The `peakvalley` process provides automated detection of peaks and valleys in time-series data by analysing amplitude changes and slope patterns. It identifies significant drops, recoveries, and inflexion points to classify each time step as a peak, a valley, or a neutral state. 
This process is particularly useful for applications such as vegetation phenology monitoring, hydrological studies, and climate data analysis.

## Parameters

The `mogpr_s2` service requires the following parameters:


| Name            | Description                                                    | Type    | Default |
| --------------- | -------------------------------------------------------------- | ------- | ------- |
| spatial_extent  | Polygon representing the AOI on which to apply the data fusion | GeoJSON |         |
| temporal_extent | Date range for which to apply the data fusion                  | Array   |         |
| drop_threshold  | Threshold to drop low confidence predictions                   | Float   | 0.15    |
| recovery_ratio  | Ratio to recover from drops in the data                        | Float   | 1.0     |
| slope_threshold  | Threshold to identify steep slopes in the data                | Float   | 0.007   |
