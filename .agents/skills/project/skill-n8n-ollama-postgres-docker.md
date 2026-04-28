---
name: n8n-ollama-postgres-docker
version: 1.0.0
description: >
  Agent skill for running n8n, Ollama, and PostgreSQL together in a Docker Compose
  stack. Covers service topology, environment variables, GPU profiles, healthchecks,
  volumes, networking, model initialization, reverse proxy, and upgrade procedures.
  Sourced from the official n8n self-hosted AI starter kit and verified community
  production setups (2025–2026).
---

# n8n + Ollama + PostgreSQL — Docker Compose Skill

## Overview

This stack provides a fully self-hosted local AI automation platform:

| Service | Role | Port |
|---------|------|------|
| **n8n** | Workflow automation & AI agent orchestration | 5678 |
| **Ollama** | Local LLM inference server | 11434 (internal) |
| **PostgreSQL** | n8n workflow/credential/execution persistence | 5432 (internal) |
| **ollama-pull** *(init)* | One-shot model download at stack startup | — |

Ollama and Postgres ports should **not** be exposed to the host in production.
Only n8n (or a reverse proxy fronting it) needs to be externally accessible.

---

## Directory Structure

```
project/
├── docker-compose.yml
├── docker-compose.gpu-nvidia.yml  # GPU override (optional)
├── .env                           # secrets — never commit to Git
├── .env.example                   # committed template
├── init-scripts/
│   └── init-db.sh                 # optional DB init on first run
└── shared/                        # mounted into n8n at /data/shared
```

---

## Environment File (`.env`)

```dotenv
# ── PostgreSQL ────────────────────────────────────────────────────────────
POSTGRES_USER=n8n
POSTGRES_PASSWORD=change_me_strong_password
POSTGRES_DB=n8n

# ── n8n → PostgreSQL connection ───────────────────────────────────────────
DB_TYPE=postgresdb           # MUST be "postgresdb" — NOT "postgres"
DB_POSTGRESDB_HOST=postgres  # Docker service name, NOT localhost
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
DB_POSTGRESDB_USER=${POSTGRES_USER}
DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
DB_POSTGRESDB_SCHEMA=public
DB_POSTGRESDB_POOL_SIZE=10
DB_POSTGRESDB_CONNECTION_TIMEOUT=30000
DB_POSTGRESDB_IDLE_CONNECTION_TIMEOUT=60000

# ── n8n Security ─────────────────────────────────────────────────────────
N8N_ENCRYPTION_KEY=replace_with_long_random_secret_32chars_min
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=change_me_now

# ── n8n Instance ─────────────────────────────────────────────────────────
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
WEBHOOK_URL=http://localhost:5678
GENERIC_TIMEZONE=UTC
TZ=UTC
N8N_DIAGNOSTICS_ENABLED=false

# ── n8n Execution Retention ───────────────────────────────────────────────
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=336    # 14 days in hours

# ── Ollama ────────────────────────────────────────────────────────────────
OLLAMA_IMAGE_TAG=latest        # pin to specific version in production
OLLAMA_KEEP_ALIVE=1h           # keep models warm between requests
OLLAMA_NUM_PARALLEL=1          # parallel requests per model
OLLAMA_MAX_LOADED_MODELS=2     # chat model + embedding model
OLLAMA_FLASH_ATTENTION=1       # reduce VRAM at large context sizes
OLLAMA_CONTEXT_LENGTH=8192     # global default context window

# ── Models to auto-pull at startup ────────────────────────────────────────
DEFAULT_CHAT_MODEL=llama3.2
DEFAULT_EMBED_MODEL=nomic-embed-text

# For Mac users running Ollama natively (not in Docker):
# OLLAMA_HOST=host.docker.internal:11434
```

`.env.example` should contain all keys with placeholder values and be committed to Git.
`.env` contains real secrets and must be in `.gitignore`.

---

## `docker-compose.yml` (CPU / Mac / Default)

