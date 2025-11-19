## Overview

This service calculates Soil-Adjusted Vegetation Index (SAVI) for an area and time period. The Soil-Adjusted Vegetation Index (SAVI) is an enhancement of the Normalized Difference Vegetation Index (NDVI) that takes into account the effects of soil background. SAVI minimizes soil brightness influences, making it more suitable for areas with substantial soil exposure. It is often used to assess vegetation health and density in remote sensing applications. It can be applied in agricultural monitoring to evaluate vegetation cover and health in areas with varying soil brightness, helping to distinguish between bare soil and vegetation.

## Methodology

SAVI is calculated as a ratio between the R and NIR values with a soil brightness correction factor (L) defined as 0.5 to accommodate most land cover types. The formula is SAVI = ((1 + L) * (NIR - Red)) / (NIR + Red + L), where L = 0.5.

## Result

The process generates an image representing a qualitative descriptor. The values will range from -1 to 1, with higher values indicating healthier and denser vegetation, while negative values may represent areas with minimal vegetation or regions where the soil reflects more than the vegetation.