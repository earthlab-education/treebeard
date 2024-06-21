#!/bin/bash

# Navigate to the directory containing the script
cd "$(dirname "$0")"

# Create extlibs directory if it doesn't exist
if [ ! -d "extlibs" ]; then
    mkdir extlibs
fi

# Install dependencies into extlibs
pip install fiona geopandas numpy rasterio scikit-learn shapely --target=extlibs

# Inform the user
echo "Dependencies installed in extlibs directory."
