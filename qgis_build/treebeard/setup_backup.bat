@echo off
setlocal

REM Set the QGIS directory and handle spaces by enclosing in double quotes
set "QGIS_DIR=C:\Program Files\QGIS 3.34.10"

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

echo Uninstalling numpy...
call "%OSGeo4W_SETUP%" ^
python3 -m pip uninstall -y numpy

echo Installing numpy version 1.26.4...
call "%OSGeo4W_SETUP%" ^
python3 -m pip install numpy==1.26.4

echo Uninstalling xarray...
call "%OSGeo4W_SETUP%" ^
python3 -m pip uninstall -y xarray

echo Installing compatible xarray version 2024.2.0...
call "%OSGeo4W_SETUP%" ^
python3 -m pip install xarray==2024.2.0

echo Installing other dependencies...
call "%OSGeo4W_SETUP%" ^
python3 -m pip install --force-reinstall rioxarray rasterio geopandas shapely scipy whitebox scikit-learn fiona pyogrio laspy earthpy tqdm

echo Verifying package installation...
call "%OSGeo4W_SETUP%" ^
python3 -c "import numpy, xarray, rioxarray, rasterio, geopandas, shapely; print('Packages installed correctly. numpy:', numpy.__version__, 'xarray:', xarray.__version__)"

if errorlevel 1 (
    echo "Error occurred during the installation of packages."
    pause
    exit /b 1
)

echo Restart QGIS to see the changes.
pause
endlocal
