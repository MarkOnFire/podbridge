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

  # Optional: MCP server for remote Claude Desktop
  mcp:
    build:
      context: ./mcp_server
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      - API_URL=http://api:8000
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
COPY agent-instructions/ ./agent-instructions/

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

### Phase 1: Home VM Deployment (2 sprints)

1. Docker Compose setup
2. Cloudflare Tunnel configuration
3. Cloudflare Access email auth
4. Basic monitoring (healthchecks)
5. Backup scripts
6. Stability testing (1 week minimum)

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
