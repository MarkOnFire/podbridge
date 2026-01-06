# Editorial Assistant v4.0 - Design & Vision Document

**Goal:** Build on v3.0's reliable local infrastructure to enable remote deployment, embedded chat experiences, multi-user collaboration, and production-grade hardening.

**Status:** Planning document - features tabled from v3.0 for future implementation.

**Last Updated:** January 2026

---

## Executive Summary

Editorial Assistant v4.0 represents the transition from a **single-user local tool** to a **production-ready, remotely-accessible service**. While v3.0 achieved the core goals of database-backed processing, web dashboard monitoring, and MCP-based copy editing via Claude Desktop, several features were explicitly deferred to maintain scope discipline.

This document captures those deferred features as the foundation for v4.0 planning.

---

## Features Deferred from v3.0

### 1. Embedded Web Chat (High Priority)

**Original Scope:** Build a chat interface directly into the web dashboard for copy-editor workflow, eliminating the need for Claude Desktop.

**Why Deferred:** Significant complexity - WebSocket real-time messaging, session persistence, artifact rendering. v3.0 uses Claude Desktop with MCP tools as the copy-editor interface instead.

**v4.0 Requirements:**

| Component | Description |
|-----------|-------------|
| **WebSocket messaging** | Real-time bidirectional communication with LLM backend |
| **Session persistence** | Chat history stored per project, resumable conversations |
| **File attachments** | Upload screenshots, draft copy, reference documents |
| **Artifact rendering** | Inline display of revision documents, brainstorming output |
| **Context auto-loading** | Automatically inject project context (transcript, SST metadata, brainstorming) |
| **Multi-turn conversations** | Maintain coherent conversation state across edits |

**Technical Considerations:**
- WebSocket endpoint for chat messages (separate from job status WebSocket)
- LLM backend abstraction for chat (OpenRouter, direct APIs)
- Conversation context window management
- Rate limiting and cost controls for interactive chat
- Mobile-responsive chat UI

**Estimated Effort:** 3-4 sprints

---

### 2. Collaborative Document Editing (Future Vision)

**Original Scope:** Integration with Google Docs or similar, where agent writes to a live document, user edits directly, agent reviews changes - true back-and-forth collaboration like working with a human editor.

**Why Deferred:** This is a significant re-architecture, not an incremental upgrade. Would require real-time sync, potentially CRDTs/OTs, robust auth, and fundamental changes to the data layer.

**v4.0 Exploration:**

| Approach | Complexity | Trade-offs |
|----------|------------|------------|
| **Google Docs API** | Medium | Requires Google auth, API quotas, formatting translation |
| **Notion API** | Medium | Requires Notion workspace, block-based editing model |
| **Custom CRDT editor** | Very High | Full control but massive development effort |
| **Etherpad integration** | Medium-High | Self-hosted option, real-time collaboration built-in |
| **Monaco/CodeMirror + Y.js** | High | In-browser collaborative editing with conflict resolution |

**Recommended v4.0 Approach:**
1. Start with export-to-Google-Docs functionality (one-way push)
2. Later add import-from-Google-Docs for round-trip editing
3. Full real-time collaboration is v5.0 territory

**Estimated Effort:** 2-3 sprints for one-way export; 5+ sprints for full collaboration

---

### 3. Remote Deployment & Production Hardening

**Original Scope:** Enable running Editorial Assistant on a remote server (Proxmox, cloud VPS, or PBSWI Engineering infrastructure).

**Why Deferred:** v3.0 focused on local reliability and cost optimization. Remote deployment requires auth, security hardening, and observability infrastructure.

**v4.0 Requirements:**

#### 3.1 Server Infrastructure

| Component | Description |
|-----------|-------------|
| **ASGI server** | Gunicorn + Uvicorn for production-grade request handling |
| **Process management** | systemd or supervisor for service lifecycle |
| **Reverse proxy** | nginx or Caddy for SSL termination, static files |
| **Database** | SQLite for single-server; PostgreSQL option for scale |

#### 3.2 Security

| Component | Description |
|-----------|-------------|
| **Authentication** | Token-based API auth (API keys or JWT) |
| **Authorization** | Role-based access (admin, editor, viewer) |
| **Rate limiting** | Per-user/IP request limits |
| **Audit logging** | Track all authenticated actions |
| **Secret management** | Environment variables, Vault integration option |

