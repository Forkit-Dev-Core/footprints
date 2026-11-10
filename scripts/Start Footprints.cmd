@echo off
setlocal
pushd "%~dp0" || exit /b 1
echo Open http://127.0.0.1:8765/footprints/ once the server starts.
echo Press Ctrl+C in this window to stop Footprints.
"runtime\python.exe" -B "app\serve.py"
set "FOOTPRINTS_EXIT=%ERRORLEVEL%"
if not "%FOOTPRINTS_EXIT%"=="0" pause
popd
exit /b %FOOTPRINTS_EXIT%
