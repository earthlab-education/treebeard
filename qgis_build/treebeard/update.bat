@echo off
setlocal

REM Get the directory where the batch file is located (the dev folder)
set "DEV_DIR=%~dp0"
set "PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard"

if "%DEV_DIR:~-1%"=="\" set "DEV_DIR=%DEV_DIR:~0,-1%"


REM Specify the file to sync
set "FILENAME=treebeard.py"

REM Debugging output to check paths and file
echo Development Directory: %DEV_DIR%
echo Plugin Directory: %PLUGIN_DIR%
echo File to sync: %FILENAME%

echo Syncing the specified file from development folder to QGIS plugin directory...

REM Use robocopy to copy only the specified file if it has changed
robocopy "%DEV_DIR%" "%PLUGIN_DIR%" "%FILENAME%" /XO /XC /R:3 /W:10

echo Restart QGIS to see the changes.
pause
endlocal
