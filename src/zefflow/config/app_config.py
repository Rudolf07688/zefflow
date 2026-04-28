from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # ── PostgreSQL ────────────────────────────────────────────────────────
    postgres_user: str = Field("n8n", description="PostgreSQL superuser/role used by n8n.")
    postgres_password: str = Field(
        "change_me_strong_password",
        description="Password for postgres_user. Override in .env; never commit a real value.",
    )
    postgres_db: str = Field("n8n", description="Default database created in the Postgres container.")

    # ── n8n → PostgreSQL connection ───────────────────────────────────────
    db_type: str = Field(
        "postgresdb",
        description='n8n DB driver. MUST be "postgresdb" (not "postgres").',
    )
    db_postgresdb_host: str = Field(
        "postgres",
        description="Postgres hostname as seen from n8n. Use the docker-compose service name, not localhost.",
    )
    db_postgresdb_port: int = Field(5432, description="Postgres TCP port.")
    db_postgresdb_database: str = Field("n8n", description="Database name n8n connects to (usually == POSTGRES_DB).")
    db_postgresdb_user: str = Field("n8n", description="Postgres user n8n authenticates as (usually == POSTGRES_USER).")
    db_postgresdb_password: str = Field(
        "change_me_strong_password",
        description="Password n8n uses to connect (usually == POSTGRES_PASSWORD).",
    )
    db_postgresdb_schema: str = Field("public", description="Postgres schema n8n stores its tables in.")
    db_postgresdb_pool_size: int = Field(10, description="Max connections in n8n's Postgres pool.")
    db_postgresdb_connection_timeout: int = Field(
        30000, description="Connection acquisition timeout in milliseconds."
    )
    db_postgresdb_idle_connection_timeout: int = Field(
        60000, description="Idle connection eviction timeout in milliseconds."
    )

    # ── n8n Security ─────────────────────────────────────────────────────
    n8n_encryption_key: str = Field(
        "replace_with_long_random_secret_32chars_min",
        description="Encrypts stored credentials. Must be a stable random string ≥32 chars.",
    )
    n8n_basic_auth_active: bool = Field(True, description="Toggle HTTP basic auth on the n8n editor UI.")
    n8n_basic_auth_user: str = Field("admin", description="Username for n8n basic auth.")
    n8n_basic_auth_password: str = Field("change_me_now", description="Password for n8n basic auth.")

    # ── n8n Instance ─────────────────────────────────────────────────────
    n8n_host: str = Field("localhost", description="Public hostname n8n advertises (used for webhooks/UI).")
    n8n_port: int = Field(5678, description="Port n8n listens on inside the container.")
    n8n_protocol: str = Field("http", description="Protocol n8n advertises in webhook URLs (http or https).")
    webhook_url: str = Field(
        "http://localhost:5678",
        description="Externally reachable base URL for n8n webhooks.",
    )
    generic_timezone: str = Field("UTC", description="Default timezone for n8n schedules and cron triggers.")
    tz: str = Field("UTC", description="Container OS timezone (used by logs and date functions).")
    n8n_diagnostics_enabled: bool = Field(
        False, description="Send anonymous telemetry/diagnostics to n8n. Disabled by default."
    )

    # ── n8n Execution Retention ──────────────────────────────────────────
    executions_data_save_on_error: str = Field(
        "all", description="Which error executions to persist: all | none."
    )
    executions_data_save_on_success: str = Field(
        "none", description="Which successful executions to persist: all | none."
    )
    executions_data_prune: bool = Field(True, description="Enable automatic pruning of old execution data.")
    executions_data_max_age: int = Field(
        336, description="Max age of retained executions, in hours (336 = 14 days)."
    )

    # ── Ollama ────────────────────────────────────────────────────────────
    ollama_image_tag: str = Field(
        "latest", description="Ollama Docker image tag. Pin to a version in production."
    )
    ollama_keep_alive: str = Field(
        "1h", description="How long Ollama keeps a model resident after the last request."
    )
    ollama_num_parallel: int = Field(1, description="Parallel requests served per loaded model.")
    ollama_max_loaded_models: int = Field(
        2, description="Max models held in memory simultaneously (e.g. chat + embedding)."
    )
    ollama_flash_attention: int = Field(
        1, description="Enable FlashAttention to reduce VRAM at large context sizes (1=on, 0=off)."
    )
    ollama_context_length: int = Field(8192, description="Default context window size for Ollama models.")

    # ── Models to auto-pull at startup ───────────────────────────────────
    default_chat_model: str = Field("llama3.2", description="Chat model auto-pulled on container start.")
    default_embed_model: str = Field(
        "nomic-embed-text", description="Embedding model auto-pulled on container start."
    )

    # ── Host override (for Mac users running Ollama natively) ────────────
    ollama_host: str | None = Field(
        None,
        description=(
            "Override Ollama API endpoint. Set to 'host.docker.internal:11434' to use a "
            "Mac-host Ollama daemon (Metal GPU) instead of the in-container one."
        ),
    )

