#!/usr/bin/env bash
set -euo pipefail

CH_HOST="${CH_HOST:-localhost}"
CH_PORT="${CH_PORT:-8123}"

echo "[INFO] Applying ClickHouse schema to ${CH_HOST}:${CH_PORT} ..."
curl -sS "http://${CH_HOST}:${CH_PORT}/" --data-binary @infra/clickhouse_init.sql > /dev/null
echo "[OK] ClickHouse schema applied."
