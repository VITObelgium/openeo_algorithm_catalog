# Changelog for **Phenology Detection** Service

### 26/11/2025

#### Added
- Migrated the Phenology Detection algorithm to a public GitHub repository.
- Added benchmark scenario example notebook for Phenology Detection service.
- Added the ndvi calculation step before applying the Phenology function within the service.

#### Updated
- Updated the documentation to reflect the new repository location.
- Spatial and temporal filtering done within the `load_collection` process.
- Removed the `input_raster` parameter and updated to take spatial_extent and temporal_extent input parameters.

### 19/06/2025

#### Changed
- Updated SCL masking from `mask_scl_dilation` to `to_scl_dilation_mask`.

### Initial release

- Migrated the MOGPR service as-is from the FuseTS implementation.
- The service is available in the marketplace under the namespace: https://openeo.dataspace.copernicus.eu/openeo/processes/u:6391851f-9042-4108-8b2a-3dd2e8a9dd0b/phenology"