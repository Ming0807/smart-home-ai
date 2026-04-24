# Project Structure

```text
smart-home-ai
|-- .gitignore
|-- AGENT_RULES.md
|-- AI Smart Home Thai Assistant Project.md
|-- data
|   `-- .gitkeep
|-- Development Rules Best Practices Performance.md
|-- docs
|   `-- .gitkeep
|-- esp32
|   |-- api_client.py
|   |-- config.py
|   |-- main.py
|   |-- sensor_reader.py
|   `-- wifi_manager.py
|-- NEXT_TASKS.md
|-- project_structure.md
|-- prompts
|   `-- system_prompt.txt
|-- requirements.txt
|-- run_all.bat
|-- server
|   |-- __init__.py
|   |-- app.py
|   |-- config.py
|   |-- models
|   |   |-- __init__.py
|   |   |-- chat.py
|   |   |-- dashboard.py
|   |   |-- esp32.py
|   |   |-- health.py
|   |   `-- voice.py
|   |-- routes
|   |   |-- __init__.py
|   |   |-- chat.py
|   |   |-- dashboard.py
|   |   |-- esp32.py
|   |   |-- health.py
|   |   `-- voice.py
|   |-- services
|   |   |-- __init__.py
|   |   |-- device_control.py
|   |   |-- esp32_manager.py
|   |   |-- health.py
|   |   |-- intent_router.py
|   |   |-- llm_manager.py
|   |   |-- sensor_manager.py
|   |   |-- system_status_service.py
|   |   |-- tts_service.py
|   |   `-- weather_service.py
|   `-- utils
|       |-- __init__.py
|       `-- observability.py
|-- start_ollama_clean.bat
|-- static
|-- Task Breakdown Master Plan.md
`-- webui
    |-- app.js
    |-- index.html
    `-- style.css
```

Excluded from this tree:
- `.git/`
- `venv/`
- `.venv/`
- `__pycache__/`
- `.phase*_deps/`
- generated audio files in `static/`
