#!/bin/bash

# Set the QGIS directory (Adjust this if needed for your QGIS installation)
QGIS_DIR="/Applications/QGIS.app/Contents/MacOS"

# Add the QGIS bin and apps directories to the PATH for correct Python and QGIS dependencies
export PATH="$QGIS_DIR/bin:$QGIS_DIR/Resources/python/bin:$QGIS_DIR/Resources/bin:$PATH"

# Ensure the QGIS Python environment is sourced correctly
OSGEO_SETUP="$QGIS_DIR/osgeo4w.bash"

# Check if the osgeo4w setup script exists
if [ ! -f "$OSGEO_SETUP" ]; then
    echo "OSGeo4W setup file not found at $OSGEO_SETUP"
    exit 1
fi

# Remove the user site-packages directory from PYTHONPATH
export PYTHONNOUSERSITE=1

# Install necessary Python packages
echo "Installing dependencies using OSGeo4W..."
source "$OSGEO_SETUP"
python3 -m pip install --upgrade pip && \
python3 -m pip install --force-reinstall rioxarray rasterio geopandas shapely scipy whitebox scikit-learn fiona pyogrio laspy earthpy tqdm && \
python3 -c "import rioxarray, rasterio, geopandas, shapely; print('Packages installed correctly')"

# Check if there was an error during the installation
if [ $? -ne 0 ]; then
    echo "Error occurred during the installation of packages."
    exit 1
fi

echo "Restart QGIS to see the changes."
