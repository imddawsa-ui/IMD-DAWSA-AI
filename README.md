# IMD DAWSA AI

Privacy-first AI assistant foundation for Windows 11, 8 GB RAM and CPU-only hardware. Milestone 0.1 provides a FastAPI web interface connected to a local Ollama model.

## Current features
- Arabic/English web interface
- Local Ollama chat; no cloud provider enabled
- Health/readiness endpoints
- SQLite conversation storage
- Optional API access token
- Windows setup scripts and basic test

This is a foundation, not a frontier-scale model or the completed social/marketplace Super App.

## Requirements
Python 3.11+ and Ollama. For an 8 GB CPU-only PC, start with qwen2.5:3b and expect slower responses than on a GPU.

## Windows setup
1. Install Python and Ollama.
2. Copy .env.example to .env and review it.
3. Run install_windows.bat.
4. Run pull_model.bat once (model download needs internet).
5. Run start_windows.bat and open http://127.0.0.1:8000.

After the model is downloaded, local chat can run offline.

## API
GET /api/health, GET /api/readiness, POST /api/chat with JSON {"message":"Hello"}.

See SECURITY.md and ROADMAP.md before deploying or adding modules.
