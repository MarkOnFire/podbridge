# Editorial Assistant v4.0 - Remote Deployment & Production Hardening

**Goal:** Transform the Editorial Assistant from a local development tool into a production-ready, remotely-accessible service that can run on VMs (home network, then station infrastructure).

**Status:** Planning document
**Last Updated:** January 2026

---

## Executive Summary

V4.0 focuses exclusively on **deployment, security, and operational stability**. All feature work has been moved to V3.5 (see `planning/DESIGN_3.5.md`). This document addresses the "where and how" of running the Editorial Assistant, not the "what it does."

**Core V4.0 Themes:**
1. **Remote Deployment** - Run on VMs beyond localhost
2. **Security Hardening** - Authentication, authorization, audit logging
3. **Containerization** - Docker for portable deployment
4. **Operational Stability** - Monitoring, alerting, backup/recovery
5. **Cost Analysis** - Cloud vs self-hosted decision framework
6. **Remote MCP Access** - Expose Cardigan as a Custom Connector for Claude web/mobile

---

## Part 1: Deployment Targets

### 1.1 Deployment Progression

| Phase | Target | Timeline | Purpose |
|-------|--------|----------|---------|
| **Phase A** | Home VM (Proxmox) | V4.0 initial | Validation in controlled environment |
| **Phase B** | Station infrastructure | V4.0+ | Production deployment for team use |
| **Phase C** | Cloud option | Future | Scalability or disaster recovery |

### 1.2 Home VM Deployment (Phase A)

**Environment:**
- Proxmox hypervisor on home network
- Ubuntu Server 22.04 LTS VM
- Cloudflare Tunnel for secure remote access
- SQLite database (single-user sufficient)

**Requirements:**
- Docker Compose for service orchestration
- Automatic startup on VM boot
- Log persistence and rotation
- Basic monitoring (healthchecks, disk space)

### 1.3 Station Infrastructure (Phase B)

**PBSWI Engineering Integration Requirements:**

| Requirement | Description |
|-------------|-------------|
| **Months of stable use** | Proven track record on home VM first |
| **Predictable LLM spend** | Cost caps, budget alerts, monthly projections |
| **API documentation** | OpenAPI spec for integration with existing workflows |
| **Self-healing** | Automatic recovery from transient failures |
| **Comprehensive logging** | Audit trail for all operations |
| **Handoff documentation** | Complete setup, operation, and troubleshooting guides |

---

## Part 2: Security Architecture

### 2.1 Authentication Options

| Method | Complexity | Use Case |
|--------|------------|----------|
| **Cloudflare Access** | Low | Email-based gate, no app changes |
| **API Keys** | Low | Programmatic access, simple tokens |
| **JWT with refresh** | Medium | Standard web auth, session management |
| **OAuth/SSO** | Medium-High | Google/Microsoft integration |
| **LDAP/AD** | High | Enterprise directory integration |

**Recommended Progression:**
1. **Phase A (Home VM):** Cloudflare Access only (email allowlist)
2. **Phase B (Station):** Add API keys for integration + optional SSO

### 2.2 Authorization Model

```sql
-- User accounts (Phase B+)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,  -- Null if OAuth-only
    role TEXT DEFAULT 'editor',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- Project access control
CREATE TABLE project_access (
    project_id INTEGER REFERENCES jobs(id),
    user_id INTEGER REFERENCES users(id),
    permission TEXT CHECK (permission IN ('owner', 'editor', 'viewer')),
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
);

-- Audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    details TEXT,  -- JSON
    ip_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Security Checklist

| Category | Item | Priority |
|----------|------|----------|
| **Network** | HTTPS only (SSL termination) | P0 |
| **Network** | Rate limiting (per-IP, per-user) | P1 |
| **Network** | Cloudflare WAF rules | P2 |
| **Auth** | Password hashing (bcrypt/argon2) | P0 |
| **Auth** | Session timeout (configurable) | P1 |
| **Auth** | Failed login lockout | P1 |
| **Data** | Encrypted secrets (env vars, not files) | P0 |
| **Data** | Database backup encryption | P1 |
| **Audit** | All auth events logged | P0 |
| **Audit** | All data modifications logged | P1 |

---

## Part 3: Docker Containerization

### 3.1 Service Architecture

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/dashboard.db
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - AIRTABLE_API_KEY=${AIRTABLE_API_KEY}
    volumes:
      - ./data:/app/data
      - ./OUTPUT:/app/OUTPUT
      - ./transcripts:/app/transcripts
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=sqlite:///data/dashboard.db
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./data:/app/data
      - ./OUTPUT:/app/OUTPUT
      - ./transcripts:/app/transcripts
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

  # Remote MCP server — see Part 9 for architecture details
  # Exposes Cardigan as a Streamable HTTP endpoint for Claude web/mobile
  mcp:
    build:
      context: ./mcp_server
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      - API_URL=http://api:8000
      - MCP_TRANSPORT=http          # Streamable HTTP (not stdio)
      - MCP_AUTH_MODE=cloudflare    # Rely on Cloudflare Access; upgrade to OAuth later
    depends_on:
      - api
    restart: unless-stopped
```

