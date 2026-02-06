# Podbridge

A podcast content pipeline dashboard. Bridges audio content to articles, video, and social formats through an API-first architecture with a React dashboard for real-time monitoring.

---

## Overview

Podbridge coordinates the transformation of podcast audio into multiple output formats — written articles, video audiograms, and social media posts. The dashboard provides a unified view of pipeline stages, queue management, and processing status.

### Key Features

- **API-first architecture** — FastAPI backend enables multiple interfaces
- **Real-time monitoring** — React dashboard with WebSocket live updates
- **Multi-model routing** — Cost-optimized LLM selection (Gemini, GPT-4o, Claude)
- **Batch processing** — Drag-and-drop upload or folder watching
- **Pipeline stages** — Configurable processing pipeline per episode

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                      PODBRIDGE                        │
├──────────────────────────────────────────────────────┤
│                                                       │
│   ┌──────────────┐    ┌──────────────┐               │
│   │     Web      │    │   Transcript │               │
│   │  Dashboard   │    │    Watcher   │               │
│   │    :3000     │    │              │               │
│   └──────┬───────┘    └──────┬───────┘               │
│          │                   │                        │
│          └───────────┬───────┘                        │
│                      │                                │
│                      ▼                                │
│   ┌──────────────────────────────────────────────┐   │
│   │           FastAPI Server (:8000)              │   │
│   │   /api/queue  /api/jobs  /api/ws/jobs         │   │
│   └───────────────────┬──────────────────────────┘   │
│                       │                               │
│        ┌──────────────┼──────────────┐               │
│        │              │              │                │
│   ┌────▼────┐   ┌─────▼─────┐  ┌────▼─────┐        │
│   │ Worker  │   │  SQLite   │  │ LLM API  │        │
│   │ (Queue) │   │    DB     │  │          │        │
│   └─────────┘   └───────────┘  └──────────┘        │
│                                                       │
└──────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+ (for web dashboard)
- OpenRouter API key

### Installation

```bash
git clone https://github.com/MarkOnFire/podbridge.git
cd podbridge

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd web && npm install && cd ..

cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

./venv/bin/alembic upgrade head
```

### Running

```bash
# Start API server
uvicorn api.main:app --reload

# Start web dashboard (separate terminal)
cd web && npm run dev
```

### Access Points

| URL | Description |
|-----|-------------|
| http://localhost:8000 | API server |
| http://localhost:3000 | Web dashboard |

---

## Dashboard

The React-based dashboard provides real-time monitoring:

- **Pipeline** — Queue stats, recent runs, system health
- **Ready for Review** — Items awaiting human review
- **Queue** — Run list with filtering, search, bulk actions
- **Episodes** — Browse completed outputs by episode
- **Settings** — Agent configuration, routing rules
- **System** — API health, worker status, log viewer

---

## Pipeline Stages

Each episode run passes through configurable stages:

1. **Analyst** — Extracts key themes, quotes, and metadata from transcript
2. **SEO Specialist** — Generates keyword analysis and search optimization
3. **Formatter** — Produces final title, description, and tags
4. **Timestamp** — (Optional) Creates chapter markers

### Cost Optimization

| Task | Default Model | Fallback |
|------|--------------|----------|
| Analysis | gemini-2.0-flash | gpt-4o-mini |
| SEO | gemini-2.0-flash | gpt-4o-mini |
| Formatting | gpt-4o-mini | gemini-2.0-flash |

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/queue/` | List runs with pagination/filtering |
| GET | `/api/queue/stats` | Queue statistics |
| POST | `/api/queue` | Create new run |
| GET | `/api/jobs/{id}` | Get run details |
| PATCH | `/api/jobs/{id}` | Update run |
| DELETE | `/api/jobs/{id}` | Delete run |
| POST | `/api/upload/transcripts` | Bulk upload transcripts |
| WS | `/api/ws/jobs` | Real-time run updates |

---

## Part of podcast-publishing-suite

Podbridge is one component of the [podcast-publishing-suite](https://github.com/MarkOnFire/podcast-publishing-suite) ecosystem:

- `podcast-whisper-transcription` — Whisper-based transcription
- `prx-to-ghost-publisher` — PRX feed to Ghost CMS
- `audiogram-tools` — Animated audiogram generation
- `robo-social` — Social media distribution

---

## Development

See [CLAUDE.md](CLAUDE.md) for development guidelines and architecture details.

```bash
# Run tests
pytest

# TypeScript build check
cd web && npm run build
```

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | API key for LLM requests |
| `DATABASE_URL` | No | SQLite path (default: `./dashboard.db`) |

---

## License

MIT
