@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo InfluenceSignal needs Python 3.10 or newer.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating InfluenceSignal's private Python environment...
  py -m venv .venv
)
".venv\Scripts\python.exe" -c "import streamlit, defusedxml, yaml, openpyxl, plotly" >nul 2>&1
if errorlevel 1 (
  echo Installing InfluenceSignal's open-source packages...
  ".venv\Scripts\python.exe" -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
if "%INFLUENCESIGNAL_PORT%"=="" set INFLUENCESIGNAL_PORT=8590
echo Starting InfluenceSignal at http://127.0.0.1:%INFLUENCESIGNAL_PORT% ...
echo Your data is saved in the "data" folder next to this file. The first start loads the fictional demo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=false --server.address=127.0.0.1 --server.port=%INFLUENCESIGNAL_PORT% --server.maxUploadSize=20 --server.fileWatcherType=none --browser.gatherUsageStats=false
if errorlevel 1 pause
