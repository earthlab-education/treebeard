@echo off
setlocal

REM Set the QGIS directory
set QGIS_DIR=C:\Program Files\QGIS 3.36.3

REM Add the QGIS bin directory to the PATH
set PATH=%QGIS_DIR%\bin;%PATH%

REM Define the OSGeo4W setup command
set OSGeo4W_SETUP=%QGIS_DIR%\bin\osgeo4w-setup.exe

REM Ensure the OSGeo4W setup executable exists
if not exist "%OSGeo4W_SETUP%" (
    echo "OSGeo4W setup executable not found."
    exit /b 1
)

REM Sync plugin files to the QGIS plugin directory
set DEV_DIR=%~dp0
set PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard

if "%DEV_DIR:~-1%"=="\" set "DEV_DIR=%DEV_DIR:~0,-1%"
echo Development Directory: %DEV_DIR%
echo Plugin Directory: %PLUGIN_DIR%

echo Syncing the specified files from development folder to QGIS plugin directory...
robocopy "%DEV_DIR%" "%PLUGIN_DIR%" treebeard.py treebeard_dialog.py __init__.py

REM Install necessary Python packages using OSGeo4W
echo Installing dependencies using OSGeo4W...
"%OSGeo4W_SETUP%" ^ --advanced ^ --quiet ^ --packages python3-rioxarray,python3-rasterio,python3-geopandas,python3-shapely,python3-scipy,python3-whitebox,python3-scikit-learn,python3-fiona,python3-pyogrio

echo Restart QGIS to see the changes.
pause
endlocal