### 3.2 Dockerfile Examples

**API Service:**
```dockerfile
# Dockerfile.api
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api/ ./api/
COPY config/ ./config/
COPY claude-desktop-project/ ./claude-desktop-project/

# Create data directories
RUN mkdir -p /app/data /app/OUTPUT /app/transcripts

# Run with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Web Dashboard:**
```dockerfile
# web/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### 3.3 Production Considerations

| Consideration | Approach |
|---------------|----------|
| **Multi-stage builds** | Smaller images, faster deploys |
| **Non-root user** | Security best practice |
| **Health checks** | Automatic restart on failure |
| **Log aggregation** | stdout/stderr to Docker logging |
| **Secret management** | Docker secrets or env files |
| **Volume persistence** | Named volumes for data durability |

---

## Part 4: Cost Analysis - Cloud vs Self-Hosted

### 4.1 Cost Categories

| Category | Description |
|----------|-------------|
| **Compute** | CPU/memory for API, worker, web |
| **Storage** | Database, transcripts, outputs |
| **LLM API** | OpenRouter costs (same regardless of hosting) |
| **Bandwidth** | Egress for web dashboard, API calls |
| **Maintenance** | Time spent on updates, troubleshooting |

### 4.2 Self-Hosted Options

#### Option A: Home VM (Proxmox)

| Item | Monthly Cost | Notes |
|------|--------------|-------|
| Electricity | ~$5-10 | VM share of server power |
| Hardware depreciation | ~$10-20 | Amortized over 5 years |
| Internet bandwidth | $0 | Already paying for home internet |
| Cloudflare Tunnel | $0 | Free tier sufficient |
| Maintenance time | ~2 hrs/month | Updates, monitoring |
| **Total** | **~$15-30/month** | Plus your time |

**Pros:**
- Full control over hardware and data
- No per-request costs
- Learning opportunity

**Cons:**
- Dependent on home power/internet
- You're the on-call engineer
- Limited redundancy

#### Option B: Station Infrastructure

| Item | Monthly Cost | Notes |
|------|--------------|-------|
| VM allocation | $0 | Absorbed by station IT budget |
| IT support | $0 | Existing staff |
| Bandwidth | $0 | Station internet |
| Maintenance time | ~1 hr/month | IT handles infrastructure |
| **Total** | **~$0/month** | Requires handoff readiness |

**Pros:**
- Professional infrastructure
- IT support available
- Reliable power/network
- Closer to production users

**Cons:**
- Requires months of stable operation first
- Must meet engineering standards
- Less experimentation freedom

### 4.3 Cloud Hosting Options

#### Option C: AWS EC2/ECS

| Item | Monthly Cost | Notes |
|------|--------------|-------|
| t3.small instance | ~$15-20 | 2 vCPU, 2GB RAM |
| EBS storage (50GB) | ~$5 | General purpose SSD |
| Data transfer | ~$5-10 | Varies with usage |
| Route 53 (DNS) | ~$1 | Hosted zone |
| **Total** | **~$25-35/month** | Plus LLM API costs |

**Scaling Options:**
- Fargate: ~$40-60/month (serverless containers)
- Lambda + API Gateway: ~$10-30/month (request-based)

#### Option D: Cloudflare Workers + D1

| Item | Monthly Cost | Notes |
|------|--------------|-------|
| Workers (paid) | $5 | 10M requests included |
| D1 Database | $5 | 5GB storage included |
| R2 Storage | ~$5 | For transcripts/outputs |
| Pages | $0 | Free for web dashboard |
| **Total** | **~$15/month** | Requires architecture adaptation |

**Note:** Would require rewriting Python backend to JavaScript/TypeScript for Workers runtime.

#### Option E: DigitalOcean/Linode/Vultr VPS

| Item | Monthly Cost | Notes |
|------|--------------|-------|
| Basic VPS | $6-12 | 1-2 vCPU, 1-2GB RAM |
| Backups | $1-2 | Weekly snapshots |
| **Total** | **~$8-15/month** | Closest to home VM experience |

### 4.4 Cost Comparison Matrix

| Option | Monthly Cost | Reliability | Maintenance | Best For |
|--------|--------------|-------------|-------------|----------|
| Home VM | $15-30 | Medium | High (you) | Development, learning |
| Station | $0 | High | Low (IT) | Production use |
| AWS EC2 | $25-35 | High | Medium | Scalability needs |
| Cloudflare | $15 | High | Low | Edge performance |
| VPS | $8-15 | Medium-High | Medium | Simple remote hosting |

