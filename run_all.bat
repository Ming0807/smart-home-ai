@echo off
call start_ollama_clean.bat
timeout /t 5
start cmd /k python warmup.py
start cmd /k uvicorn server.app:app --host 0.0.0.0 --port 8000
start http://localhost:8000