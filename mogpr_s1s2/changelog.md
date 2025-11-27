# Changelog for **MOGPR_S1S2** Service

### 26/11/2025

#### Added
- Migrated the MOGPR_S1S2 algorithm to a public GitHub repository.
- Added benchmark scenario example notebook for MOGPR_S1S2 service.
- Added the ndvi calculation step before applying the MOGPR_S1S2 function within the service.

#### Updated
- Updated the documentation to reflect the new repository location.
- Spatial and temporal filtering done within the `load_collection` process.
- Removed the `input_raster` parameter and updated to take spatial_extent, temporal_extent, s1_collection, s2_collection as input parameters.
- The default value for s1_collection is set to 'RVI' and for s2_collection is set to 'NDVI'.


### Initial release

- Migrated the MOGPR service as-is from the FuseTS implementation.
- The service is available in the marketplace under the namespace: https://openeo.dataspace.copernicus.eu/openeo/processes/u:6391851f-9042-4108-8b2a-3dd2e8a9dd0b/mogpr
