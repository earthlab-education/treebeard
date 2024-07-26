@echo off
setlocal

REM Get the directory where the batch file is located (the dev folder)
set "DEV_DIR=%~dp0"
set "PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard"

if "%DEV_DIR:~-1%"=="\" set "DEV_DIR=%DEV_DIR:~0,-1%"

REM Specify the files to sync
set "FILES=treebeard.py treebeard_dialog.py __init__.py extlibs\*.*"

REM Debugging output to check paths and files
echo Development Directory: %DEV_DIR%
echo Plugin Directory: %PLUGIN_DIR%
echo Files to sync: %FILES%

echo Syncing the specified files from development folder to QGIS plugin directory...

REM Use robocopy to copy only the specified files if they have changed
robocopy "%DEV_DIR%" "%PLUGIN_DIR%" %FILES% /XO /XC /R:3 /W:10

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

echo Installing dependencies using QGIS...

REM Set up the environment for QGIS
call "%QGIS_DIR%\bin\o4w_env.bat"

REM Use the QGIS Python environment to install dependencies
"%QGIS_DIR%\bin\python3.exe" -m pip install numpy
"%QGIS_DIR%\bin\python3.exe" -m pip install rioxarray
"%QGIS_DIR%\bin\python3.exe" -m pip install rasterio
"%QGIS_DIR%\bin\python3.exe" -m pip install geopandas
"%QGIS_DIR%\bin\python3.exe" -m pip install shapely
"%QGIS_DIR%\bin\python3.exe" -m pip install scipy
"%QGIS_DIR%\bin\python3.exe" -m pip install whitebox
"%QGIS_DIR%\bin\python3.exe" -m pip install scikit-learn

echo Restart QGIS to see the changes.
pause
endlocal