```yaml
name: local-ai-stack

services:

  # ── PostgreSQL ────────────────────────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: n8n-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - ai-network

  # ── Ollama ────────────────────────────────────────────────────────────────
  ollama:
    image: ollama/ollama:${OLLAMA_IMAGE_TAG:-latest}
    container_name: ollama
    restart: unless-stopped
    # Bind only to internal network; don't expose port to host in production
    # ports:
    #   - "127.0.0.1:11434:11434"   # uncomment only for local dev testing
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE:-1h}
      - OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL:-1}
      - OLLAMA_MAX_LOADED_MODELS=${OLLAMA_MAX_LOADED_MODELS:-2}
      - OLLAMA_FLASH_ATTENTION=${OLLAMA_FLASH_ATTENTION:-1}
      - OLLAMA_CONTEXT_LENGTH=${OLLAMA_CONTEXT_LENGTH:-8192}
    healthcheck:
      test: ["CMD-SHELL", "ollama list || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s    # allow time for initial model downloads
    networks:
      - ai-network

  # ── Ollama Model Init (one-shot) ─────────────────────────────────────────
  # Pulls default models on first run; exits immediately after.
  # Remove or comment out after first successful start for faster restarts.
  ollama-pull:
    image: ollama/ollama:${OLLAMA_IMAGE_TAG:-latest}
    container_name: ollama-pull
    restart: "no"           # run once and exit
    depends_on:
      ollama:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
        ollama pull ${DEFAULT_CHAT_MODEL:-llama3.2} &&
        ollama pull ${DEFAULT_EMBED_MODEL:-nomic-embed-text} &&
        echo 'Models ready'
      "
    environment:
      - OLLAMA_HOST=ollama:11434
    networks:
      - ai-network

  # ── n8n ───────────────────────────────────────────────────────────────────
  n8n:
    image: n8nio/n8n:latest
    # Pin in production: n8nio/n8n:1.88.0
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      # Database
      - DB_TYPE=${DB_TYPE}
      - DB_POSTGRESDB_HOST=${DB_POSTGRESDB_HOST}
      - DB_POSTGRESDB_PORT=${DB_POSTGRESDB_PORT}
      - DB_POSTGRESDB_DATABASE=${DB_POSTGRESDB_DATABASE}
      - DB_POSTGRESDB_USER=${DB_POSTGRESDB_USER}
      - DB_POSTGRESDB_PASSWORD=${DB_POSTGRESDB_PASSWORD}
      - DB_POSTGRESDB_SCHEMA=${DB_POSTGRESDB_SCHEMA}
      - DB_POSTGRESDB_POOL_SIZE=${DB_POSTGRESDB_POOL_SIZE:-10}
      # Instance
      - N8N_HOST=${N8N_HOST:-localhost}
      - N8N_PORT=${N8N_PORT:-5678}
      - N8N_PROTOCOL=${N8N_PROTOCOL:-http}
      - WEBHOOK_URL=${WEBHOOK_URL}
      - GENERIC_TIMEZONE=${GENERIC_TIMEZONE:-UTC}
      - TZ=${TZ:-UTC}
      - N8N_DIAGNOSTICS_ENABLED=${N8N_DIAGNOSTICS_ENABLED:-false}
      # Security
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_BASIC_AUTH_ACTIVE=${N8N_BASIC_AUTH_ACTIVE:-true}
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      # Execution
      - EXECUTIONS_DATA_SAVE_ON_ERROR=${EXECUTIONS_DATA_SAVE_ON_ERROR:-all}
      - EXECUTIONS_DATA_SAVE_ON_SUCCESS=${EXECUTIONS_DATA_SAVE_ON_SUCCESS:-none}
      - EXECUTIONS_DATA_PRUNE=${EXECUTIONS_DATA_PRUNE:-true}
      - EXECUTIONS_DATA_MAX_AGE=${EXECUTIONS_DATA_MAX_AGE:-336}
    user: "1000:1000"
    volumes:
      - n8n_data:/home/node/.n8n
      - ./shared:/data/shared          # shared filesystem for Read/Write File nodes
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:5678/healthz || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 20
      start_period: 30s
    networks:
      - ai-network

volumes:
  postgres_data:
  ollama_data:
  n8n_data:

networks:
  ai-network:
    driver: bridge
```

---

## GPU Override File (`docker-compose.gpu-nvidia.yml`)

Compose supports **profiles** or **override files** for GPU variants. Use an override
file pattern to keep the base file clean:

