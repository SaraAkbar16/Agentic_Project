# AgenticAI Project | PixFrame AI

An end-to-end **AI-powered animated video generation system** that converts a single prompt into a complete short film using modular LLM agents.

---
<img width="1908" height="788" alt="image" src="https://github.com/user-attachments/assets/594629b7-a4b0-4b4d-9780-13de00eb24d0" />
<img width="1916" height="838" alt="image" src="https://github.com/user-attachments/assets/c3f97515-5c2f-4643-9fd8-21cd8d942ab1" />
<img width="1914" height="916" alt="Screenshot 2026-05-03 205943" src="https://github.com/user-attachments/assets/546035ef-3a5a-46c6-b0f5-fc35929db7a0" />

## Overview

This project implements a **multi-phase agentic pipeline**:

1. **Story & Script Generation** — Prompt → structured story, scenes, characters
2. **Audio Generation** — Dialogue + character voices + background music
3. **Video Composition** — Scene visuals + animation + A/V sync → final video
4. **Web Interface** — UI to run pipeline, track progress, and preview output
5. **Edit Agent** — Natural language edits with versioning and undo support

---

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | FastAPI |
| Frontend | Next.js / React |
| Agents | LangGraph / LLM APIs |
| Audio | ElevenLabs / Coqui / Bark (TTS) |
| Video | FFmpeg / MoviePy |
| Image Generation | Stable Diffusion / APIs |
| State Management | JSON + version snapshots |

---

## Quick Start

### Backend

```bash
pip install -r requirements.txt
python -m backend.app
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Features

- Prompt → full animated video pipeline
- Scene-wise generation (modular phases)
- Real-time progress tracking (Phase 4)
- Phase-level re-run support
- Edit agent with:
  - Natural language edits
  - Targeted regeneration (audio / video / script)
  - Version history (v1, v2, v3…)
  - Undo / revert system

---

## Project Structure

```
agents/          # Phase-wise agents (story, audio, video, edit)
backend/         # API + orchestration layer
frontend/        # Web UI
mcp/             # Tooling layer (LLM, audio, video, etc.)
state_manager/   # Versioning + snapshots
data/            # Outputs and assets
shared/          # Schemas and utilities
```

---

## Notes

- All phases communicate via a shared JSON state schema
- Each phase is modular and independently testable
- Every run/edit creates a new version snapshot

