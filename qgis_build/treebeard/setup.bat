@echo off

REM Navigate to the directory containing the script
cd /d "%~dp0"

REM Create extlibs directory if it doesn't exist
IF NOT EXIST extlibs (
    mkdir extlibs
)

REM Install dependencies into extlibs
pip install fiona geopandas numpy rasterio scikit-learn shapely gdal --target=extlibs

REM Inform the user
echo Dependencies installed in extlibs directory.
pause
