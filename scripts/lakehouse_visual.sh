#!/bin/bash
# Ensure execution from project root
if [ -f "../docker-compose-visual.yml" ]; then
    cd ..
fi

echo "Starting Lakehouse Visualization & Monitoring (Superset, OpenSearch, Grafana, Streamlit)..."
docker compose -f docker-compose-visual.yml up -d
