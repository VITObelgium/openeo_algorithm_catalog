# Terrascope openEO Service Catalog

## Overview

This repository serves as a catalog for openEO algorithms that are available as User Defined Processes (UDPs). 

These UDPs will be hosted either in EOplaza(https://portal.terrascope.be/) or CDSE (https://marketplace-portal.dataspace.copernicus.eu/).

## Structure

Each algorithm is organized in its own directory within the repository.


The structure of each algorithm directory is as follows:

```

algorithm_name/
├── openeo_udp/         # Directory containing the openEO UDP implementation
│   ├── generate_udp_pg.py     # Main algorithm implementation file that generates the process graph
│   ├── helper_functions.py        # Helper functions used by the UDP (if any)
│   └── requirements.txt # List of dependencies for the UDP (if any)
    ├── algorithm_name_pg.json  # Process graph generated of the UDP
|   └── README.md        # Documentation specific to the UDP
└── benchmark_scenarios/  # Directory containing benchmark scenarios for the algorithm
    ├── example.ipynb  # Example Jupyter notebook demonstrating the algorithm usage
    └── algorithm_name.json  # Benchmark scenario definition generated from the UDP demonstrated in the notebook
├── utils/               # Directory containing utility scripts for the algorithm
|__ changelog.md        # Changelog for the algorithm
    
            

```
