## Overview

This service calculates Enhanced Vegetation Index (EVI) for an area and time period. The EVI is an 'optimized' vegetation index designed to enhance the vegetation signal with improved sensitivity in high biomass regions and improved vegetation monitoring through a de-coupling of the canopy background signal and a reduction in atmosphere influences.

## Methodology

For calculating the EVI, we need the reflectance of the red, blue and (near) infrared spectral components. EVI uses the blue, red, and NIR bands. It incorporates an “L” value to adjust for the canopy background, “C” values as coefficients for atmospheric resistance and values from the blue band (B). These enhancements allow for index calculation as a ratio between the R and NIR values while reducing the background noise, atmospheric noise, and saturation. This methodology rescales the digital number values to physical reflectances

The formula is EVI = G * ((NIR - R) / (NIR + C1 * R – C2 * B + L)). where G = 2.5, C1 = 6.0, C2 = 7.5 and L = 1.