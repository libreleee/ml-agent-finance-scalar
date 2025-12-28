#!/bin/bash
# Ensure execution from project root
if [ -f "../docker-compose-mlops.yml" ]; then
    cd ..
fi

echo "Stopping MLOps Stack..."
docker compose -f docker-compose-mlops.yml down
