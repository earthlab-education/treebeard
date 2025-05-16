@echo off
setlocal

REM Dynamically find the latest installed QGIS version
for /d %%D in ("C:\Program Files\QGIS *") do set "QGIS_DIR=%%D"

REM Ensure that QGIS was found
if not exist "%QGIS_DIR%" (
    echo QGIS installation not found in C:\Program Files\
    pause
    exit /b 1
)

echo Using QGIS installation at: %QGIS_DIR%

REM Define the OSGeo4W environment batch file
set "OSGeo4W_SETUP=%QGIS_DIR%\OSGeo4W.bat"

REM Ensure the OSGeo4W batch file exists
if not exist "%OSGeo4W_SETUP%" (
    echo OSGeo4W batch file not found at %OSGeo4W_SETUP%
    pause
    exit /b 1
)

REM Start a new shell using OSGeo4W.bat so the environment persists
call "%OSGeo4W_SETUP%"
if errorlevel 1 (
    echo Failed to set up OSGeo4W environment
    pause
    exit /b 1
)

REM Install Python packages in that environment
python3 -m pip install --upgrade pip
python3 -m pip install --force-reinstall rioxarray rasterio geopandas shapely scipy whitebox scikit-learn fiona pyogrio laspy earthpy tqdm

if errorlevel 1 (
    echo Error occurred during the installation of packages.
    pause
    exit /b 1
)

python3 -c "import rioxarray, rasterio, geopandas, shapely; print('Packages installed correctly')"

echo Restart QGIS to see the changes.
pause
endlocal
