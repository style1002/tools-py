#!/usr/bin/env bash

set -euo pipefail

CODE="${1:0}"
YM="${2:-2026-05}"
D="${3:-20260519}"

PRICE_SQL="/tmp/scripts/stock/${CODE}/stock_${CODE}_price_${D}_${D}.sql"
BROKERS_SQL="/tmp/scripts/stock/${CODE}/${YM}/stock_${CODE}_brokers_${D}.sql"

echo "brokers: ${BROKERS_SQL}"

DOCKER_ARGS=()
if docker exec postgres test -f "${PRICE_SQL}"; then
  DOCKER_ARGS+=(-f "${PRICE_SQL}")
  echo "price:   ${PRICE_SQL}"
fi

if ! docker exec postgres test -f "${BROKERS_SQL}"; then
  echo "❌ 文件不存在: ${BROKERS_SQL}" >&2
  exit 1
fi

DOCKER_ARGS+=(-f "${BROKERS_SQL}")

docker exec postgres psql -U postgres -d stock \
  "${DOCKER_ARGS[@]}" \
  -c "UPDATE stock_broker_holdings SET stock_name = '諾比侃' WHERE stock_name = '諾比侃(新)';"
