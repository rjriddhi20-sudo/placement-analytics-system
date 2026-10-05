@echo off
REM Double-click to set up (first time) and start the app on Windows.
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