```yaml
# docker-compose.gpu-nvidia.yml
# Usage: docker compose -f docker-compose.yml -f docker-compose.gpu-nvidia.yml up -d

services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all           # or: device_ids: ["0"] for a specific GPU
              capabilities: [gpu]
    environment:
      - OLLAMA_GPU_OVERHEAD=536870912   # 512 MB VRAM reserved for OS
```

**NVIDIA prerequisites on host:**
```bash
# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=...] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**AMD GPU (Linux):**
```yaml
# docker-compose.gpu-amd.yml
services:
  ollama:
    image: ollama/ollama:rocm
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - video
```

**Profile-based alternative (n8n official starter kit pattern):**
```bash
docker compose --profile gpu-nvidia up -d
docker compose --profile gpu-amd up -d
docker compose --profile cpu up -d
```

---

## Startup Sequence

```
docker compose up -d
```

Start order enforced by `depends_on` with healthchecks:

```
postgres (healthy)
    └─> ollama (healthy)
            └─> ollama-pull (runs once, exits)
            └─> n8n (starts after postgres + ollama healthy)
```

n8n **must** wait for postgres to be healthy before starting — otherwise it tries to
run DB migrations against an unready server and fails. Use `condition: service_healthy`
not just `condition: service_started`.

---

## Connecting n8n to Ollama

In n8n's **Credentials** panel:

| Field | Value |
|-------|-------|
| Credential Type | `Ollama` |
| Base URL | `http://ollama:11434` |

The service name `ollama` resolves within the shared Docker network `ai-network`.
Do **not** use `localhost` — n8n runs in a separate container.

For Mac users running Ollama natively (not in Docker):
```
OLLAMA_HOST=host.docker.internal:11434
```
Also update the n8n Ollama credential Base URL to `http://host.docker.internal:11434`.

### n8n Nodes for Ollama

| Node | Purpose | Suggested Model |
|------|---------|----------------|
| `Ollama Chat Model` | AI Agent LLM backend | `llama3.2` |
| `Embeddings Ollama` | Vector embedding for RAG | `nomic-embed-text` |
| `Ollama Model` | Standalone text generation | `llama3.2` |

---

## Connecting n8n to PostgreSQL (as a Data Tool)

Beyond n8n's own metadata DB, you can use the same Postgres container as a **data store**
inside n8n workflows (e.g., for storing vector embeddings, RAG chunks, or app data).

**Credential:**
- Type: `Postgres`
- Host: `postgres`  ← Docker service name
- Port: `5432`
- Database: `n8n` (or create a separate DB)
- User/Password: match `.env` values
- SSL: off (internal Docker network)

**pgvector for RAG** — install pgvector into the Postgres container to enable vector
similarity search without a separate Qdrant instance:

```yaml
# Replace postgres image in docker-compose.yml
postgres:
  image: pgvector/pgvector:pg16    # includes pgvector extension
```

Then enable in Postgres:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  content TEXT,
  metadata JSONB,
  embedding vector(768)            -- match nomic-embed-text dimensions
);
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## Reverse Proxy with TLS (Caddy)

Add Caddy to the Compose stack for automatic HTTPS:

```yaml
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - n8n
    networks:
      - ai-network
```

`Caddyfile`:
```
automation.example.com {
    reverse_proxy n8n:5678
}
```

Update `.env`:
```dotenv
N8N_HOST=automation.example.com
N8N_PROTOCOL=https
WEBHOOK_URL=https://automation.example.com
```

Ensure the proxy forwards `X-Forwarded-Proto` and `X-Forwarded-For` so n8n knows it
is behind HTTPS. Add `N8N_PROXY_HOPS=1` to the n8n environment.

---

## Common n8n AI Workflow Patterns on This Stack

### RAG Chatbot (Postgres pgvector)

```
[Chat Trigger]
    → [Embeddings Ollama: nomic-embed-text]
    → [Postgres: vector similarity search]
    → [AI Agent: llama3.2 + context from search results]
    → [Respond to Chat]
```

### Document Ingestion Pipeline

```
[Local File Trigger / Webhook]
    → [Read File from /data/shared]
    → [Text Splitter: chunk document]
    → [Embeddings Ollama: nomic-embed-text]
    → [Postgres: INSERT INTO embeddings]
```

### Agentic Multi-Step Workflow

```
[Webhook Trigger]
    → [AI Agent: llama3.2]
         ├── Tool: Postgres Query
         ├── Tool: HTTP Request (external API)
         └── Tool: Execute Sub-workflow
    → [Guardrails Node]
    → [Action: write result to Postgres / send notification]
```

