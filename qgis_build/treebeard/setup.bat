@echo off
setlocal

REM Get the directory where the batch file is located (the dev folder)
set "DEV_DIR=%~dp0"
set "PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard"

if "%DEV_DIR:~-1%"=="\" set "DEV_DIR=%DEV_DIR:~0,-1%"

REM Specify the files to sync
set "FILES=treebeard.py treebeard_dialog.py __init__.py"

REM Debugging output to check paths and files
echo Development Directory: %DEV_DIR%
echo Plugin Directory: %PLUGIN_DIR%
echo Files to sync: %FILES%

echo Syncing the specified files from development folder to QGIS plugin directory...

REM Use robocopy to copy only the specified files if they have changed
for %%f in (%FILES%) do (
    robocopy "%DEV_DIR%" "%PLUGIN_DIR%" "%%f" /XO /XC /R:3 /W:10
)

REM Set the path to the standalone QGIS installation directory
set "QGIS_DIR=C:\Program Files\QGIS 3.36.3"

REM Verify the QGIS_DIR path
if not exist "%QGIS_DIR%\bin\o4w_env.bat" (
    echo The QGIS_DIR path "%QGIS_DIR%" is incorrect.
    echo Please set the QGIS_DIR environment variable to the correct QGIS installation directory.
    pause
    exit /b 1
)

echo QGIS_DIR is set to %QGIS_DIR%

echo Installing dependencies using OSGeo4W shell...

REM Set up the environment for QGIS
call "%QGIS_DIR%\bin\o4w_env.bat"

REM Ensure GDAL path is included
set "PATH=%QGIS_DIR%\apps\gdal\bin;%PATH%"

REM Use the OSGeo4W shell to install the required packages
set "OSGEO4W_SHELL=%QGIS_DIR%\OSGeo4W.bat"
set "PACKAGES=python3-rioxarray python3-rasterio python3-geopandas python3-shapely python3-scipy python3-whitebox python3-scikit-learn python3-fiona python3-pyogrio"

REM Run osgeo4w-setup.exe to install the required packages
for %%p in (%PACKAGES%) do (
    echo Installing %%p...
    "%OSGEO4W_SHELL%" --advanced --package %%p
)

echo Restart QGIS to see the changes.
pause
endlocal
