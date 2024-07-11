@echo off

REM Navigate to the directory containing the script
cd /d "%~dp0"

REM Create extlibs directory if it doesn't exist
IF NOT EXIST extlibs (
    mkdir extlibs
)

REM Install dependencies into extlibs
pip install geopandas  scikit-learn --target=extlibs

REM Inform the user
echo Dependencies installed in extlibs directory.
pause
