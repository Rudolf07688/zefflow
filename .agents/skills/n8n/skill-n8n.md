---
name: n8n
version: 1.0.0
description: >
  Agent skill for n8n workflow automation — covering workflow design, AI agents,
  sub-workflows, error handling, security, observability, and production deployment
  patterns. All techniques are sourced from verified 2025–2026 production usage.
---

# n8n Agent Skill

## Overview

n8n is a self-hostable, low-code workflow automation platform with over 400 integrations,
native LangChain-based AI nodes, and support for agentic workflows. This skill teaches
proven patterns for building, deploying, and maintaining n8n workflows in production.

---

## Core Concepts

### Workflow Primitives

| Node Type | Role | Examples |
|-----------|------|---------|
| **Trigger** | Starts the workflow | Webhook, Schedule, Email, Manual |
| **Action** | Executes a task | HTTP Request, DB write, Send Email |
| **Logic** | Controls flow | IF, Switch, Merge, Filter |
| **Code** | Custom JavaScript/Python | Function Node, Code Node |
| **AI** | LLM/Agent nodes | AI Agent, Ollama Chat, Text Classifier |

### Execution Modes

- **Manual** — developer-triggered; used for testing and debugging
- **Production** — triggered by external events (webhooks, crons)
- **Queue Mode** — uses Redis to distribute work across worker processes; required for
  high-throughput and horizontal scaling. Use `N8N_RUNNERS_ENABLED=true` and
  `N8N_RUNNERS_MODE=external` for the modern task runner architecture (n8n 2.x+).

---

## Workflow Design Principles

### One Workflow, One Job

Every workflow must have a single, describable responsibility. If the description
requires the word "and", it is doing too much and should be split into sub-workflows.

```
✅ "Validate incoming lead payload"
✅ "Enrich contact via Clearbit"
✅ "Send Slack notification on enrichment failure"

❌ "Validate, enrich, and notify on incoming leads"
```

Refactor to sub-workflows when:
- A workflow exceeds 15–20 nodes
- It has more than three distinct branching paths
- The same logic appears in more than one workflow

### Sub-Workflows

Use the **Execute Sub-workflow** node to call child workflows. Each sub-workflow must
define a clear input schema and a clear output schema. This allows:

- Independent testing against sample data
- Isolated failure scope (only the sub-workflow fails, not the parent)
- Reuse across multiple parent workflows without copy-pasting nodes

```
Parent Workflow
  └─> Execute Sub-workflow: "Validate Payload"
  └─> Execute Sub-workflow: "Enrich via Clearbit"
  └─> Execute Sub-workflow: "Write to CRM"
  └─> Execute Sub-workflow: "Send Slack Alert"
```

### Naming Conventions

All workflows and nodes must be named descriptively:

| Bad ❌ | Good ✅ |
|--------|---------|
| `HTTP Request 4` | `GET Contact from HubSpot` |
| `If` | `Filter: Active Customers Only` |
| `Workflow 12` | `prod-leads-enrich-clearbit-v2` |

Workflow naming pattern: `{env}-{domain}-{action}-{integration}-{version}`
Node naming pattern: `{Verb}: {Subject} [via Service]`

### Version Control

- Export workflow JSON to Git **before every meaningful change**
- Include a one-line commit message describing what changed
- Never edit production workflows directly; use dev/staging first
- For rollback, maintain a named snapshot so restoration takes under 10 minutes

---

## Error Handling

### Error Trigger (Global Handler)

Every critical workflow must be assigned an **Error Trigger** workflow via
`Workflow Settings → Error Workflow`. This runs automatically on failure.

The error payload must capture:
- Workflow name and execution ID
- Node where the failure occurred
- Input data snapshot (redacted of PII/secrets)
- Correlation ID (for tracing across sub-workflows)
- Error message and stack trace
- Direct link to the failed execution for one-click debugging

### Retry Logic

Configure **Retry on Fail** on all nodes that call external APIs:
- Max attempts: 3–5
- Wait time: exponential backoff (1s → 2s → 4s → 8s)
- Add ±20% jitter to avoid thundering herd on simultaneous retries
- Cap max delay at 30 seconds

Map HTTP response codes to explicit actions:

| Code | Action |
|------|--------|
| 5xx | Retry with backoff |
| 401 | Refresh credentials, then retry |
| 429 | Respect `Retry-After` header; apply backoff |
| 422 | Route to manual review — retrying will never succeed |
| Any config error | Fail fast with immediate alert |

