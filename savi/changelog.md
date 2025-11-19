# Changelog for **SAVI** Service

### 18/11/2025

#### Added
- Migrated the SAVI algorithm to a public GitHub repository.
- Added benchmark scenario example notebook for SAVI service.

#### Updated
- Updated the documentation to reflect the new repository location.
- Spatial and temporal filtering done within the `load_collection` process.
- Updated the `polygon` parameter name to `spatial_extent` for consistency with other services.
- Updated the `date` parameter name to `temporal_extent` for consistency with other services.
- Updated the service name `SAVI` to `savi`.
- Updated the namespace URL to point to the JSON file hosted in the GitHub repository.




### 04/06/2025

#### Changed
- Updated SCL masking from `mask_scl_dilation` to `to_scl_dilation_mask`.


### Initial release

- Migrated the SAVI service as-is from the EOplaza Implementation.
- The service is available in the marketplace under the namespace: https://openeo.dataspace.copernicus.eu/openeo/1.2/processes/u:3e24e251-2e9a-438f-90a9-d4500e576574/SAVI
