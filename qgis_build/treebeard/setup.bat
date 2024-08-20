@echo off
setlocal

REM Set the QGIS directory
set QGIS_DIR=C:\Program Files\QGIS 3.36.3

REM Add the QGIS bin directory to the PATH
set PATH=%QGIS_DIR%\bin;%PATH%

REM Define the OSGeo4W setup command
set OSGeo4W_SETUP=%QGIS_DIR%\OSGeo4W.bat

REM Ensure the OSGeo4W batch file exists
if not exist "%OSGeo4W_SETUP%" (
    echo "OSGeo4W batch file not found at %OSGeo4W_SETUP%"
    pause
    exit /b 1
)

REM Sync plugin files to the QGIS plugin directory
set DEV_DIR=%~dp0
set PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard

echo Development Directory: %DEV_DIR%
echo Plugin Directory: %PLUGIN_DIR%

echo Syncing the specified files from the development folder to the QGIS plugin directory...
robocopy "%DEV_DIR%" "%PLUGIN_DIR%" treebeard.py treebeard_dialog.py __init__.py

REM Install necessary Python packages using OSGeo4W
echo Installing dependencies using OSGeo4W...
call "%OSGeo4W_SETUP%" ^
    python3-rioxarray ^
    python3-rasterio ^
    python3-geopandas ^
    python3-shapely ^
    python3-scipy ^
    python3-whitebox ^
    python3-scikit-learn ^
    python3-fiona ^
    python3-pyogrio ^
    python3-laspy

if errorlevel 1 (
    echo "Error occurred during the installation of packages."
    pause
    exit /b 1
)

echo Restart QGIS to see the changes.
pause
endlocal
