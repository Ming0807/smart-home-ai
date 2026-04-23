@echo off
echo Killing Ollama GUI...
taskkill /f /im "ollama app.exe"

echo Killing Ollama Background...
taskkill /f /im ollama.exe

timeout /t 2

set OLLAMA_MODELS=D:\Ollama_Models

echo Starting Ollama Server...
start cmd /k ollama serve