#!/bin/bash
# Ensure execution from project root
if [ -f "../docker-compose-mlops.yml" ]; then
    cd ..
fi

echo "Starting MLOps Stack (Airflow, MLflow, MinIO)..."
docker compose -f docker-compose-mlops.yml up -d
