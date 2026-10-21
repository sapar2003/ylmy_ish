@echo off
rem Raspisaniye: backend + web UI bir serwerde, SQLite bilen (PostgreSQL gerek dal).
cd /d "%~dp0backend"
if not exist .venv (
  py -3 -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q --upgrade pip
pip install -q -e .
set DATABASE_URL=sqlite:///./raspisaniye.db
set STATIC_DIR=%~dp0frontend\build\web
alembic upgrade head
python -m app.seed --if-empty
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8000"
uvicorn app.main:app --port 8000
