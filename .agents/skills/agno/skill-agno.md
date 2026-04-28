---
name: agno
version: 1.0.0
description: >
  Agent skill for the Agno Python agent SDK — covering agent construction,
  tool authoring, Teams and multi-agent orchestration, memory and storage,
  knowledge bases, structured outputs, reasoning, async/streaming, and
  production deployment via AgentOS. Sourced from official Agno docs and
  verified 2025–2026 usage.
---

# Agno Agent Skill

## Overview

Agno is an open-source Python framework for building, running, and managing AI agents
at scale. Its architecture has three layers:

| Layer | Purpose | Key Class |
|-------|---------|-----------|
| **SDK** | Define agents, tools, memory, knowledge, Teams | `Agent`, `Team`, `Toolkit` |
| **Runtime (AgentOS)** | Serve agents as a stateless FastAPI service | `AgentOS` |
| **Control Plane** | Monitor and manage via app.agno.com UI | Cloud dashboard |

Install:
```bash
pip install agno
```

---

## Agent Construction

### Minimal Agent

```python
from agno.agent import Agent
from agno.models.google import Gemini

agent = Agent(
    model=Gemini(id="gemini-2.5-flash"),
    description="You are a concise assistant.",
    markdown=True,
)
agent.print_response("Summarise the Agno framework in 3 bullets", stream=True)
```

### Full Agent Constructor Reference

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.memory import MemoryManager
from agno.models.google import Gemini

db = SqliteDb(db_file="tmp/agents.db")

agent = Agent(
    # ── Identity ─────────────────────────────────────────────────────────
    name="Analytics Agent",
    description="Expert data analyst with SQL and Python skills.",

    # ── Model ─────────────────────────────────────────────────────────────
    model=Gemini(id="gemini-2.5-flash"),

    # ── Instructions ──────────────────────────────────────────────────────
    # Use a list of strings — each item is a separate instruction bullet.
    # More structured and easier to edit than a single prompt string.
    instructions=[
        "Think step-by-step before answering.",
        "Always cite the data source in your response.",
        "Return results as markdown tables where possible.",
    ],

    # ── Tools ─────────────────────────────────────────────────────────────
    tools=[],                       # list of Toolkit instances or @tool functions
    show_tool_calls=True,           # show tool call details in output (dev mode)

    # ── Session Storage ───────────────────────────────────────────────────
    db=db,                          # persists conversation history by session_id
    add_history_to_context=True,    # inject past turns into context
    num_history_runs=5,             # how many past runs to include

    # ── User Memory ───────────────────────────────────────────────────────
    memory_manager=MemoryManager(model=Gemini(id="gemini-2.5-flash"), db=db),
    enable_agentic_memory=True,     # agent decides when to store/retrieve memories
    # update_memory_on_run=True,    # alternative: always update after every run

    # ── Output ────────────────────────────────────────────────────────────
    markdown=True,
    # output_schema=MyPydanticModel, # enforce structured output (see below)

    # ── Context ───────────────────────────────────────────────────────────
    add_datetime_to_context=True,

    # ── Reasoning ─────────────────────────────────────────────────────────
    # reasoning=True,               # enable full Reasoning Agent (see below)
)
```

### Model Providers

```python
from agno.models.google import Gemini          # Gemini / Vertex AI
from agno.models.anthropic import Claude       # Anthropic
from agno.models.openai import OpenAIResponses # OpenAI
from agno.models.ollama import Ollama          # Local via Ollama

# Gemini via Vertex AI (service account auth via ADC)
model = Gemini(
    id="gemini-2.5-flash",
    vertexai=True,
    project_id="my-gcp-project",
    location="us-central1",
)

# Ollama (local)
model = Ollama(id="llama3.2")

# Never instantiate the same model object in two agents —
# Agno stores response_model on the instance; sharing causes bleeds.
```

---

## Running Agents

```python
# Synchronous — returns RunResponse
response = agent.run("Analyse the SQL query performance", session_id="session-1")
print(response.content)