### 4.5 Recommendation

**V4.0 Deployment Path:**

1. **Start with Home VM** - Validate remote operation, work out issues
2. **Add Cloudflare Tunnel** - Enable secure remote access without port forwarding
3. **Run stability tests** - 1-2 months of reliable operation
4. **Prepare station handoff** - Documentation, runbooks, cost projections
5. **Deploy to station** - Primary production environment
6. **Keep home VM as backup** - Disaster recovery, testing

**Cloud hosting is deferred** unless:
- Station deployment is blocked for policy reasons
- Scalability requirements exceed single-VM capacity
- Geographic distribution becomes important

---

## Part 5: Stability Testing

### 5.1 Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| **Load** | Concurrent job processing | Verify worker handles queue |
| **Endurance** | 24-hour continuous operation | Find memory leaks, resource exhaustion |
| **Recovery** | Service restart, database recovery | Validate self-healing |
| **Failover** | Network interruption, API timeout | Graceful degradation |
| **Security** | Auth bypass attempts, injection | Vulnerability scanning |

### 5.2 Load Testing Plan

```python
# tests/load/test_concurrent_jobs.py
import asyncio
import httpx

async def submit_job(client, transcript_path):
    response = await client.post("/api/queue", json={
        "transcript_path": transcript_path,
        "priority": "normal"
    })
    return response.json()["job_id"]

async def test_concurrent_processing():
    """Submit 10 jobs simultaneously, verify all complete."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Submit jobs concurrently
        jobs = await asyncio.gather(*[
            submit_job(client, f"test_transcript_{i}.srt")
            for i in range(10)
        ])

        # Wait for completion (with timeout)
        for job_id in jobs:
            await wait_for_completion(client, job_id, timeout=300)
```

### 5.3 Monitoring Requirements

| Metric | Alert Threshold | Response |
|--------|-----------------|----------|
| API response time | >5s p95 | Investigate load, scale if needed |
| Worker queue depth | >20 jobs | Check worker health, add capacity |
| Error rate | >5% | Review logs, identify root cause |
| Disk usage | >80% | Archive old outputs, expand storage |
| Memory usage | >90% | Restart services, check for leaks |
| LLM API errors | >10% | Check OpenRouter status, switch provider |

---

## Part 6: Network Architecture

### 6.1 Cloudflare Tunnel Setup

```bash
# Install cloudflared
brew install cloudflared  # macOS
# or
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create editorial-assistant

# Configure tunnel
cat > ~/.cloudflared/config.yml << EOF
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: editorial.yourdomain.com
    service: http://localhost:8000
  - hostname: editorial-app.yourdomain.com
    service: http://localhost:3000
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run editorial-assistant
```

### 6.2 Cloudflare Access Policies

Configure in Cloudflare Zero Trust dashboard:
- **Email allowlist** - Only specified emails can access
- **IP restrictions** - Optional additional layer
- **Session duration** - 24 hours recommended
- **Device posture** - Optional (require specific OS, browser)

### 6.3 Network Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Edge                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  WAF / DDoS     │  │  Access Policy  │  │  Tunnel Proxy   │  │
│  │  Protection     │  │  (Email Auth)   │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Encrypted tunnel
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Home VM / Station Server                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ cloudflared │  │             │  │             │              │
│  │   daemon    │──│  API :8000  │  │  Web :3000  │              │
│  └─────────────┘  │             │  │             │              │
│                   └─────────────┘  └─────────────┘              │
│                          │                                       │
│                   ┌──────┴──────┐                                │
│                   │   Worker    │                                │
│                   │  (SQLite)   │                                │
│                   └─────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Backup & Recovery

### 7.1 Backup Strategy

| Data | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| SQLite database | Daily | 30 days | SQLite backup API + compress |
| Transcripts | On ingest | Indefinite | Original files preserved |
| Outputs | On generation | 90 days | Archive older to cold storage |
| Config files | On change | Git history | Version controlled |
| Secrets | Manual | Secure note | 1Password/Bitwarden |

### 7.2 Recovery Procedures

**Database Corruption:**
```bash
# Restore from backup
cp /backups/dashboard-YYYYMMDD.db data/dashboard.db

# Verify integrity
sqlite3 data/dashboard.db "PRAGMA integrity_check;"
```

**Service Failure:**
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs --tail=100 api

# Restart specific service
docker-compose restart api

