#!/bin/bash
# Ensure execution from project root
if [ -f "../docker-compose.yml" ]; then
    cd ..
fi

# Create shared network if it doesn't exist
if [ -z "$(docker network ls -q -f name=lakehouse-net)" ]; then
    echo "Creating network: lakehouse-net"
    docker network create lakehouse-net
fi

echo "Starting Lakehouse Infrastructure (Storage, Metadata, Compute)..."
docker compose up -d
