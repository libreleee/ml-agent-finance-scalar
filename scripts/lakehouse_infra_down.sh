#!/bin/bash
# Ensure execution from project root
if [ -f "../docker-compose.yml" ]; then
    cd ..
fi

echo "Stopping Lakehouse Infrastructure..."
docker compose down
