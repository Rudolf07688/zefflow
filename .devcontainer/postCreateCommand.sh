#!/bin/bash

echo "[$(date)] | Running post-create command..."

# General log file for whatever
log_file="/home/general_logs.txt"
mkdir -p $(dirname $log_file)
touch $log_file

log_general () {
    log_message="[$(date)] | $1"
    echo "$log_message" | tee -a $log_file
}

# General env variables
DEBIAN_FRONTEND=noninteractive
export LOG_FILE_GENERAL_PATH=$(realpath $log_file)
export -f log_general

log_general "LOG_FILE_GENERAL_PATH: $LOG_FILE_GENERAL_PATH"

# UV
if [ -z "$UV_VENV_PATH" ]; then
    export UV_VENV_PATH="/home/.uv/venv"
    log_general "UV_VENV_PATH not set. Defaulting to $UV_VENV_PATH"
else
    log_general "UV_VENV_PATH: $UV_VENV_PATH"
fi

if [ -z "/workspaces/zefflow/.venv" ]; then
    log_general "Creating uv .venv..."
    uv venv .venv
fi

log_general "Installing dependencies with uv..."
uv sync
log_general "($uv pip list)"

# Random shit
apt-get update && apt-get install -y curl tree zstd
apt-get upgrade zstd

# Ollama
OLLAMA_BIN="/usr/local/bin/ollama"
install_ollama() {
    log_general "Ollama not found. Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
}

if [ ! -f "$OLLAMA_BIN" ]; then
    if ! install_ollama; then
        log_general "Failed to install Ollama. Please check the error messages above."
        return 1 2>/dev/null || exit 1
    fi
fi

log_general "Ollama available at $OLLAMA_BIN. Please rather run on host and port forward to container for best performance."

# ---------------------------------- Exports --------------------------------- #
log_general "Exporting build context variables..."
export UV_VENV_PATH
export OLLAMA_BIN
export LOG_FILE_GENERAL_PATH
export -f log_general

echo ""
log_general ">> Container lyk vir my mooi bra. Laat ons post start 'n go gee."
