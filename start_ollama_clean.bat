@echo off
echo Killing Ollama GUI...
taskkill /f /im "ollama app.exe" 2>nul

echo Killing Ollama Background...
taskkill /f /im ollama.exe 2>nul

timeout /t 2

set "OLLAMA_MODELS=D:\Ollama_Models"

echo Starting Ollama Server...
start "Ollama Serve" cmd /k "set OLLAMA_MODELS=D:\Ollama_Models && ollama serve"