#### 3.3 Deployment Options

| Option | Cost | Requirements |
|--------|------|--------------|
| **A. Proxmox (Self-Hosted)** | ~$0/month (electricity) | Docker packaging, remote MCP transport, basic auth |
| **B. Cloud VPS** | $5-25/month + LLM costs | Same as A, plus domain/SSL, hardened security |
| **C. PBSWI Engineering** | $0 (absorbed by station) | Rock-solid reliability, predictable cost, easy integration, minimal maintenance, clear documentation, proven track record |

**PBSWI Engineering Integration Requirements:**
- Months of stable local production use
- Predictable LLM spend with cost caps and budget alerts
- API for integration with existing workflows
- Self-healing with comprehensive logging
- Complete handoff documentation

**Estimated Effort:** 2-3 sprints

---

### 4. Authentication & Multi-User Support

**Original Scope:** Separate queues/projects per user, shared project review, approval workflows.

**Why Deferred:** v3.0 is explicitly local-only, single-user. Auth adds complexity and v3.0 didn't need it.

**v4.0 Requirements:**

| Feature | Description |
|---------|-------------|
| **User accounts** | Registration, login, password management |
| **Project ownership** | Projects belong to specific users |
| **Sharing** | Share project read/write access with other users |
| **Workspaces/Teams** | Group users into organizations |
| **Approval workflows** | Request review, approve/reject changes |
| **Activity feeds** | See what teammates have done |

**Authentication Options:**
1. Simple API keys (minimal, for remote access)
2. JWT with refresh tokens (standard web auth)
3. OAuth integration (Google, Microsoft SSO)
4. LDAP/Active Directory (enterprise)

**Database Schema Additions:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'editor',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_access (
    project_id INTEGER REFERENCES jobs(id),
    user_id INTEGER REFERENCES users(id),
    permission TEXT CHECK (permission IN ('owner', 'editor', 'viewer')),
    PRIMARY KEY (project_id, user_id)
);

CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id)
);

CREATE TABLE team_members (
    team_id INTEGER REFERENCES teams(id),
    user_id INTEGER REFERENCES users(id),
    role TEXT DEFAULT 'member',
    PRIMARY KEY (team_id, user_id)
);
```

**Estimated Effort:** 2-3 sprints

---

### 5. Mobile Application

**Original Scope:** Push notifications and quick status checks from mobile devices.

**Why Deferred:** Web dashboard is responsive and works on mobile. Native app adds significant development/maintenance burden.

**v4.0 Options:**

| Approach | Pros | Cons |
|----------|------|------|
| **PWA (Progressive Web App)** | No app store, shares web codebase | Limited push notification support on iOS |
| **React Native** | Cross-platform, shared business logic | New codebase, app store management |
| **Capacitor (Ionic)** | Wrap existing React app | Performance trade-offs, native bridge complexity |

**Recommended v4.0 Approach:**
1. Enhance web dashboard for mobile-first responsive design
2. Add PWA manifest and service worker for offline capability
3. Implement web push notifications (Chrome/Android)
4. Defer native app to v5.0 based on user demand

**Core Mobile Features:**
- Queue status at a glance
- Push notifications for job completion/failure
- Quick approve/reject for review workflows
- View project outputs

**Estimated Effort:** 1-2 sprints for PWA enhancements

---

### 6. Plugin System

**Original Scope:** Custom agents and external integrations as plugins.

**Why Deferred:** Core agent system still evolving. Plugin architecture should stabilize after v3.0 patterns mature.

**v4.0 Design:**

#### 6.1 Plugin Types

| Type | Description | Example |
|------|-------------|---------|
| **Agent plugins** | Custom processing phases | "social-media-agent" for TikTok/Instagram copy |
| **Output formatters** | Transform outputs to different formats | Export to CMS-specific XML |
| **Integrations** | Connect to external services | Slack notifications, Trello cards |
| **Model providers** | Add new LLM backends | Local Ollama, Azure OpenAI |

#### 6.2 Plugin API

```python
# Plugin manifest (plugin.yaml)
name: social-media-agent
version: 1.0.0
author: Your Name
type: agent
hooks:
  - phase: after_seo
    handler: generate_social_copy

