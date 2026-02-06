# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Repository Purpose

Podbridge — a podcast content pipeline dashboard. Bridges podcast audio content to articles, video, and social formats through an API-first architecture with a React dashboard for monitoring.

Part of the [podcast-publishing-suite](https://github.com/MarkOnFire/podcast-publishing-suite) ecosystem.

## Key Commands

### Development

```bash
# Start API server
uvicorn api.main:app --reload

# Run tests
pytest

# Start web dev server
cd web && npm run dev
```

### Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Architecture

```
podbridge/
├── api/                        # FastAPI application
│   ├── main.py                 # App entry point
│   ├── routers/                # API endpoints
│   ├── models/                 # Pydantic schemas
│   └── services/               # Business logic
├── web/                        # React dashboard (Vite + TypeScript)
│   └── src/
│       ├── components/         # Shared UI components
│       ├── pages/              # Route pages
│       └── hooks/              # Custom React hooks (WebSocket, etc.)
├── config/                     # Configuration files
├── tests/                      # Test suite
├── docs/                       # Documentation
└── planning/                   # Design reference docs
```

## Pipeline Concepts

The dashboard coordinates pipeline stages for podcast content:

| Internal Model | Pipeline Concept |
|---------------|-----------------|
| Job | Episode Run |
| Job Phase | Pipeline Stage |
| Project | Episode |
| Worker | Stage Runner |

**Note:** Internal model names (Job, Phase, etc.) are retained from the original codebase. The UI uses the pipeline terminology. A deeper rename is planned for a future session.

## Sibling Submodules

This project is part of the podcast-publishing-suite:
- `podcast-whisper-transcription` — Whisper-based transcription
- `prx-to-ghost-publisher` — PRX feed to Ghost CMS
- `audiogram-tools` — Animated audiogram generation
- `robo-social` — Social media distribution

## Notes for Claude Code

1. **Run tests** before marking work complete
2. **Don't break the API contract** — OpenAPI spec is the source of truth
3. **Surface-layer naming** uses Podbridge/pipeline terminology; internal models use legacy names
