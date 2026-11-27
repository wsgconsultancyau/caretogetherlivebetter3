@echo off
rem Double-click this file to start CareTogetherLiveBetter.
rem The first time, it sets everything up (this takes a few minutes).
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Setting up for the first time...
  py -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
streamlit run app.py
pause