# Full restart
docker-compose down && docker-compose up -d
```

---

## Part 8: V4.0 Roadmap

### Phase 0: Naming Consolidation (pre-sprint)

1. Rename GitHub repo to `cardigan`
2. Rename local directory, update remotes
3. Update user-visible strings (API title, web UI, README, CLAUDE.md)
4. Update Claude Desktop MCP config path
5. Update agent prompts
6. Verify all services start cleanly under new name

### Phase 1: Home VM Deployment (2 sprints)

1. Docker Compose setup
2. Cloudflare Tunnel configuration
3. Cloudflare Access email auth
4. Basic monitoring (healthchecks)
5. Backup scripts
6. Stability testing (1 week minimum)

### Phase 1.5: Remote MCP Server (1 sprint)

1. Add Streamable HTTP transport to Cardigan (dual-transport: keep stdio)
2. Route MCP endpoint through Cloudflare tunnel (new subdomain or path)
3. Verify Cloudflare Access protects the MCP endpoint
4. Register as Custom Connector in claude.ai
5. Test from web (claude.ai) and mobile (Claude iOS)
6. Verify all tools and prompts work over HTTP transport

### Phase 2: Security Hardening (1-2 sprints)

1. Rate limiting implementation
2. Audit logging
3. Secret rotation procedures
4. Security scanning (OWASP ZAP, etc.)
5. Penetration testing checklist

### Phase 3: Station Preparation (1-2 sprints)

1. Documentation for IT handoff
2. Runbooks for common operations
3. Cost projection reports
4. Integration API documentation
5. Training materials

### Phase 4: Station Deployment

1. VM provisioning (IT)
2. Application deployment
3. Monitoring integration
4. User onboarding
5. Support transition

---

## Part 9: Remote MCP Server (Cardigan Over HTTP)

### 9.1 Background & Research (January 2026)

As of late 2025 / early 2026, Claude's MCP support has expanded well beyond
Claude Desktop's original stdio-only model:

- **Claude.ai (web)** supports remote MCP servers via "Custom Connectors"
  (Settings > Connectors > Add Custom Connector). Available on Pro, Max, Team,
  and Enterprise plans.
- **Claude Mobile (iOS/Android)** supports remote MCP since July 2025. Servers
  added via claude.ai sync automatically. Cannot add new servers from mobile.
- **Claude Code** supports remote MCP via `claude mcp add --transport http`.
- **Claude Desktop** supports remote connectors configured through Settings >
  Connectors (not via `claude_desktop_config.json`).

**Transport protocols:**
- **Streamable HTTP** — the current recommended transport (spec version 2025-03-26).
  Combines HTTP with SSE for bidirectional communication.
- **SSE (Server-Sent Events)** — still supported but actively being deprecated.
- **stdio** — local-only, used by Claude Desktop for subprocess-based servers.

**Authentication:**
- Authless connections (rely on network-level auth like Cloudflare Access)
- OAuth 2.0 (both 3/26 and 6/18 spec versions; Dynamic Client Registration supported)
- Custom client ID + secret

**Sources:**
- https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers
- https://modelcontextprotocol.io/docs/develop/connect-remote-servers
- https://platform.claude.com/docs/en/agents-and-tools/remote-mcp-servers

### 9.2 What This Enables

Exposing Cardigan as a remote MCP server means the full copy-editor workflow
(list projects, load context, review brainstorming, save revisions, check SST
metadata) becomes available from:

- **Any browser** via claude.ai — no Claude Desktop needed
- **Mobile** via the Claude iOS/Android app — review metadata from anywhere
- **Claude Code** via `claude mcp add --transport http cardigan <url>`
- **Claude Desktop** via Settings > Connectors (alongside the existing stdio config)

All of Cardigan's prompts (hello_neighbor, start_edit_session,
review_brainstorming, analyze_seo, fact_check, save_my_work) would appear in
the Claude web/mobile attachment menu as selectable prompts.

### 9.3 Implementation Plan

**What changes:**

The transport layer only. All tool definitions, handlers, prompts, and business
logic in `mcp_server/server.py` remain identical. The conversion is:

```python
# CURRENT (stdio — local only)
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         server.create_initialization_options())

# NEW (Streamable HTTP — remote accessible)
# Uses the MCP Python SDK's HTTP server support.
# The exact API depends on SDK version; conceptually:
from mcp.server.http import create_http_server  # or similar

app = create_http_server(server)
# Run with uvicorn on port 3001
```

**Dual-transport approach (recommended):**
Keep stdio as the default for local Claude Desktop use. Add an HTTP entrypoint
(e.g., `server_http.py` or a `--transport http` CLI flag) for remote access.
This avoids disrupting the existing Claude Desktop workflow.

**Tunnel routing:**

Add a second ingress rule in `config/cloudflared.yml`:

```yaml
ingress:
  - hostname: cardigan.bymarkriechers.com
    service: http://localhost:3000      # Web dashboard (existing)
  - hostname: mcp.bymarkriechers.com    # or cardigan-mcp.bymarkriechers.com
    service: http://localhost:3001      # Cardigan MCP HTTP endpoint
  - service: http_status:404
