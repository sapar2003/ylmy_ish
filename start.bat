@echo off
rem Raspisaniye: backend + web UI bir serwerde, SQLite bilen (PostgreSQL gerek dal).
rem Iki gezek basyn: serwer bashlayar we brauzer acylyar. Serwer eyyam ishleyan bolsa, dine brauzer acylyar.
rem Kitaphanalary taze den gurnamak ucin: start.bat --install
rem PORT: 8000 "Gijeki barlag" programmasy bilen eyelenen, shonun ucin Raspisaniye 8001-de ishleyar.
set PORT=8001
title Raspisaniye serweri (port %PORT%)
cd /d "%~dp0backend"

rem Portda Raspisaniye ishleyan bolsa (basga programma dal!), dine brauzeri acyarys.
curl -s -m 3 http://127.0.0.1:%PORT%/health 2>nul | findstr /c:"raspisaniye" >nul && (
  start "" http://localhost:%PORT%
  exit /b 0
)
rem Port basga programma bilen eyelenen bolsa duydurys.
curl -s -m 3 -o nul http://127.0.0.1:%PORT%/health 2>nul && (
  echo %PORT% porty basga programma bilen eyelenen. start.bat icinde PORT bahasyny uytgedin.
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Ilkinji gezek: Python gurshawy doredilyar we kitaphanalar gurnalyar, garashyn...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  set INSTALL=1
)
if /i "%~1"=="--install" set INSTALL=1
if defined INSTALL (
  .venv\Scripts\python.exe -m pip install -q --upgrade pip
  .venv\Scripts\python.exe -m pip install -q -e .
)

set DATABASE_URL=sqlite:///./raspisaniye.db
set STATIC_DIR=%~dp0frontend\build\web
rem Mugallym app-ynyn web gornushi: http://shu-kompyuter:%PORT%/m/
set MOBILE_DIR=%~dp0mobile\build\web
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe -m app.seed --if-empty

rem Serwer tayyar bolanda brauzeri acmak (diňe Raspisaniye jogap berende)
start "" /min cmd /c "for /l %%i in (1,1,90) do (curl -s -m 2 http://127.0.0.1:%PORT%/health 2>nul | findstr /c:raspisaniye >nul && (start http://localhost:%PORT% & exit) || timeout /t 1 >nul)"

echo.
echo Raspisaniye ishleyar: http://localhost:%PORT%
echo Telefondan (shol bir Wi-Fi): http://^<shu kompyuterin IP salgysy^>:%PORT%/m/
echo Bu penjireni yapsanyz serwer duryar.
echo.
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port %PORT% >> server.log 2>&1
