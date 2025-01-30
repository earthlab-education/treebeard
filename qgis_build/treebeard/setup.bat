@echo off
setlocal

REM Dynamically find the latest installed QGIS version
for /d %%D in ("C:\Program Files\QGIS *") do set "QGIS_DIR=%%D"

REM Ensure that QGIS was found
if not exist "%QGIS_DIR%" (
    echo "QGIS installation not found in C:\Program Files\"
    pause
    exit /b 1
)

echo "Using QGIS installation at: %QGIS_DIR%"

REM Add QGIS bin and apps directories to the PATH
set "PATH=%QGIS_DIR%\bin;%QGIS_DIR%\apps\Python312\Scripts;%QGIS_DIR%\apps\Python312\bin;%QGIS_DIR%\apps\qgis\bin;%QGIS_DIR%\apps\grass\bin;%PATH%"

REM Define the OSGeo4W setup command with the correct path
set OSGeo4W_SETUP=%QGIS_DIR%\bin\o4w_env.bat

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
&& python3 -m pip install --upgrade pip ^ 
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