# Plugin implementation
from editorial_assistant.plugins import AgentPlugin

class SocialMediaAgent(AgentPlugin):
    def process(self, context: ProjectContext) -> PluginResult:
        # Generate TikTok/Instagram/Twitter copy from transcript
        ...
```

#### 6.3 Plugin Registry

- Local plugins in `plugins/` directory
- Remote plugin registry for sharing (future)
- Plugin enable/disable in settings
- Plugin-specific configuration

**Estimated Effort:** 2-3 sprints

---

### 7. Self-Hosted Docker Deployment

**Original Scope:** Docker Compose for easy deployment anywhere.

**Why Deferred:** Local development prioritized. Docker adds deployment complexity that wasn't needed for v3.0.

**v4.0 Docker Stack:**

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/dashboard.db
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./data:/app/data
      - ./OUTPUT:/app/OUTPUT
      - ./transcripts:/app/transcripts

  worker:
    build: .
    command: python run_worker.py
    environment:
      - DATABASE_URL=sqlite:///data/dashboard.db
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./data:/app/data
      - ./OUTPUT:/app/OUTPUT
      - ./transcripts:/app/transcripts
    depends_on:
      - api

  web:
    build: ./web
    ports:
      - "3000:80"
    depends_on:
      - api

  # Optional: MCP server for Claude Desktop remote access
  mcp:
    build: ./mcp_server
    ports:
      - "3001:3001"
    depends_on:
      - api
```

**Additional Docker Considerations:**
- Multi-stage builds for smaller images
- Health checks for all services
- Volume management for persistent data
- Log aggregation (optional: Loki/Grafana stack)
- Backup strategy for SQLite database

**Estimated Effort:** 1-2 sprints

---

### 8. Observability: Langfuse Integration

**Original Scope:** Production-grade LLM observability for remote deployment.

**Why Deferred:** CLI-Agent usage (free tier) doesn't need precise tracking. v3.0's manifest-based cost tracking is sufficient for local use.

**v4.0 Rationale:**
- Remote deployment uses OpenRouter exclusively (no CLI-Agent)
- All costs are 1:1 metered, precise tracking essential
- Langfuse provides traces, cost analysis, prompt versioning

**Implementation:**

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# In LLM client
trace = langfuse.trace(
    name="editorial-assistant-job",
    metadata={"job_id": job.id, "phase": phase}
)

