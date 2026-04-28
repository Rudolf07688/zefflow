---
date: 2026-04-28
status: day-0 — no workflows created yet
---

# n8n Workflow Inventory

**Last confirmed with user:** 2026-04-28 (day-0, stack not yet started)

> Rule: never assume a workflow is unchanged since last session. Confirm with user before acting on any entry here.

---

## Known Workflows

_None yet. Stack has not been started and n8n UI has not been opened._

---

## Workflow Template (fill in when user creates or exports a workflow)

| Field | Value |
|-------|-------|
| **Name** | |
| **Trigger** | Manual / Cron (schedule) |
| **Status** | Active / Inactive |
| **Purpose** | |
| **Key nodes** | |
| **Postgres queries** | |
| **LLM calls** | Ollama model or Gemini |
| **Output** | |
| **Last confirmed** | YYYY-MM-DD |

---

## Workflow Design Conventions

- One workflow = one job (sub-workflows preferred over monoliths)
- All triggers: manual or cron — no inbound webhooks
- Rails DB connection: separate Postgres credential from n8n's own DB credential
- Shared filesystem for file I/O: `/data/shared` inside n8n container
- Keep sub-workflow logic documented here once built
