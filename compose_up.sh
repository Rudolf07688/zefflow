#!/bin/bash

# This script is intended to be run inside the dev container to start up the Docker Compose services.

user_args=("$@")

# help message
if [[ " ${user_args[*]} " == *" --help "* ]]; then
    echo "Usage: compose_up.sh [options]"
    echo "Options:"
    echo "  --help    Show this help message and exit"
    exit 0
fi

# up
echo "[$(date)] | Starting up Docker Compose services..."
docker-compose -f /workspaces/zefflow/docker-compose.yml up -d

# confirm
echo "[$(date)] | Docker Compose services started. Checking status..."
docker-compose -f /workspaces/zefflow/docker-compose.yml ps
