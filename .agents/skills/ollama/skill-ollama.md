---
name: ollama
version: 1.0.0
description: >
  Agent skill for Ollama — covering model management, API usage, Modelfiles,
  structured outputs, environment configuration, memory management, GPU setup,
  and production integration patterns. Sourced from official Ollama docs and
  verified 2025–2026 production usage.
---

# Ollama Agent Skill

## Overview

Ollama is a cross-platform LLM runtime that packages model weights, configuration, and
serving logic into a single local API server. It exposes an OpenAI-compatible REST API
at `http://localhost:11434` and can be deployed via Docker. It supports NVIDIA, AMD, and
Apple Silicon GPUs out of the box.

---

## Core API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate` | POST | Single-turn text generation |
| `/api/chat` | POST | Multi-turn conversation |
| `/api/embed` | POST | Generate embeddings |
| `/api/pull` | POST | Download a model |
| `/api/push` | POST | Push model to registry |
| `/api/show` | POST | Show model info |
| `/api/tags` | GET | List available models |
| `/api/delete` | DELETE | Remove a model |
| `/api/ps` | GET | List models currently loaded |

### Chat Request (OpenAI-compatible)

```bash
curl http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Summarize this in 3 bullet points: ..."}
    ],
    "stream": false,
    "options": {
      "temperature": 0.2,
      "num_ctx": 8192
    }
  }'
```

### OpenAI-Compatible Endpoint

