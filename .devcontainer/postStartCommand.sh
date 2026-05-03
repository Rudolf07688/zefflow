#!/bin/bash
set -e

echo " -- source post-create command -- "
source ./.devcontainer/postCreateCommand.sh

# functions
run_python() {
    log_general "Running Python command: $1"
    if ! python -c "$1"; then
        log_general "Failed to run Python command: $1"
        return 1 2>/dev/null || exit 1
    fi
}

# give docker a second to start up
sleep 2

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    log_general "Docker is not running."
fi

source .venv/bin/activate
log_general "Activated Python virtual environment."
log_general "UV version: $(uv --version)"
log_general "UV Python: $(uv run python --version)"
log_general "Docker version: $(docker --version)"

if [ -f "/workspaces/zefflow/.venv" ]; then
    log_general "Virtual environment .venv exists. Activating..."
    source .venv/bin/activate

else
    log_general "Virtual environment .venv does not exist. Please check the post-create command for errors."
fi

log_general "Nou laat ons dan in duik hier... Salute en veel sukses met die verdere ontwikkeling van Zefflow!"
