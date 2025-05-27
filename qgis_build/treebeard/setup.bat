@echo off
setlocal enabledelayedexpansion

REM === Automatically find QGIS installation ===
for /f "delims=" %%D in ('dir "C:\Program Files\QGIS*" /ad /b /o-n') do (
    set "QGIS_DIR=C:\Program Files\%%D"
    goto found_qgis
)

echo QGIS installation not found in C:\Program Files\QGIS*
pause
exit /b 1

:found_qgis
echo Using QGIS installation at: "%QGIS_DIR%"

REM === Set PATH and environment variables ===
set "PATH=%QGIS_DIR%\bin;%QGIS_DIR%\apps\Python312\Scripts;%QGIS_DIR%\apps\Python312\bin;%QGIS_DIR%\apps\qgis\bin;%QGIS_DIR%\apps\grass\bin;%PATH%"
set "PYTHONNOUSERSITE=1"
set "OSGeo4W_SETUP=%QGIS_DIR%\osgeo4w.bat"

REM === Confirm OSGeo4W batch file exists ===
if not exist "%OSGeo4W_SETUP%" (
    echo OSGeo4W batch file not found at %OSGeo4W_SETUP%
    pause
    exit /b 1
)

REM === Clean user site-packages that may conflict ===
echo Cleaning user site-packages...
rmdir /s /q "%APPDATA%\Python\Python312\site-packages\numpy" 2>nul
rmdir /s /q "%APPDATA%\Python\Python312\site-packages\numpy-*" 2>nul
rmdir /s /q "%APPDATA%\Python\Python312\site-packages\xarray" 2>nul
rmdir /s /q "%APPDATA%\Python\Python312\site-packages\rioxarray" 2>nul

echo.
echo Uninstalling existing numpy...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip uninstall -y numpy

echo.
echo Installing numpy==1.26.4...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip install --no-cache-dir numpy==1.26.4

echo.
echo Uninstalling existing xarray...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip uninstall -y xarray

echo.
echo Installing xarray==2024.2.0...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip install --no-cache-dir xarray==2024.2.0

echo.
echo Uninstalling rioxarray and rasterio...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip uninstall -y rioxarray rasterio

echo.
echo Installing rioxarray and rasterio...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip install --no-cache-dir --force-reinstall rioxarray rasterio

echo.
echo Installing additional dependencies...
call "%OSGeo4W_SETUP%" ^
    python3 -m pip install --no-cache-dir --force-reinstall geopandas shapely scipy whitebox scikit-learn fiona pyogrio laspy earthpy tqdm

echo.
echo Verifying installed packages...
call "%OSGeo4W_SETUP%" ^
    python3 -c "import numpy, xarray, rioxarray, rasterio, geopandas, shapely; print('✅ Packages installed. numpy:', numpy.__version__, '| xarray:', xarray.__version__, '| rioxarray:', rioxarray.__version__, '| rasterio:', rasterio.__version__)"

if errorlevel 1 (
    echo ❌ Error occurred during the installation of packages.
    pause
    exit /b 1
)

echo All packages installed successfully. ✅
echo Please restart QGIS to apply changes.
pause
endlocal