### Human-in-the-Loop (Send & Wait)

For high-risk or irreversible actions (emails, payments, database writes, AI-generated
output), implement a **send-and-wait** pause gate:

1. AI agent generates action
2. Validate output (see AI guardrails below)
3. Pause and send review request to named Slack channel / email
4. Resume on approval, reject on denial, or time-out after N minutes with escalation

---

## AI Agent Patterns

### Four Agentic Workflow Patterns

1. **Chained Requests** — Serial calls to different models in a fixed order. Use for
   multi-model pipelines (e.g., classify → summarize → translate).

2. **Single Agent with State** — One LLM node maintains context throughout the entire
   workflow. Use for conversational assistants and single-task automation.

3. **Gatekeeper + Specialists** — A primary agent routes tasks to specialized
   sub-agents. The gatekeeper handles simple requests directly and delegates
   complex ones. Use for multi-domain automation (e.g., support routing).

4. **Multi-Agent Team** — Multiple agents collaborate with distributed decision-making.
   Structures: mesh (free communication), hierarchical tree, or hybrid.
   Use for end-to-end pipelines (research → write → review → publish).

### AI Output Validation (Generate → Validate → Act)

**Never pass raw AI output directly into a consequential action.**

```
[AI Agent Node]
      ↓
[Guardrails Node]          ← validate on OUTPUT (v1.119+)
      ↓ pass
[Action Node]
      ↓ fail
[Human Review Queue]
```

Use n8n's native **Guardrails node** (v1.119+) for:
- Keyword blocking
- PII detection (emails, phone numbers, SSNs, credit cards)
- Secret key detection in outputs
- Jailbreak/prompt injection detection
- Topical alignment checks

For high-risk actions, additionally require **structured JSON output** with schema
validation before proceeding.

### AI Agent Guardrails Checklist

- [ ] `generate → validate → act` pattern enforced
- [ ] Guardrails node runs on **both input and output**
- [ ] Each agent scoped to minimum necessary tools
- [ ] Human-in-the-loop gates on irreversible actions
- [ ] Kill switch per agent workflow (pausable without touching infrastructure)
- [ ] Per-agent rate limits and execution caps to prevent runaway costs
- [ ] Prompts version-controlled separately from workflow logic
- [ ] Model and tool versions explicitly pinned (e.g., `llama3.2:3b`, not `latest`)

### Connecting n8n to Ollama

In the **Credentials** panel:
- Credential type: `Ollama`
- Base URL (Ollama in Docker): `http://ollama:11434`
- Base URL (Ollama on Mac host): `http://host.docker.internal:11434`
- Base URL (Ollama local, n8n local): `http://localhost:11434`

Available n8n Ollama nodes:
- `Ollama Chat Model` — for conversational AI agents
- `Ollama Model` — for standalone text generation
- `Embeddings Ollama` — for vector embedding (use with `nomic-embed-text`)

---

## Security

### Credential Management

- All secrets stored in **n8n's Credential Manager** — never hardcoded in nodes or
  Code node logic
- Workflow JSON exports contain credential IDs only, not values
- Set `N8N_ENCRYPTION_KEY` before first run; losing this key makes all stored
  credentials permanently unrecoverable
- Use least-privilege: each credential scoped to only the permissions the workflow needs
- For regulated environments: use HashiCorp Vault or AWS Secrets Manager instead of
  plain environment variables

### Webhook Security

- Every production webhook requires authentication:
  - Simple: Header token or Basic auth
  - Recommended for known vendors: HMAC signature verification (Stripe, GitHub, etc.)
- Rate limit webhooks at the reverse proxy level, not inside n8n
- Treat webhook paths as secrets even with auth in place
- Audit webhook paths periodically for orphans or collisions

### Execution Log Hygiene

| Log this ✅ | Do NOT log this ❌ |
|-------------|-------------------|
| Workflow name, execution ID | Full AI prompt/response payloads |
| Trigger type, key decision points | PII in any form |
| Error context and output summaries | API keys/tokens in response bodies |

---

## Observability

### Built-in Tools

- **Execution logs**: input/output captured per node (redact sensitive data)
- **n8n Insights Dashboard**: available from v1.89.0 on Pro/Enterprise — tracks
  execution count, failure rates, p95 runtime, and time saved per workflow
- **`/metrics` endpoint**: expose Prometheus-compatible metrics on self-hosted; disabled
  by default — enable before you need it