# Synchronous with streaming output to stdout
agent.print_response("...", session_id="session-1", stream=True)

# Async
import asyncio
response = asyncio.run(agent.arun("...", session_id="session-1"))

# Async streaming
async def main():
    async for chunk in await agent.astream("..."):
        print(chunk.content, end="", flush=True)
```

Pass `session_id` consistently to maintain conversation history.
Pass `user_id` consistently to maintain per-user long-term memory.

---

## Tools

### Any Python Function as a Tool

Pass any function directly — Agno infers the schema from the type annotations and
docstring:

```python
import psycopg2
from agno.agent import Agent

def run_sql_query(query: str) -> str:
    """Execute a read-only SQL query and return results as a markdown table."""
    conn = psycopg2.connect("postgresql://user:pass@postgres:5432/mydb")
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = "\n".join("| " + " | ".join(str(c) for c in row) + " |" for row in rows)
    return f"{header}\n{sep}\n{body}"

agent = Agent(tools=[run_sql_query], ...)
```

### `@tool` Decorator

Use `@tool` for fine-grained control over caching, result display, and early exit:

```python
from agno.tools import tool
from agno.agent import Agent

@tool(
    show_result=True,           # display tool result in streamed output
    stop_after_tool_call=False, # set True to halt agent after this call
    cache_results=True,         # cache identical inputs (same args → same result)
)
def get_schema_summary(table_name: str) -> str:
    """Return the column names and types for the given Postgres table."""
    # implementation
    ...

agent = Agent(tools=[get_schema_summary], ...)
```

### Toolkit Class (grouping related tools)

```python
from agno.tools import Toolkit
from agno.tools import tool

class RailsDbTools(Toolkit):
    def __init__(self, db_url: str):
        super().__init__(name="RailsDbTools")
        self.db_url = db_url
        self.register(self.list_tables)
        self.register(self.describe_table)
        self.register(self.run_query)

    def list_tables(self) -> str:
        """List all tables in the Rails application database."""
        ...

    def describe_table(self, table_name: str) -> str:
        """Return schema definition for a specific table."""
        ...

    def run_query(self, sql: str) -> str:
        """Execute a read-only SELECT query and return results."""
        ...

agent = Agent(tools=[RailsDbTools(db_url="postgresql://...")], ...)
```

### Built-in Tools (selective reference)

| Import | Purpose |
|--------|---------|
| `agno.tools.mcp.MCPTools` | Connect to any MCP server |
| `agno.tools.duckduckgo.DuckDuckGoTools` | Web search |
| `agno.tools.reasoning.ReasoningTools` | `think()` + `analyze()` scratchpad |
| `agno.tools.yfinance.YFinanceTools` | Financial data |
| `agno.tools.arxiv.ArxivTools` | Academic paper search |
| `agno.tools.hackernews.HackerNewsTools` | HN stories |

---

## Memory vs Storage

Agno distinguishes two separate persistence concerns:

| Concept | What it stores | Scope | Key param |
|---------|---------------|-------|-----------|
| **Storage** (`db=`) | Conversation turns (messages) | Per `session_id` | `add_history_to_context=True` |
| **Memory** (`memory_manager=`) | Extracted user facts ("user prefers dark mode") | Per `user_id` across sessions | `enable_agentic_memory=True` |

```python
from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb

# Development
db = SqliteDb(db_file="tmp/agents.db")

# Production
db = PostgresDb(db_url="postgresql+psycopg://user:pass@postgres:5432/agno")
```

> Use `PostgresDb` in production — it is the same Postgres instance already in the
> Docker Compose stack. Create a dedicated `agno` schema or database to keep it
> separate from Rails data.

---

## Structured Output

```python
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.google import Gemini

