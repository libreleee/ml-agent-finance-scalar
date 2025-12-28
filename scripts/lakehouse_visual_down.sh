#!/bin/bash
# Ensure execution from project root
if [ -f "../docker-compose-visual.yml" ]; then
    cd ..
fi

echo "Stopping Lakehouse Visualization & Monitoring..."
docker compose -f docker-compose-visual.yml down
