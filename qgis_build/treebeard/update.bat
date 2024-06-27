@echo off
setlocal

REM Get the directory where the batch file is located (the dev folder)
set DEV_DIR=%~dp0
set PLUGIN_DIR=%USERPROFILE%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\treebeard

echo Syncing updated files from development folder to QGIS plugin directory...

REM Use robocopy to copy only new and changed files
robocopy "%DEV_DIR%" "%PLUGIN_DIR%" /MIR

echo Restart QGIS to see the changes.
pause
endlocal