Ollama also exposes `/v1/chat/completions` for drop-in OpenAI SDK compatibility:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
response = client.chat.completions.create(
    model="llama3.2",
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## Model Management

### Essential Commands

```bash
ollama pull llama3.2              # download a model
ollama pull nomic-embed-text      # embedding model
ollama list                       # list available models
ollama ps                         # show loaded models + processor type
ollama show llama3.2              # show model metadata
ollama show --modelfile llama3.2  # dump Modelfile
ollama rm llama3.2                # delete a model
ollama run llama3.2               # interactive REPL
ollama stop llama3.2              # unload from memory immediately
```

### Checking GPU Usage

```bash
ollama ps
# NAME             ID        SIZE   PROCESSOR   UNTIL
# llama3.2:latest  abc123    4.7GB  100% GPU    5 minutes from now
```

The `PROCESSOR` column indicates:
- `100% GPU` — fully in VRAM (fastest)
- `100% CPU` — fully in system RAM (slower)
- `48%/52% CPU/GPU` — split (partial offload, common on constrained VRAM)

---

## Modelfile Reference

A Modelfile defines a model's base, system prompt, parameters, and few-shot examples.
Modelfiles are **not case-sensitive**; instructions can appear in any order.

### Syntax

```
# comment
INSTRUCTION arguments
```

### All Instructions

| Instruction | Required | Description |
|-------------|----------|-------------|
| `FROM` | ✅ Yes | Base model (registry name, GGUF path, or Safetensors dir) |
| `PARAMETER` | No | Runtime parameters (temperature, num_ctx, stop tokens, etc.) |
| `SYSTEM` | No | System prompt baked into the model |
| `TEMPLATE` | No | Custom chat template (Go template syntax) |
| `ADAPTER` | No | QLoRA / LoRA adapter path |
| `MESSAGE` | No | Few-shot conversation history |
| `LICENSE` | No | Legal license text |
| `REQUIRES` | No | Minimum Ollama version |

### PARAMETER Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature` | float | 0.8 | Creativity (0=deterministic, 2=max creative) |
| `num_ctx` | int | 2048 | Context window size in tokens |
| `top_k` | int | 40 | Reduce nonsense — lower = more conservative |
| `top_p` | float | 0.9 | Nucleus sampling threshold |
| `min_p` | float | 0.0 | Minimum token probability relative to top token |
| `repeat_penalty` | float | 1.1 | Penalize repeated tokens |
| `repeat_last_n` | int | 64 | How far back to check for repeats (-1 = num_ctx) |
| `num_predict` | int | -1 | Max tokens to generate (-1 = unlimited) |
| `seed` | int | 0 | Fixed seed for reproducible outputs |
| `stop` | string | — | Stop sequence(s); add multiple PARAMETER stop lines |

### Example Modelfile: Production AI Agent

```dockerfile
FROM llama3.2

# Deterministic structured outputs
PARAMETER temperature 0.0
PARAMETER num_ctx 16384
PARAMETER repeat_penalty 1.05
PARAMETER top_k 20
PARAMETER top_p 0.85

SYSTEM """
You are a JSON-only data extraction assistant.
Always respond with valid JSON matching the provided schema.
Never add explanation, markdown formatting, or preamble.
If you cannot extract the requested data, return {"error": "reason"}.
"""

# Few-shot examples to anchor behavior
MESSAGE user Extract name and age from: "John is 30 years old"
MESSAGE assistant {"name": "John", "age": 30}

MESSAGE user Extract name and age from: "Hello there!"
MESSAGE assistant {"error": "No name or age found in input"}
```

```bash
ollama create json-extractor -f ./Modelfile
ollama run json-extractor  # test interactively
```

---

## Structured Outputs

Ollama supports JSON Schema-constrained outputs via the `format` field (v0.5+).
The model is forced to produce output conforming to the schema.

### REST API

```bash
curl http://localhost:11434/api/chat \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Tell me about Canada"}],
    "stream": false,
    "format": {
      "type": "object",
      "properties": {
        "name":      {"type": "string"},
        "capital":   {"type": "string"},
        "languages": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["name", "capital", "languages"]
    }
  }'
```

### Python with Pydantic (recommended)

```python
from ollama import chat
from pydantic import BaseModel

class CountryInfo(BaseModel):
    name: str
    capital: str
    languages: list[str]
    population_millions: float

response = chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "Tell me about Canada"}],
    format=CountryInfo.model_json_schema(),
    options={"temperature": 0}   # deterministic for structured output
)
data = CountryInfo.model_validate_json(response.message.content)
```

**Tips for reliable structured outputs:**
- Set `temperature: 0` for deterministic schema compliance
- Include the JSON schema as a string in the system/user prompt to ground the model
- Use Pydantic (Python) or Zod (JavaScript) schemas — they are reusable for validation
- Structured outputs also work via the OpenAI-compatible `/v1/chat/completions` endpoint
  using `response_format`

---

## Memory Management

### Keep-Alive

By default, Ollama unloads a model 5 minutes after the last request.
Cold-start for a 7B model typically costs 3–10 seconds.

**Set globally via environment variable:**
```
OLLAMA_KEEP_ALIVE=1h    # keep all models loaded for 1 hour after last use
OLLAMA_KEEP_ALIVE=-1    # keep loaded indefinitely (until restart)
OLLAMA_KEEP_ALIVE=0     # unload immediately after each request
```

**Override per request:**
```bash
# Keep loaded indefinitely
curl http://localhost:11434/api/chat \
  -d '{"model":"llama3.2","messages":[...],"keep_alive": -1}'

# Unload immediately after this request (free VRAM)
curl http://localhost:11434/api/chat \
  -d '{"model":"llama3.2","messages":[...],"keep_alive": 0}'
```

### Model Preloading

Send a warmup request at startup with `keep_alive: -1`:

```python
import requests, time

def wait_for_ollama(timeout=30):
    for _ in range(timeout):
        try:
            requests.get("http://localhost:11434", timeout=1)
            return True
        except:
            time.sleep(1)
    return False

def preload(model: str):
    requests.post("http://localhost:11434/api/generate",
        json={"model": model, "prompt": " ", "stream": False, "keep_alive": -1})
    print(f"{model} preloaded")

if wait_for_ollama():
    preload("llama3.2")
    preload("nomic-embed-text")   # always preload embedding model for RAG
```

### Strategy by Use Case

| Scenario | Recommended Setting |
|----------|-------------------|
| Interactive chat app | `OLLAMA_KEEP_ALIVE=1h` + preload primary model at startup |
| Batch processing pipeline | Default `5m`; first batch pays load cost; model unloads between batches |
| Multi-model RAG | `OLLAMA_MAX_LOADED_MODELS=2` + preload both chat and embedding models |
| Low VRAM (≤8 GB) | Default `5m`; only preload one model; avoid simultaneous loading |

---

## Concurrency & Parallelism

```
OLLAMA_NUM_PARALLEL       # max parallel requests per model (default: 1)
                          # each parallel slot multiplies context memory usage
                          # e.g. OLLAMA_NUM_PARALLEL=4 + 2K ctx = 8K context allocated

OLLAMA_MAX_LOADED_MODELS  # max models in memory simultaneously
                          # default: 3 × GPU count (or 3 for CPU)
                          # set to 1 on memory-constrained systems

OLLAMA_MAX_QUEUE          # max queued requests before 503 (default: 512)
                          # increase for bursty batch workloads

OLLAMA_CONTEXT_LENGTH     # global default context window override
```

**Balancing act:**
- Increasing `OLLAMA_NUM_PARALLEL` reserves more memory per model
- Increasing `OLLAMA_MAX_LOADED_MODELS` spreads VRAM across more models
- On a single 24 GB GPU: `OLLAMA_MAX_LOADED_MODELS=2` + `OLLAMA_NUM_PARALLEL=2` is
  a reliable starting point. Adjust based on `ollama ps` VRAM readings.

**Design at infrastructure level:** Set `OLLAMA_KEEP_ALIVE` and `OLLAMA_MAX_LOADED_MODELS`
via environment variable rather than relying on individual applications to coordinate
their per-request `keep_alive` settings.

---

## Environment Variables Reference

```dotenv
# ── Server ────────────────────────────────────────────────────────────────
OLLAMA_HOST=0.0.0.0:11434          # bind address (default: 127.0.0.1:11434)
OLLAMA_ORIGINS=*                   # allowed CORS origins; use specific origins in prod
OLLAMA_MODELS=/root/.ollama/models # model storage path

# ── Memory & Concurrency ─────────────────────────────────────────────────
OLLAMA_KEEP_ALIVE=5m               # model unload timeout; -1 = never, 0 = immediate
OLLAMA_NUM_PARALLEL=1              # parallel requests per model
OLLAMA_MAX_LOADED_MODELS=1         # models in memory simultaneously (0 = unlimited)
OLLAMA_MAX_QUEUE=512               # request queue depth before 503

# ── Context ───────────────────────────────────────────────────────────────
OLLAMA_CONTEXT_LENGTH=4096         # global default context window

# ── Performance ───────────────────────────────────────────────────────────
OLLAMA_FLASH_ATTENTION=1           # enable Flash Attention (reduces memory at large ctx)
OLLAMA_KV_CACHE_TYPE=q8_0          # KV cache quantization: f16 | q8_0 | q4_0
                                   # q8_0 ≈ half memory of f16, minimal quality loss
                                   # only effective when OLLAMA_FLASH_ATTENTION=1

# ── GPU ───────────────────────────────────────────────────────────────────
OLLAMA_GPU_OVERHEAD=2147483648     # reserve VRAM bytes for OS/other processes
OLLAMA_SCHED_SPREAD=true           # spread load across multiple GPUs
# OLLAMA_INTEL_GPU=1               # enable Intel GPU (experimental)

# ── Proxy ─────────────────────────────────────────────────────────────────
HTTPS_PROXY=https://proxy.example.com  # model downloads go through proxy
# Do NOT set HTTP_PROXY — Ollama uses HTTPS for pulls; HTTP_PROXY breaks clients

# ── Privacy ───────────────────────────────────────────────────────────────
OLLAMA_NO_CLOUD=1                  # disable cloud model features (fully local)
```

---

## GPU Setup (Docker / Linux)

### NVIDIA (Linux + WSL2)

**Prerequisites on host:**
```bash
# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:11.5.2-base-ubuntu20.04 nvidia-smi
```

**Docker Compose GPU reservation (modern pattern):**
```yaml
services:
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all          # or count: 1 / device_ids: ["0"]
              capabilities: [gpu]
```

> ⚠️ Avoid the legacy `runtime: nvidia` pattern — it fails on newer Docker setups.
> Use `deploy.resources.reservations.devices` instead.

### AMD GPU (Linux)

```yaml
services:
  ollama:
    image: ollama/ollama:rocm
    devices:
      - /dev/kfd
      - /dev/dri
    group_add:
      - video
```

### Apple Silicon (macOS)

GPU passthrough is not available in Docker Desktop on macOS. Options:
1. Run Ollama natively on macOS (`brew install ollama` or .dmg installer)
2. Point n8n/other containers at `http://host.docker.internal:11434`

---

## Embedding Models

| Model | Dimensions | Best For |
|-------|-----------|---------|
| `nomic-embed-text` | 768 | General text; fast; recommended default |
| `mxbai-embed-large` | 1024 | Higher quality; more VRAM |
| `all-minilm` | 384 | Ultra-fast; low resource |

```bash
# Generate embeddings via REST
curl http://localhost:11434/api/embed \
  -d '{"model": "nomic-embed-text", "input": "The sky is blue"}'
```

Always use the **same embedding model** for both indexing and querying.
Mixing models will produce meaningless similarity scores.

---

## Recommended Models by Use Case

| Use Case | Recommended Model | Notes |
|----------|------------------|-------|
| General chat / agents | `llama3.2:3b` / `llama3.2:8b` | Fast; solid reasoning |
| Code generation | `qwen2.5-coder:7b` | Strong code quality |
| Long context tasks | `gemma3:12b` | Up to 128K context |
| Embedding (RAG) | `nomic-embed-text` | Best perf/resource ratio |
| Structured extraction | `llama3.2` + `format` field | Use temperature 0 |
| Resource-constrained | `llama3.2:1b` / `phi4-mini` | Sub-2GB VRAM |

Always pin a specific tag (e.g., `llama3.2:3b`) rather than `latest` in production.
Model providers update default versions silently.

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Cold start latency on every request | Set `OLLAMA_KEEP_ALIVE=-1` + preload at startup |
| `OLLAMA_HOST=0.0.0.0` on host but containers can't reach it | In Docker, service name is the hostname; set `OLLAMA_HOST=0.0.0.0:11434` in container |
| GPU not being used | Run `ollama ps` and check PROCESSOR column; verify NVIDIA toolkit + deploy.resources.reservations |
| Two 7B models OOM on 8 GB VRAM | Lower `OLLAMA_MAX_LOADED_MODELS=1`; let Ollama swap on demand |
| `runtime: nvidia` Compose error | Switch to `deploy.resources.reservations.devices` pattern |
| Mixing embedding models | Always use identical model for indexing and querying |
| Non-deterministic structured output | Set `temperature: 0` when using `format` schema |