span = trace.span(
    name=f"llm-{phase}",
    input={"prompt": prompt},
    output={"response": response},
    model=model_name,
    usage={"input": input_tokens, "output": output_tokens}
)
```

**Self-Hosted Option:**
- Run Langfuse locally for PBSWI Engineering deployment
- Docker Compose addition for langfuse service
- No external data dependency

**Estimated Effort:** 1 sprint

---

### 9. Large Transcript Parallel Processing

**Original Scope:** Chunk large transcripts and process in parallel for faster throughput.

**Status in v3.0:** Partially addressed with tier escalation for long-form content. Full chunking/parallelization deferred.

**v4.0 Full Implementation:**

| Feature | Description |
|---------|-------------|
| **Size estimation** | Calculate transcript token count before processing |
| **Chunking strategy** | Split at natural boundaries (paragraph, speaker change) |
| **Overlap handling** | Overlap chunks to maintain context, dedupe on merge |
| **Parallel execution** | Process chunks concurrently (configurable max workers) |
| **Result merging** | Intelligent merge with overlap deduplication |
| **Progress tracking** | Per-chunk progress in job phases |

**Chunking Configuration:**
```python
CHUNK_CONFIG = {
    "threshold_chars": 100_000,      # When to start chunking
    "chunk_size": 50_000,            # Target size per chunk
    "overlap_chars": 2_000,          # Overlap for context continuity
    "max_parallel": 3,               # Max concurrent LLM calls
    "merge_strategy": "dedupe_overlap",
    "split_boundaries": ["speaker_change", "paragraph", "sentence"]
}
```

**Estimated Effort:** 2 sprints

---

### 10. Auto-Ingest from Caption Sources

**Original Scope:** Automatically ingest transcripts from PBS Wisconsin's caption server (mmingest.pbswi.wisc.edu).

**Why Deferred:** Requires remote deployment, filtering logic, and integration approval.

**v4.0 Requirements:**

| Component | Description |
|-----------|-------------|
| **Polling or webhook** | Detect new caption files |
| **Filtering** | Show whitelist, keyword filters, date filters |
| **Approval queue** | Optional human review before processing |
| **Deduplication** | Don't re-process already-handled videos |
| **Volume management** | Rate limiting to control LLM costs |

**Filtering Strategies:**
1. **Show whitelist** - Auto-process specific programs only
2. **Manual approval** - All new captions enter review queue
3. **Keyword/date filters** - Process based on metadata rules
4. **Hybrid** - Whitelist + manual for new shows

**Estimated Volume:**
- 40-200 videos/month
- $0.03-0.15 per video
- $4-20/month LLM cost if processing everything
- Filtering significantly reduces costs

**Estimated Effort:** 2 sprints

---

## Priority Matrix

| Feature | User Value | Technical Risk | Effort | Recommended Priority |
|---------|------------|----------------|--------|---------------------|
| Embedded Web Chat | High | Medium | High | P1 - Core v4.0 |
| Remote Deployment | High | Medium | Medium | P1 - Core v4.0 |
| Authentication | Medium | Low | Medium | P1 - Required for remote |
| Docker Deployment | Medium | Low | Low | P2 - Enables adoption |
| Langfuse Observability | Medium | Low | Low | P2 - Operational need |
| Mobile PWA | Medium | Low | Low | P3 - Nice to have |
| Plugin System | Medium | Medium | Medium | P3 - Ecosystem growth |
| Collaborative Editing | High | Very High | Very High | P4 - v5.0 candidate |
| Large Transcript Chunking | Low | Medium | Medium | P4 - Edge case |
| Auto-Ingest | Low | Medium | Medium | P4 - PBSWI-specific |

---

## Recommended v4.0 Roadmap

### Phase 1: Remote Foundation (2-3 sprints)
1. Docker containerization
2. ASGI server setup (Gunicorn + Uvicorn)
3. Basic API authentication (token-based)
4. Langfuse integration

### Phase 2: Embedded Chat (3-4 sprints)
1. WebSocket chat endpoint
2. Chat session persistence
3. LLM backend integration for chat
4. React chat UI component
5. Project context injection

### Phase 3: Multi-User (2-3 sprints)
1. User accounts and auth
2. Project ownership/sharing
3. Activity feeds
4. Basic approval workflows

### Phase 4: Polish & Ecosystem (2 sprints)
1. PWA enhancements
2. Plugin system foundation
3. Documentation and onboarding
4. Performance optimization

---

## Dependencies and Prerequisites

Before starting v4.0 development:

1. **v3.0 must be stable** - Months of local production use without major issues
2. **Cost tracking validated** - Predictable LLM spend patterns established
3. **User workflows documented** - Clear understanding of how the tool is actually used
4. **API contract frozen** - v3.0 API shouldn't have breaking changes during v4.0

---

## Open Questions for v4.0

| Question | Options | Recommendation |
|----------|---------|----------------|
| **Chat backend** | OpenRouter only vs. direct API support | OpenRouter for simplicity, direct APIs for cost optimization |
| **Database** | SQLite vs. PostgreSQL | PostgreSQL for multi-user, SQLite for single-user deployments |
| **Auth provider** | Custom vs. Auth0 vs. Clerk | Clerk for fastest time-to-market |
| **Chat persistence** | Local DB vs. external service | Local DB with export option |
| **Mobile strategy** | PWA vs. native | PWA first, evaluate native demand |

---

## Success Metrics for v4.0

| Metric | Target |
|--------|--------|
| Remote deployment uptime | 99.5% |
| Chat response latency | <3s average |
| Authentication setup time | <10 minutes |
| Cost tracking accuracy | Within 2% of actual |
| Mobile experience score | Lighthouse >80 |
| New user onboarding | <30 minutes to first edit |

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-06 | Claude Code | Initial creation from v3.0 deferred features |
