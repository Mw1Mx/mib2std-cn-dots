@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
echo [BUILD] Starting Skin build. Progress will appear below.
echo [BUILD] Recommended first: run "dump all skins" in Toolbox on your unit.
echo [BUILD] Origin info.txt must match except for the skin.displayname value.
echo [BUILD] Output names keep your input label with one [CN_Dots]- prefix.
echo [BUILD] Firmware, variant and source skin will be matched against Projects.
echo [BUILD] Locating Python 3.9 or later...
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 goto python
py -3 -u "%~dp0build.py"
set "BUILD_EXIT=%ERRORLEVEL%"
goto result
:python
where python >nul 2>nul
if errorlevel 1 goto missing
python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>nul
if errorlevel 1 goto missing
python -u "%~dp0build.py"
set "BUILD_EXIT=%ERRORLEVEL%"
goto result
:missing
echo ERROR: Python 3.9 or later was not found. Install Python and run build.cmd again.
set "BUILD_EXIT=1"
:result
if not "%BUILD_EXIT%"=="0" goto failed
echo [BUILD] Build completed successfully. Check the selected skins above.
goto end
:failed
echo [BUILD] Build failed. Read the error above; do not install an older result by mistake.
:end
echo.
echo Press any key to close this window.
pause >nul
exit /b %BUILD_EXIT%
