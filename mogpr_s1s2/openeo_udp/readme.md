# Sentinel-1 and Sentinel-2 data fusion through Multi-output Gaussian process regression (MOGPR)

This service is designed to enable multi-output regression analysis using Gaussian Process Regression (GPR) on geospatial data. It provides a powerful tool for understanding and predicting spatiotemporal phenomena by filling gaps based on other correlated indicators. This service focuses on fusing Sentinel-1 and Sentinel-2 data, allowing the user to select one of the predefined data sources.

This User-Defined-Process (UDP) produces a datacube that contains a gap-filled time series for all pixels within the specified temporal and spatial range. This datacube can be seamlessly integrated with other openEO processes.