class QueryAnalysis(BaseModel):
    query_intent: str = Field(description="What the SQL query is trying to do")
    tables_used: list[str]
    estimated_complexity: str = Field(description="low | medium | high")
    suggested_index: str | None = None

agent = Agent(
    model=Gemini(id="gemini-2.5-flash"),
    output_schema=QueryAnalysis,   # preferred over legacy response_model
)

response = agent.run("Analyse this query: SELECT * FROM users JOIN orders ...")
analysis: QueryAnalysis = response.content   # fully typed Pydantic object
```

**Rules for reliable structured output:**
- Use `output_schema` (not `response_model`) — current API
- Include `Field(description=...)` on every field — guides the model
- For local Ollama models: also set `temperature=0` and include the JSON schema
  in `instructions` — native structured output support varies by model
- Do **not** share a model instance between agents with different `output_schema`
  definitions — Agno stores the schema on the model object

---

## Reasoning

### Reasoning Tools (recommended — model-agnostic)

```python
from agno.tools.reasoning import ReasoningTools

agent = Agent(
    model=Gemini(id="gemini-2.5-flash"),
    tools=[
        ReasoningTools(add_instructions=True),  # adds think() + analyze() tools
        your_custom_tools_here,
    ],
    show_tool_calls=True,
)
```

The agent decides when to invoke `think()` and `analyze()`. Works with any model.
Use this for: analytical pipelines, multi-step data tasks, debugging workflows.

### Reasoning Agent (full chain-of-thought loop)

```python
agent = Agent(
    model=Gemini(id="gemini-2.5-flash"),
    reasoning=True,      # spawns a separate reasoning sub-agent; higher latency
    reasoning_model=Gemini(id="gemini-2.5-pro"),  # optional: stronger model for reasoning
)
```

Runs a 6-step framework (analyse → decompose → plan → execute → validate → answer)
up to 10 iterations. Use for complex, multi-step problems where you need full
chain-of-thought. Adds latency — do not use for simple tasks.

---

## Teams (Multi-Agent)

```python
from agno.agent import Agent
from agno.team import Team, TeamMode
from agno.models.google import Gemini
from agno.models.ollama import Ollama

# Specialist agents
schema_agent = Agent(
    name="Schema Agent",
    role="Extract and describe database schema structure.",
    model=Ollama(id="llama3.2"),   # local model for fast, simple tasks
    tools=[describe_schema_tool],
)

analysis_agent = Agent(
    name="Analysis Agent",
    role="Analyse query performance and suggest optimisations.",
    model=Gemini(id="gemini-2.5-pro"),  # cloud model for deep reasoning
    tools=[run_explain_tool, run_query_tool],
    reasoning=True,
)

team = Team(
    name="DB Analysis Team",
    mode=TeamMode.coordinate,   # default: leader delegates + synthesises
    model=Gemini(id="gemini-2.5-flash"),
    members=[schema_agent, analysis_agent],
    instructions=[
        "Delegate schema questions to Schema Agent.",
        "Delegate performance analysis to Analysis Agent.",
        "Synthesise results into a single structured report.",
    ],
    db=db,
    add_history_to_context=True,
    num_history_runs=3,
    store_member_responses=True,     # persist member outputs
    share_member_interactions=True,  # members can see each other's context
    markdown=True,
)

team.print_response("Why is this query slow? ...", stream=True)
```

### Team Modes

| Mode | Behaviour | Use When |
|------|-----------|---------|
| `coordinate` (default) | Leader decomposes, delegates, synthesises | General multi-step tasks |
| `route` | Leader routes to a single best-fit member | Task classification + dispatch |
| `broadcast` | Same task sent to all members; results synthesised | Parallel research/analysis |
| `tasks` | Work broken into discrete trackable units | Long pipelines with clear stages |

---

## Knowledge Bases

```python
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector

# Production: same Postgres instance — use pgvector extension
knowledge = Knowledge(
    vector_db=PgVector(
        table_name="agent_knowledge",
        db_url="postgresql+psycopg://user:pass@postgres:5432/n8n",
    )
)

