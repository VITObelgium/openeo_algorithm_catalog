# Terrascope openEO Service Catalog

## Overview

This repository serves as a catalog for openEO algorithms developed by Terrascope that are available as User Defined Processes (UDPs). T

These UDPs will be hosted either in EOplaza(https://portal.terrascope.be/) or CDSE (https://marketplace-portal.dataspace.copernicus.eu/).

## Structure

Each algorithm is organized in its own directory within this repository in the servi

. The structure of each algorithm directory is as follows:

```

algorithm_name/
├── openeo_udp/         # Directory containing the openEO UDP implementation
│   ├── __init__.py     # Initialization file for the UDP package
│   ├── generate_pg.py     # Main algorithm implementation file that generates the process graph
│   ├── utils.py        # Utility functions used by the UDP
│   └── requirements.txt # List of dependencies for the UDP
    ├── algorithm_name_pg.json  # Process graph generated of the UDP
|   └── README.md        # Documentation specific to the UDP
└── benchmark_scenarios/  # Directory containing benchmark scenarios for the algorithm
    ├── example.ipynb  # Example Jupyter notebook demonstrating the algorithm usage
    └── algorithm_name.json  # Benchmark scenario definition generated from the UDP demostrated in the notebook
    
            

```
