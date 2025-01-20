@echo off
setlocal

REM Set the QGIS directory and handle spaces by enclosing in double quotes
set "QGIS_DIR=C:\Program Files\QGIS 3.38.0"

REM Add the QGIS bin and apps directories to the PATH for correct Python and QGIS dependencies
set "PATH=%QGIS_DIR%\bin;%QGIS_DIR%\apps\Python312\Scripts;%QGIS_DIR%\apps\Python312\bin;%QGIS_DIR%\apps\qgis\bin;%QGIS_DIR%\apps\grass\bin;%PATH%"

REM Define the OSGeo4W setup command with the correct path
set OSGeo4W_SETUP=%QGIS_DIR%\osgeo4w.bat

REM Ensure the OSGeo4W batch file exists
if not exist "%OSGeo4W_SETUP%" (
    echo "OSGeo4W batch file not found at %OSGeo4W_SETUP%"
    pause
    exit /b 1
)

REM Remove the user site-packages directory from PYTHONPATH
set "PYTHONNOUSERSITE=1"

REM Install necessary Python packages using OSGeo4W
echo Installing dependencies using OSGeo4W...

call "%OSGeo4W_SETUP%" ^
python3 -m pip install --upgrade pip ^
&& python3 -m pip install --force-reinstall rioxarray rasterio geopandas shapely scipy whitebox scikit-learn fiona pyogrio laspy earthpy tqdm
&& python3 -c "import rioxarray, rasterio, geopandas, shapely; print('Packages installed correctly')"


if errorlevel 1 (
    echo "Error occurred during the installation of packages."
    pause
    exit /b 1
)

echo Restart QGIS to see the changes.
pause
endlocal