---

## Operations

### Day-to-Day Commands

```bash
# Start the full stack
docker compose up -d

# Start with NVIDIA GPU
docker compose -f docker-compose.yml -f docker-compose.gpu-nvidia.yml up -d

# View logs
docker compose logs -f n8n
docker compose logs -f ollama
docker compose logs -f postgres

# Stop without removing data
docker compose down

# Stop and remove all volumes (DESTRUCTIVE — deletes all data)
docker compose down -v
```

### Health Checks

```bash
# n8n health
curl http://localhost:5678/healthz

# Ollama health + loaded models
curl http://localhost:11434/api/tags
docker exec ollama ollama ps

# Postgres health
docker exec n8n-postgres pg_isready -U n8n -d n8n
```

### Backup

```bash
# Backup Postgres (includes n8n workflows, credentials, execution history)
docker exec -t n8n-postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > backup_$(date +%F).sql

# Restore
cat backup_2026-04-28.sql | \
  docker exec -i n8n-postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

# Backup n8n encryption key metadata (CRITICAL — losing this = lost credentials)
docker run --rm -v n8n_data:/data alpine \
  tar czf - -C / data > n8n_data_$(date +%F).tgz

# Backup Ollama models (optional — re-pullable, but saves bandwidth)
docker run --rm -v ollama_data:/data alpine \
  tar czf - -C / data > ollama_models_$(date +%F).tgz
```

### Upgrade

```bash
# 1. Take backups
# 2. Pin new versions in docker-compose.yml
# 3. Pull and recreate
docker compose pull
docker compose up -d

# Watch n8n DB migrations
docker compose logs -f n8n | grep -i migrat
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| n8n: "connection refused" to Postgres | DB not healthy yet or wrong host | Confirm `DB_POSTGRESDB_HOST=postgres`, check `postgres` service healthcheck passes |
| n8n: can't reach Ollama | Wrong credential URL | Set Base URL to `http://ollama:11434` in n8n credentials |
| Ollama GPU not used | Missing NVIDIA toolkit or wrong Compose GPU config | Verify `ollama ps` PROCESSOR column; use `deploy.resources.reservations.devices` |
| `DB_TYPE=postgres` fallback to SQLite | Typo in env var | Must be `DB_TYPE=postgresdb` exactly |
| n8n credentials unrecoverable | Lost `N8N_ENCRYPTION_KEY` | Set it before first run; store in secrets manager; never rotate without migration |
| Models unloading between requests | Default 5-minute keep-alive | Set `OLLAMA_KEEP_ALIVE=1h` or preload at startup with `keep_alive: -1` |
| `ollama-pull` keeps re-running | Restart policy not `no` | Set `restart: "no"` on the init container |
| OOM on GPU during multi-model load | Too many models for VRAM | Reduce `OLLAMA_MAX_LOADED_MODELS=1`; check VRAM with `nvidia-smi` |
| Volume permission errors on n8n | User mismatch | n8n runs as UID 1000; use named volumes (not bind mounts) or `chown -R 1000:1000` |
| Webhook URL mismatch | Wrong `WEBHOOK_URL` env var | Set to exact public base URL; update `N8N_PROTOCOL` and `N8N_HOST` to match |
| Cold start latency on first Ollama request | Model not preloaded | Use `ollama-pull` init container + `OLLAMA_KEEP_ALIVE=-1` for warm models |

---

## Security Hardening Checklist

- [ ] `N8N_ENCRYPTION_KEY` set before first run and backed up to a secrets manager
- [ ] `N8N_BASIC_AUTH_ACTIVE=true` with strong, non-default credentials
- [ ] Ollama port **not** exposed to host (`11434` commented out in ports)
- [ ] Postgres port **not** exposed to host (`5432` not in ports)
- [ ] n8n behind reverse proxy with TLS in production
- [ ] `.env` in `.gitignore`; `.env.example` committed without real secrets
- [ ] Image versions pinned (not `latest`) in production
- [ ] n8n credential URLs use Docker service names, not `localhost`
- [ ] Firewall: only ports 80/443 open externally; 5678, 5432, 11434 internal only
- [ ] Backups automated and tested for restore
