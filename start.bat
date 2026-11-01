@echo off
rem Raspisaniye: backend + web UI bir serwerde, SQLite bilen (PostgreSQL gerek dal).
rem Iki gezek basyn: serwer bashlayar we brauzer acylyar. Serwer eyyam ishleyan bolsa, dine brauzer acylyar.
rem Kitaphanalary taze den gurnamak ucin: start.bat --install
title Raspisaniye serweri
cd /d "%~dp0backend"

curl -s -o nul http://127.0.0.1:8000/health && (
  start http://localhost:8000
  exit /b 0
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
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe -m app.seed --if-empty

rem Serwer tayyar bolanda brauzeri acmak
start "" /min cmd /c "for /l %%i in (1,1,60) do (curl -s -o nul http://127.0.0.1:8000/health && (start http://localhost:8000 & exit) || timeout /t 1 >nul)"

echo.
echo Raspisaniye ishleyar: http://localhost:8000
echo Bu penjireni yapsanyz serwer duryar.
echo.
.venv\Scripts\uvicorn.exe app.main:app --port 8000