```

Requires a one-time `cloudflared tunnel route dns cardigan mcp.bymarkriechers.com`
to create the CNAME record.

**Registration:**
In claude.ai: Settings > Connectors > Add Custom Connector > enter the MCP URL.
This syncs to Desktop and Mobile automatically.

### 9.4 Security Considerations

**Deployment assumption:** Remote MCP should be rolled out alongside the VM
migration (Phase A or Phase B), not on a personal laptop. Running on a VM or
station server addresses uptime, eliminates personal-machine exposure, and
lets Docker container isolation do its job. The remaining concern is the
**attack surface of Cardigan's privileged API access** — what an authenticated
(or compromised) session can reach.

#### 9.4.1 Tool-by-Tool Attack Surface Audit

**Read-only tools (data exposure risk):**

| Tool | What It Reads | Sensitive? | Notes |
|------|---------------|------------|-------|
| `list_processed_projects` | Project folder names, manifest metadata | Low | No content, just inventory |
| `get_project_summary` | Manifest metadata | Low | Status, dates, deliverable list |
| `search_projects` | Same as list, with filtering | Low | |
| `load_project_for_editing` | Analyst output + Airtable SST data | **Medium** | Exposes full brainstorming content and canonical metadata from Airtable |
| `get_formatted_transcript` | Full transcript text | **Medium** | Pre-broadcast content; may contain embargoed material |
| `read_project_file` | Any file within a project folder | **Medium** | Path-validated against project root (server.py:1097), but grants access to all project artifacts |
| `get_sst_metadata` | Airtable SST record by Media ID | **Medium** | Titles, descriptions, keywords from the canonical metadata store |

**Write tools (integrity risk):**

| Tool | What It Writes | Risk | Notes |
|------|----------------|------|-------|
| `save_revision` | New `copy_revision_vN.md` + manifest update | **High** | Could inject bad copy into the editorial pipeline |
| `save_keyword_report` | New `keyword_report_vN.md` + manifest update | **Medium** | Less downstream impact, but still pollutes project folder |

**External API credentials in scope:**

| Credential | Used By | Access Scope | Risk If Leaked |
|------------|---------|--------------|----------------|
| `AIRTABLE_API_KEY` | `get_sst_metadata`, `load_project_for_editing` | Read-only by policy, but the token itself may have write permissions at the Airtable level | **High** — could allow Airtable writes if exfiltrated, violating the read-only constraint |
| `EDITORIAL_API_URL` | `fetch_job_from_api` | Internal FastAPI on localhost:8000 | **Low** — only reachable within the Docker network |

#### 9.4.2 Threat Scenarios

**Scenario 1: Cloudflare Access bypass**
An attacker reaches the MCP endpoint without authenticating. They get full
tool access. *Mitigation:* Cloudflare Access is the outer gate; adding
MCP-level OAuth (Phase B) provides defense in depth. Even without OAuth,
Cloudflare Access bypass would require a Cloudflare-level vulnerability —
unlikely but not impossible.

**Scenario 2: Authorized user, compromised session**
A legitimate user's session token is stolen (e.g., cookie theft on a shared
machine). Attacker can read all project data and write garbage revisions.
*Mitigation:* Short session duration in Cloudflare Access (e.g., 8 hours
instead of 24). Audit logging of all tool invocations (see 9.4.3). Versioned
revisions mean bad writes don't overwrite good ones — they just create a new
version that can be identified and deleted.

**Scenario 3: Airtable key exfiltration**
The Airtable API key lives in the MCP server's environment. A code injection
or dependency supply-chain attack could read it. *Mitigation:* Use a
[scoped Airtable personal access token](https://airtable.com/developers/web/guides/personal-access-tokens)
with read-only permissions on only the SST table, rather than a full-access
key. The Docker container also limits what an attacker can pivot to — no
access to the host filesystem, Keychain, or other services.

#### 9.4.3 Recommended Mitigations

| Mitigation | Effort | Priority | Notes |
|------------|--------|----------|-------|
| **Scoped Airtable token** | Low | P0 | Replace full-access key with a PAT scoped to read-only on SST table only. Do this regardless of remote MCP. |
| **Audit logging** | Medium | P0 | Log every tool invocation with timestamp, tool name, arguments, and caller identity (from Cloudflare Access headers). |
| **Claude connector tool permissions** | Zero | P1 | Claude's Custom Connector settings let you enable/disable specific tools. Disable write tools for mobile-only use if desired. |
| **Read-only mode flag** | Low | P1 | Add `MCP_READ_ONLY=true` env var that disables `save_revision` and `save_keyword_report` at the server level. Useful for a "browse from phone" profile. |
| **MCP-level OAuth** | Medium | P2 | Defense-in-depth beyond Cloudflare Access. Needed for station/multi-user deployment. |
| **Rate limiting** | Low | P2 | Limit tool calls per session. Prevents bulk data exfiltration even with valid auth. |
| **Container isolation** | Zero (Docker) | P0 | The `mcp` container only mounts `OUTPUT` and `transcripts` volumes. No host filesystem, no Keychain, no SSH keys. |

#### 9.4.4 Trust Boundary Summary

```
LOCAL (stdio)                    REMOTE (HTTP)
─────────────────               ─────────────────────────────────
Caller: Claude Desktop          Caller: Anyone who authenticates
on this machine only            via Cloudflare Access + (opt) OAuth