default_app_config = AppConfig()

# # ── PostgreSQL ────────────────────────────────────────────────────────────
# POSTGRES_USER=n8n
# POSTGRES_PASSWORD=change_me_strong_password
# POSTGRES_DB=n8n

# # ── n8n → PostgreSQL connection ───────────────────────────────────────────
# DB_TYPE=postgresdb           # MUST be "postgresdb" — NOT "postgres"
# DB_POSTGRESDB_HOST=postgres  # Docker service name, NOT localhost
# DB_POSTGRESDB_PORT=5432
# DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
# DB_POSTGRESDB_USER=${POSTGRES_USER}
# DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
# DB_POSTGRESDB_SCHEMA=public
# DB_POSTGRESDB_POOL_SIZE=10
# DB_POSTGRESDB_CONNECTION_TIMEOUT=30000
# DB_POSTGRESDB_IDLE_CONNECTION_TIMEOUT=60000

# # ── n8n Security ─────────────────────────────────────────────────────────
# N8N_ENCRYPTION_KEY=replace_with_long_random_secret_32chars_min
# N8N_BASIC_AUTH_ACTIVE=true
# N8N_BASIC_AUTH_USER=admin
# N8N_BASIC_AUTH_PASSWORD=change_me_now

# # ── n8n Instance ─────────────────────────────────────────────────────────
# N8N_HOST=localhost
# N8N_PORT=5678
# N8N_PROTOCOL=http
# WEBHOOK_URL=http=//localhost=5678
# GENERIC_TIMEZONE=UTC
# TZ=UTC
# N8N_DIAGNOSTICS_ENABLED=false

# # ── n8n Execution Retention ───────────────────────────────────────────────
# EXECUTIONS_DATA_SAVE_ON_ERROR=all
# EXECUTIONS_DATA_SAVE_ON_SUCCESS=none
# EXECUTIONS_DATA_PRUNE=true
# EXECUTIONS_DATA_MAX_AGE=336    # 14 days in hours

# # ── Ollama ────────────────────────────────────────────────────────────────
# OLLAMA_IMAGE_TAG=latest        # pin to specific version in production
# OLLAMA_KEEP_ALIVE=1h           # keep models warm between requests
# OLLAMA_NUM_PARALLEL=1          # parallel requests per model
# OLLAMA_MAX_LOADED_MODELS=2     # chat model + embedding model
# OLLAMA_FLASH_ATTENTION=1       # reduce VRAM at large context sizes
# OLLAMA_CONTEXT_LENGTH=8192     # global default context window

# # ── Models to auto-pull at startup ────────────────────────────────────────
# DEFAULT_CHAT_MODEL=llama3.2
# DEFAULT_EMBED_MODEL=nomic-embed-text

# # For Mac users running Ollama natively (not in Docker)=
# # OLLAMA_HOST=host.docker.internal=11434
