# Multi output gaussian process regression based on Sentinel-2 data

## Description

This process implements a multi-output Gaussian process regression (MOGPR) on the Sentinel-2 input data to generate an integrated timeseries. While the service is similar to MOGPR based on Sentinel-1 and Sentinel-2 data, this specific implementation focuses solely on Sentinel-2 data.

The process is designed to fill gaps in the time series data by leveraging the correlations between different spectral bands of Sentinel-2 imagery. By using MOGPR, the process can provide a more accurate and reliable estimation of missing values, enhancing the overall quality of the time series data.