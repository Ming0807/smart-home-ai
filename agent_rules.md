# AGENT_RULES

## 1. Purpose
This file defines mandatory working rules for any AI coding agent (Codex / GPT / autonomous assistant) contributing to this project.

The goal is to maximize speed, code quality, maintainability, and project stability.

---

## 2. Source of Truth (Must Read First)

Before making any change, always read relevant project documentation in root folder.

Priority order:
1. AI Smart Home Thai Assistant Project.md
2. Development Rules Best Practices Performance.md
3. Task Breakdown Master Plan.md
4. Prompts Intents Ai Brain.md
5. Full Tech Stack Setup Guide.md
6. Ollama Windows Special Setup.md

If docs conflict:
- newest implementation decision wins
- prefer practical implementation over theoretical design
- preserve working system stability

---

## 3. Mandatory Workflow

For every task:

1. Read relevant docs first
2. Inspect existing files before editing
3. Explain short implementation plan
4. Make minimal safe changes
5. Preserve backward compatibility when possible
6. Validate syntax / imports / structure
7. Summarize changes clearly

Never skip step 1.

---

## 4. Scope Control Rules

Do only what is requested.

Do NOT:
- rewrite unrelated modules
- rename large structures unnecessarily
- change architecture without approval
- add dependencies unless justified
- break working APIs

If larger refactor is beneficial:
- propose it first
- wait for approval

---

## 5. Code Quality Standards

## Python
- Python 3.11+
- Use type hints
- Clear function names
- Small focused functions
- Prefer composition over giant classes
- Use docstrings where helpful

## FastAPI
- Keep routes thin
- Move logic into services/
- Use pydantic schemas
- Proper status codes

## ESP32 / MicroPython
- Keep loops lightweight
- Handle reconnects
- Avoid memory waste
- Use config file for pins / Wi-Fi

---

## 6. Architecture Rules

Use this structure unless instructed otherwise:

```text
routes/      API layer
services/    business logic
models/      schemas / db
utils/       helpers
prompts/     prompt files
esp32/       device code
webui/       frontend
docs/        markdown docs
```

Never place business logic directly in route handlers.

---

## 7. Performance Rules

This project prioritizes real-world responsiveness.

Always prefer:
- fast response time
- predictable behavior
- low RAM usage
- low CPU spikes
- stable demo performance

Rules:
- route simple commands before LLM
- keep prompts short
- keep context compact
- limit token output
- use caching when useful
- avoid blocking I/O
- prefer async for network tasks

---

## 8. LLM Integration Rules

Primary model:
- Typhoon 2 8B local

Fallback models:
- Gemma 2B / 4B

Rules:
- Do not assume cloud APIs unless enabled
- Support Ollama local mode first
- Respect OLLAMA_WINDOWS_SPECIAL_SETUP.md
- Keep prompts externalized when possible
- Prefer deterministic settings for demos

---

## 9. Safety / Reliability Rules

Always handle failures gracefully:
- model unavailable
- timeout
- API errors
- sensor offline
- ESP32 disconnected

Return useful fallback responses.
Never crash entire app because one dependency failed.

---

## 10. Database Rules

Default database: SQLite

Keep schema simple.
Do migrations carefully.
Never destroy user data without approval.

---

## 11. Frontend Rules

UI priorities:
1. Works reliably
2. Clear status visibility
3. Fast interactions
4. Then aesthetics

Include loading states where relevant.

---

## 12. Testing Rules

For meaningful changes, include tests or verification steps.

Minimum checks:
- imports valid
- syntax valid
- endpoint still runs
- no broken references

If changing logic:
- provide manual test steps

---

## 13. Git / Change Discipline

Prefer small commits.
Group related changes only.

Commit style examples:
- feat: add weather service
- fix: ollama timeout fallback
- perf: reduce chat latency
- refactor: split chat router logic

---

## 14. Communication Rules

When responding after coding:
Provide:
1. What changed
2. Why it changed
3. Files touched
4. Risks / notes
5. How to test

Be concise.

---

## 15. When Uncertain

If requirements are unclear:
- inspect docs
- inspect codebase
- choose safest minimal path
- state assumptions clearly

Do not invent complex features silently.

---

## 16. High Value Default Tasks

If asked “what next?” prioritize:
1. Core stability
2. Chat endpoint quality
3. ESP32 connectivity
4. Device control reliability
5. Weather / external APIs
6. Voice features
7. UI polish

---

## 17. Absolute Prohibitions

Never:
- delete large sections without request
- expose secrets
- hardcode API keys
- break config system
- replace local LLM path logic casually
- introduce giant dependencies unnecessarily

---

## 18. Golden Rule

Ship stable progress fast.
Reliable simple code beats clever fragile code.

