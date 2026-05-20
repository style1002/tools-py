#!/usr/bin/env bash

set -euo pipefail

CODE="${1:0}"
# CODE="${1:-00664}"
# CODE="${1:-01989}"
# CODE="${1:-02635}"
# CODE="${1:-02661}"
# CODE="${1:-03881}"
# CODE="${1:-06651}"

YM="${2:-2026-05}"
D="${3:-20260519}"

PRICE_SQL="/tmp/scripts/stock/${CODE}/stock_${CODE}_price_${D}_${D}.sql"
BROKERS_SQL="/tmp/scripts/stock/${CODE}/${YM}/stock_${CODE}_brokers_${D}.sql"

echo "price:   ${PRICE_SQL}"
echo "brokers: ${BROKERS_SQL}"

docker exec postgres psql -U postgres -d stock \
  -f "${PRICE_SQL}" \
  -f "${BROKERS_SQL}" \
  -c "UPDATE stock_broker_holdings SET stock_name = '諾比侃' WHERE stock_name = '諾比侃(新)';"
