@echo off
setlocal

echo Killing Ollama GUI...
taskkill /f /im "ollama app.exe" 2>nul

echo Killing Ollama Background...
taskkill /f /im ollama.exe 2>nul

timeout /t 2

set "OLLAMA_MODELS=D:\Ollama_Models"
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"

if not exist "%OLLAMA_EXE%" (
    set "OLLAMA_EXE=%LOCALAPPDATA%\Ollama\ollama.exe"
)

if not exist "%OLLAMA_EXE%" (
    set "OLLAMA_EXE=%ProgramFiles%\Ollama\ollama.exe"
)

if not exist "%OLLAMA_EXE%" (
    set "OLLAMA_EXE=ollama"
)

echo Starting Ollama Server...
echo Using %OLLAMA_EXE%
start "Ollama Serve" cmd /k ""%OLLAMA_EXE%" serve"
