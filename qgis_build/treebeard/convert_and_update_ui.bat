@echo off
setlocal

REM Define directories
set "DEV_DIR=%~dp0"
set "PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard"

REM Ensure the plugin directory exists
if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%"

REM Convert .ui files to .py files in the same base directory
for %%f in ("%DEV_DIR%*.ui") do (
    pyuic5 -o "%%~dpnf.py" "%%f"
)

REM Call update.bat to sync files
call "%DEV_DIR%\update.bat"

echo Conversion and update complete.
pause
endlocal