### Key Metrics to Track

| Metric | Why It Matters |
|--------|---------------|
| Execution rate | Throughput over time |
| Error rate per workflow | Not just overall — per-workflow granularity |
| p95 execution time | Where latency is hiding |
| Queue depth | Early warning for capacity problems |
| Token usage (AI workflows) | Cost and performance signal for LLM calls |
| Model response time | Detects prompt bloat and model degradation |

### Minimum Viable Alerting

Three alerts required for any production workflow:
1. Error rate above threshold → named Slack/email channel
2. Execution time above documented baseline
3. Queue depth beyond normal range

Use **Langfuse** for tracing AI model executions at the workflow level.

### Correlation IDs

Pass a `correlationId` through all sub-workflow calls so failures in child workflows
can be traced back to the originating parent execution. Generate it once at the
trigger node using the `$execution.id` or a custom UUID.

---

## Production Environment Variables

```dotenv
# ── Database (PostgreSQL) ─────────────────────────────────────────────────
DB_TYPE=postgresdb                        # MUST be "postgresdb" not "postgres"
DB_POSTGRESDB_HOST=postgres               # Docker service name, NOT localhost
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=<strong_password>
DB_POSTGRESDB_SCHEMA=public
DB_POSTGRESDB_POOL_SIZE=10                # Increase for high-concurrency
DB_POSTGRESDB_CONNECTION_TIMEOUT=30000   # ms
DB_POSTGRESDB_IDLE_CONNECTION_TIMEOUT=60000

# ── Encryption & Auth ─────────────────────────────────────────────────────
N8N_ENCRYPTION_KEY=<long_random_secret>  # Set before first run; never change
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<strong_password>

# ── Instance ─────────────────────────────────────────────────────────────
N8N_HOST=localhost                        # or your public domain
N8N_PORT=5678
N8N_PROTOCOL=http                         # use https in production
WEBHOOK_URL=http://localhost:5678         # must match public host + protocol
GENERIC_TIMEZONE=UTC
TZ=UTC
N8N_DIAGNOSTICS_ENABLED=false

# ── Task Runners (n8n 2.x+) ───────────────────────────────────────────────
N8N_RUNNERS_ENABLED=true
N8N_RUNNERS_MODE=external
N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0
N8N_RUNNERS_AUTH_TOKEN=<runner_token>

# ── Execution Retention ───────────────────────────────────────────────────
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=none      # reduce storage; keep errors only
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=336              # hours (14 days)

# ── Logging ───────────────────────────────────────────────────────────────
N8N_LOG_LEVEL=info                        # options: debug, info, warn, error
N8N_METRICS=true                          # enable /metrics endpoint
```

---

## Upgrade & Backup Procedures

### Backup

```bash
# Backup PostgreSQL
docker exec -t n8n-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > n8n_$(date +%F).sql

# Backup n8n local data volume (encryption key metadata)
docker run --rm -v n8n_data:/data alpine \
  tar czf - -C / data > n8n_data_$(date +%F).tgz
```

### Upgrade

```bash
# 1. Take backups first
# 2. Pin the new version in docker-compose.yml
# 3. Pull and recreate
docker compose pull n8n
docker compose up -d n8n
docker compose logs -f n8n   # watch for DB migrations
```

---

## Pre-Deploy Checklist

- [ ] Happy path tested with real-shape payloads (not clean dummy data)
- [ ] Failure paths explicitly tested: bad input, auth failure, API timeout, empty results
- [ ] Workflow JSON inspected: credentials are IDs, retry configs active, Error Trigger wired
- [ ] Workflow exported and committed to Git
- [ ] Rollback plan documented and practiced (< 10 min)
- [ ] High-risk workflows reviewed by a second person
- [ ] First production execution monitored in real time

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| `DB_TYPE=postgres` (wrong) | Must be `DB_TYPE=postgresdb` |
| `DB_POSTGRESDB_HOST=localhost` | Use Docker service name: `postgres` |
| Missing `N8N_ENCRYPTION_KEY` | Set before first run; unrecoverable if lost |
| Hardcoded secrets in Code nodes | Always use Credential Manager |
| No Error Trigger configured | Wire every critical workflow to a global error handler |
| Pointing Ollama credential at `localhost` from Docker | Use `http://ollama:11434` (Docker network) |
| Raw AI output passed to action | Apply `generate → validate → act` with Guardrails node |
