## Overview

The Normalized Burn Ratio (NBR) is an index designed to highlight burnt areas whose formula combines the use of both near-infrared (NIR) and shortwave infrared (SWIR) wavelengths. To benefit from the magnitude of spectral difference, NBR uses the ratio between NIR and SWIR bands, according to the formula below. A high NBR value indicates healthy vegetation, while a low value indicates bare ground and recently burnt areas. Non-burnt areas are generally attributed to values close to zero.

## Methodology

It is calculated as a ratio between the NIR and SWIR values in traditional fashion. NBR =(NIR-SWIR)/(NIR+SWIR)

## Result
The procedure creates an image representing a qualitative descriptor that lets you map the burn severity. Furthermore, when calculating the differenced/delta NBR (dNBR), you can set a bound within bounds [-0.5, 0.1, 0.27, 0.440, 0.660, 1.3] = ['Unburned', 'Low Severity', 'Moderate-low Severity', 'Moderate-high Severity', 'High Severity'] based on the documentation from [UN-SPIDER](https://un-spider.org/advisory-support/recommended-practices/recommended-practice-burn-severity/in-detail/normalized-burn-ratio)