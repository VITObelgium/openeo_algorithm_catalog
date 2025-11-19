# Changelog for **EVI** Service

### 17/11/2024

#### Added
- Migrated the EVI algorithm to a public GitHub repository.
- Added benchmark scenario example notebook for EVI service.

#### Updated
- Updated the documentation to reflect the new repository location.
- Spatial and temporal filtering done within the `load_collection` process.
- Updated the `aoi` parameter name to `spatial_extent` for consistency with other services.
- Updated the `date` parameter name to `temporal_extent` for consistency with other services.
- Updated the service name `EVI` to `evi`.
- Updated the namespace URL to point to the JSON file hosted in the GitHub repository.



### 04/06/2025

#### Changed
- Updated SCL masking from `mask_scl_dilation` to `to_scl_dilation_mask`.


### Initial release

- Migrated the EVI service as-is from the EOplaza Implementation.
- The service is available in the marketplace under the namespace: https://openeo.dataspace.copernicus.eu/openeo/1.2/processes/u:3e24e251-2e9a-438f-90a9-d4500e576574/EVI
