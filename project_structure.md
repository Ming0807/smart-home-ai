# Project Structure

```text
smart-home-ai
|-- .gitignore
|-- agent_rules.md
|-- ai_smart_home_thai_assistant_project.md
|-- data
|   `-- .gitkeep
|-- development_rules_best_practices_performance.md
|-- docs
|   `-- .gitkeep
|-- esp32
|   |-- api_client.py
|   |-- config.py
|   |-- main.py
|   |-- sensor_reader.py
|   `-- wifi_manager.py
|-- next_tasks.md
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
|   |   |-- esp32.py
|   |   `-- health.py
|   |-- routes
|   |   |-- __init__.py
|   |   |-- chat.py
|   |   |-- esp32.py
|   |   `-- health.py
|   |-- services
|   |   |-- __init__.py
|   |   |-- device_control.py
|   |   |-- esp32_manager.py
|   |   |-- health.py
|   |   |-- intent_router.py
|   |   |-- llm_manager.py
|   |   |-- sensor_manager.py
|   |   `-- weather_service.py
|   `-- utils
|       `-- __init__.py
|-- start_ollama_clean.bat
|-- static
|   |-- reply.mp3
|   |-- reply_321d0393ad4043c1af3587403764fdb0.mp3
|   |-- reply_5a698f673a684b258269e875ade49cb4.mp3
|   |-- reply_a6bc538318a643bdbf89853fce31acc2.mp3
|   `-- reply_d6d6b03c094e409386407408a51d9c30.mp3
|-- task_breakdown_master_plan.md
`-- webui
    `-- .gitkeep
```

Excluded from this tree:
- `.git/`
- `venv/`
- `__pycache__/`