# Development: local LanceDB (no DB setup required)
from agno.vectordb.lancedb import LanceDb
knowledge = Knowledge(
    vector_db=LanceDb(table_name="knowledge_docs", uri="tmp/lancedb")
)

agent = Agent(
    knowledge=knowledge,
    search_knowledge=True,   # agent uses RAG to search knowledge base
)

# Load documents (run once; re-running is idempotent)
if agent.knowledge:
    agent.knowledge.load()
```

**Always use the same embedding model** for indexing and querying.
PgVector requires the `pgvector` extension — use `agnohq/pgvector:16` or
`pgvector/pgvector:pg16` image in Docker Compose.

---

## AgentOS (Production Serving)

AgentOS wraps agents into a stateless FastAPI application with:
- `/v1/runs` endpoint for agent invocation
- Streaming support
- Session isolation
- Built-in auth hooks

```python
from agno.agent import Agent
from agno.os import AgentOS
from agno.models.google import Gemini

agent = Agent(name="My Agent", model=Gemini(id="gemini-2.5-flash"), ...)

agent_os = AgentOS(
    agents=[agent],
    tracing=True,   # enables request/response tracing
)

app = agent_os.get_app()  # returns a FastAPI app

if __name__ == "__main__":
    agent_os.serve(app="main:app", reload=True)
    # starts uvicorn on http://0.0.0.0:7777
```

**Running in Docker:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7777"]
```

```yaml
# docker-compose.yml addition
  agent:
    build: ./agent
    container_name: ai-agent
    restart: unless-stopped
    ports:
      - "7777:7777"
    environment:
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-us-central1}
      - OLLAMA_HOST=http://ollama:11434
      - DB_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    networks:
      - ai-network
```

---

## Environment Variables

```dotenv
# Google Gemini (direct API)
GOOGLE_API_KEY=your_key

# Vertex AI (preferred in GCP environments; uses ADC)
GOOGLE_CLOUD_PROJECT=my-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json  # or use Workload Identity

# Anthropic
ANTHROPIC_API_KEY=your_key

# OpenAI
OPENAI_API_KEY=your_key

# Ollama (when running in Docker alongside agent)
# No key needed; just set base_url in model constructor
OLLAMA_HOST=http://ollama:11434  # consumed by agno.models.ollama.Ollama
```

---

## Project Structure (Recommended)

```
agents/
├── __init__.py
├── models.py          # Pydantic output schemas (shared)
├── tools/
│   ├── __init__.py
│   ├── rails_db.py    # RailsDbTools Toolkit
│   └── analysis.py    # analysis helper tools
├── agents/
│   ├── __init__.py
│   ├── schema_agent.py
│   └── analysis_agent.py
├── teams/
│   └── db_analysis_team.py
└── main.py            # AgentOS entrypoint
```

One agent per file. Import and compose in `teams/` and `main.py`.

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Sharing a model instance across agents | Instantiate a new model object per agent |
| `response_model` vs `output_schema` | Use `output_schema` — current API; `response_model` is legacy |
| Ollama model ignoring `output_schema` | Add JSON schema to `instructions`; set `temperature=0` |
| Memory not persisting across restarts | Switch from `SqliteDb` to `PostgresDb` in production |
| `session_id` not passed on second turn | Always pass the same `session_id` to maintain history |
| Reasoning agent on every request | Use `ReasoningTools` instead — only reasons when needed |
| `enable_agentic_memory=True` + high traffic | Switch to `update_memory_on_run=True` for guaranteed capture |
| Mixing Vertex AI + direct Gemini API | Set `vertexai=True` on the `Gemini` model object; uses ADC |
| AgentOS serving on `localhost` in Docker | Bind to `0.0.0.0` via `agent_os.serve(host="0.0.0.0")` |
| Same `user_id` for all users | Use distinct `user_id` per user; memory is user-scoped |
