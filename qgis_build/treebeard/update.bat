@echo off
setlocal

REM Get the directory where the batch file is located (the dev folder)
set "DEV_DIR=%~dp0"
set "PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard"

if "%DEV_DIR:~-1%"=="\" set "DEV_DIR=%DEV_DIR:~0,-1%"

REM List of files to sync
set "FILES=treebeard.py treebeard_dialog.py import_raster_dialog.py import_lidar_dialog.py __init__.py progress_dialog.py treebeard_dialog_base.ui setup.bat setup.sh resources.qrc update. process_lidar.py drapp.py segment_drapp.py"

REM Debugging output to check paths and files
echo Development Directory: %DEV_DIR%
echo Plugin Directory: %PLUGIN_DIR%
echo Files to sync: %FILES%

echo Syncing the specified files from development folder to QGIS plugin directory...

REM Iterate over the list of files and sync each one
for %%F in (%FILES%) do (
    echo Syncing %%F...
    robocopy "%DEV_DIR%" "%PLUGIN_DIR%" "%%F" /XO /XC /R:3 /W:10
)

echo Restart QGIS to see the changes.
pause
endlocal