Trust: Implicit —               Trust: Verified —
same user, same OS              identity checked per-session

Secrets: Loaded from            Secrets: Loaded from container
macOS Keychain                  env vars (Docker secrets in prod)

Blast radius: Your Mac          Blast radius: OUTPUT folder +
(filesystem, Keychain, etc.)    Airtable read access (scoped)
```

Running on a VM with Docker narrows the blast radius significantly compared
to the current laptop setup. The remaining attack surface is the editorial
data itself (transcripts, metadata) and the Airtable read path — both
manageable with scoped tokens and audit logging.

### 9.5 Phasing

Remote MCP should ship alongside — not before — the VM migration. Running a
remotely-accessible MCP server on a personal laptop is inadvisable (uptime,
blast radius, secrets exposure). On a VM with Docker, the risk profile is
much more contained.

1. **Phase A (Home VM):** Deploy Cardigan as a Docker container with HTTP
   transport. Route through Cloudflare tunnel. Protect with Cloudflare Access.
   Scope the Airtable token to read-only SST. Add audit logging. Test from
   claude.ai web and mobile.
2. **Phase B (Station):** Add MCP-level OAuth for multi-user access. Evaluate
   tool-level permissions per user role (e.g., editors can write, reviewers
   read-only). The Docker compose `mcp` service already has a placeholder for
   auth mode configuration.
3. **Future:** If MCP Apps (announced January 2026) matures, Cardigan could
   potentially render UI elements within the Claude chat window — charts of
   project status, inline editing forms, etc.

---

## Part 10: Naming Consolidation — "Cardigan" as Canonical Name

### 10.1 Current Naming Landscape

The project currently uses three overlapping names with inconsistent boundaries:

| Name | Currently Means | Where It Appears |
|------|-----------------|------------------|
| **Editorial Assistant** | The whole project — repo, API, web UI, docs | 71 files; repo name `ai-editorial-assistant-v3`; API title; HTML `<title>`; CLAUDE.md; package.json `"editorial-assistant-dashboard"` |
| **The Metadata Neighborhood** | The automated pipeline / system branding | 15 files; README header; cloudflared config comments; scripts; vite config; docs |
| **Cardigan** | The MCP copy-editor agent specifically | 22 files; `Server("cardigan")`; README "Meet Cardigan" section; tunnel name; hostname |

The confusion: "Editorial Assistant" is the generic technical name nobody loves.
"The Metadata Neighborhood" is evocative but describes the pipeline/place, not
the product. "Cardigan" was introduced as the MCP agent's persona but has
organically become the name people actually use for the whole system.

### 10.2 Proposed Naming Convention

**Cardigan** becomes the canonical product name for the entire system.
**The Metadata Neighborhood** is retained as the thematic/world name — it's
the place where Cardigan lives and works, not a competing product name.

| Context | Name | Example |
|---------|------|---------|
| **Product / system name** | Cardigan | "Cardigan processes transcripts and generates metadata" |
| **Repo name** | `cardigan` | `github.com/MarkOnFire/cardigan` |
| **API title** | Cardigan API | `title="Cardigan API"` in FastAPI |
| **Web UI title** | Cardigan | `<title>Cardigan - PBS Wisconsin</title>` |
| **npm package name** | `cardigan-dashboard` | `package.json` |
| **Docker image names** | `cardigan-api`, `cardigan-web`, `cardigan-mcp` | docker-compose services |
| **Hostname / URL** | `cardigan.bymarkriechers.com` | Already done |
| **MCP server name** | `cardigan` | Already done: `Server("cardigan")` |
| **Claude connector name** | Cardigan | What appears in Settings > Connectors |
| **Thematic / flavor text** | The Metadata Neighborhood | README intro, agent persona text, "Welcome to The Metadata Neighborhood" |
| **MCP prompts / persona** | Cardigan (the friendly neighbor) | Unchanged — the Mister Rogers voice stays |
| **Internal agent prompts** | Unchanged | `.claude/agents/*.md` reference "Editorial Assistant" as the system they serve — update to "Cardigan" |

### 10.3 What Changes (Inventory)

#### Tier 1: Breaking changes (must be coordinated)

| Item | Current | New | Risk |
|------|---------|-----|------|
| **GitHub repo name** | `ai-editorial-assistant-v3` | `cardigan` | All git remotes, clone URLs, any CI referencing the old name. GitHub auto-redirects old URLs, but local remotes need updating. |
| **npm package name** | `editorial-assistant-dashboard` | `cardigan-dashboard` | Only affects `package.json` and `package-lock.json`. No public registry. |
| **Python package refs** | Various `# Editorial Assistant` headers | `# Cardigan` | No PyPI package, just file-level comments. Non-breaking. |
| **Claude Desktop config** | MCP server path references `ai-editorial-assistant-v3` | Updated path after repo rename | Claude Desktop `claude_desktop_config.json` needs the new path to `mcp_server/server.py` |
| **Directory on disk** | `~/Developer/ai-editorial-assistant-v3/` | `~/Developer/cardigan/` | Scripts, CLAUDE.md, init.sh, the-lodge submodule references all use this path |

#### Tier 2: User-visible strings (update at will, non-breaking)

| Item | Current | New |
|------|---------|-----|
| API title | `"Editorial Assistant API"` | `"Cardigan API"` |
| API description | `"API for PBS Wisconsin Editorial Assistant v3.0"` | `"PBS Wisconsin transcript processing & metadata pipeline"` |
| HTML title | `"Editorial Assistant - PBS Wisconsin"` | `"Cardigan - PBS Wisconsin"` |
| Layout header | `"Digital Editorial Assistant"` | `"Cardigan"` |
| README header | Mixed | `"# Cardigan"` with Metadata Neighborhood as subtitle |
| CLAUDE.md | `"PBS Wisconsin Editorial Assistant v3.0"` | `"Cardigan — PBS Wisconsin metadata pipeline"` |
| Log messages | `"Starting Editorial Assistant API v3.0"` | `"Starting Cardigan API"` |

#### Tier 3: Internal documentation (update as encountered)

Planning docs, sprint plans, archived docs, agent prompts — update references
to "Editorial Assistant" → "Cardigan" as files are touched during v4.0 work.
Don't do a bulk find-and-replace across archived docs; they're historical.

### 10.4 Migration Strategy

**Principle:** Do the rename as the first step of v4.0, before Docker and
remote MCP work begins. That way all new infrastructure (Dockerfiles,
compose configs, tunnel routes, connector names) starts clean with the
canonical name.

**Sequence:**

1. **Rename the repo on GitHub** (`ai-editorial-assistant-v3` → `cardigan`).
   GitHub auto-redirects the old URL. Update local remote:
   `git remote set-url origin git@github.com:MarkOnFire/cardigan.git`

2. **Rename the directory on disk** (`mv ai-editorial-assistant-v3 cardigan`).
   Update any absolute paths in:
   - `CLAUDE.md` (repo purpose line)
   - `init.sh`
   - Claude Desktop `claude_desktop_config.json` (MCP server path)
   - the-lodge references (if any submodule or symlink paths)
   - `.env` or `.env.example` if they contain paths

3. **Update user-visible strings** (Tier 2 above). This is one commit touching
   ~10 files: `api/main.py`, `web/index.html`, `web/src/components/Layout.tsx`,
   `web/package.json`, `README.md`, `CLAUDE.md`, and a few log messages.

4. **Update agent prompts** in `.claude/agents/*.md` — change "Editorial
   Assistant" references to "Cardigan" where they describe the system.

5. **Leave archived docs alone.** Files in `planning/archive/` keep their
   original naming. They're historical records.

6. **Verify nothing broke:**
   - `./scripts/start.sh` — services come up
   - `./scripts/status.sh` — all healthy
   - Claude Desktop reconnects to MCP server
   - Web UI loads with new title
   - API docs show new title at `/docs`

### 10.5 Names to Preserve

- **"The Metadata Neighborhood"** — keep as the thematic/world name in the
  README intro, the cloudflared config comments, and Cardigan's personality
  prompts. It's the *setting*, not the *product*.
- **"Cardigan" as a persona** — the Mister Rogers voice in MCP prompts stays
  exactly as-is. The rename elevates the persona name to product name; it
  doesn't change the persona.
- **Tunnel name `cardigan`** — already aligned. No change needed.
- **Hostname `cardigan.bymarkriechers.com`** — already aligned.

---

## Part 11: SEO Insights Visualization (Future — Needs Brainstorming)

### 11.1 Opportunity

The v3.5 backlog includes a SEMRush CSV upload feature (`backlog.4` in
`feature_list.json`) that will store raw keyword research data in
`OUTPUT/{media_id}/semrush/`. Once that data exists per-project, the Job
Detail page could surface it visually rather than leaving it buried in CSV
files and markdown reports.

This section intentionally captures the *opportunity and constraints* without
prescribing a design. The visualization approach should be brainstormed when
implementation is closer.

### 11.2 What Data Will Be Available

The SEMRush CSV upload workflow (once built) produces:

| Data Source | Location | Format | Contains |
|-------------|----------|--------|----------|
| Raw SEMRush export | `OUTPUT/{media_id}/semrush/*.csv` | CSV | Keywords, search volume, keyword difficulty, CPC, competition level, trends, SERP features |
| AI keyword report | `keyword_report_vN.md` | Markdown | AI-recommended keywords with rationale |
| SEO agent output | `seo_output.md` | Markdown | Titles, descriptions, tags, keyword strategy |
| SST metadata | Airtable (read-only) | API | Canonical keywords/tags currently in production |

The interesting visualization opportunity is the *intersection* of these — how
do the AI's keyword suggestions compare to actual SEMRush search volume data,
and how does that compare to what's currently live in the SST?

### 11.3 Possible Widget Directions

These are rough starting points for a future brainstorm, not specifications:

**Keyword scorecard** — A compact summary on the Job Detail page showing how
many of the AI-suggested keywords have SEMRush data backing them up. Quick
signal: "12 of 18 suggested keywords have measurable search volume."

**Volume/difficulty scatter** — Plot suggested keywords on a search volume vs.
keyword difficulty chart. Highlights the sweet spot (high volume, low
difficulty) and flags keywords that are aspirational but competitive.

**Gap analysis** — Compare what's in the SST now vs. what the AI recommends
vs. what SEMRush says people actually search for. Surface missed opportunities.

**Trend indicators** — SEMRush CSV includes trend data. Show which suggested
keywords are trending up vs. flat vs. declining. Relevant for seasonal PBS
content (holiday specials, etc.).

**Before/after** — For projects with multiple keyword report versions, show how
the keyword strategy evolved from v1 (AI-only) to v2 (SEMRush-informed).

### 11.4 Technical Considerations

- **CSV parsing**: The API will need a parser for SEMRush's CSV format. The
  `knowledge/semrush-api.md` reference doc covers the response schema. The
  CSV columns vary by report type (Keyword Overview vs. Domain Organic, etc.),
  so the parser should be tolerant of missing columns.

- **Frontend charting**: The web dashboard is React + Tailwind. Lightweight
  charting options include Recharts (already common in React projects),
  Chart.js, or even a simple HTML table with conditional formatting for a
  first pass. No need for a heavy visualization library.

- **Data freshness**: SEMRush data is a point-in-time snapshot (uploaded
  manually). The visualization should display the upload date prominently
  so users don't mistake stale data for current rankings.

- **Optional by design**: Not every project will have SEMRush data. The widget
  should degrade gracefully — show a "No SEMRush data uploaded" state with a
  prompt to upload, not an empty chart.

### 11.5 Prerequisites

1. **SEMRush CSV upload feature** (`backlog.4`) must be implemented first —
   there's no data to visualize until the upload pipeline exists.
2. **SEO agent re-run with SEMRush context** — the enriched keyword report
   is what makes the comparison meaningful.
3. **Job Detail page stable** — the visualization builds on the existing
   project detail UI, so that should be settled before adding widgets.

### 11.6 Relationship to Remote MCP

If Cardigan is exposed as a remote MCP server (Part 9), the SEMRush data
also becomes accessible to Claude via the `read_project_file` tool — a user
on mobile could ask Cardigan "what does the SEMRush data say about this
project's keywords?" without needing the web dashboard at all. The
visualization and the MCP tool access are complementary, not competing.

---

## Prerequisites

Before starting V4.0:

1. **V3.5 feature work complete** - Don't mix feature and deployment work
2. **Months of stable local use** - Proves the application is reliable
3. **Cost patterns understood** - Predictable LLM spend
4. **User workflows documented** - Know how it's actually used

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Remote deployment uptime | 99.5% |
| Mean time to recovery | <15 minutes |
| Security audit findings | 0 critical, <3 medium |
| Documentation coverage | 100% of operations |
| Handoff readiness score | Pass IT review |

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-06 | Claude Code | Initial creation from v3.0 deferred features |
| 2026-01-14 | Claude Code | Refocused on deployment/security; moved features to V3.5; added cost analysis |
| 2026-01-30 | Claude Code | Added Part 9: Remote MCP Server research; Phase 1.5 roadmap item; updated docker-compose MCP service |
| 2026-01-30 | Claude Code | Added Part 10: Naming consolidation plan ("Cardigan" as canonical); Phase 0 roadmap item |
| 2026-01-30 | Claude Code | Added Part 11: SEO Insights visualization placeholder; data inventory, widget directions, technical notes |
