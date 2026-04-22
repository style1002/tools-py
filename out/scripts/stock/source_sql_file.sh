#!/usr/bin/env bash
# 在 postgres 容器中执行某股票目录下全部 .sql：
# 先顶层（常见为 price），再子目录（常见为 brokers 按月），避免按路径字典序时子目录名排在文件名前。
set -euo pipefail

CONTAINER="${1:-postgres}"
CODE="${2:-02687}"
ROOT="/tmp/scripts/stock/${CODE}"
PSQL_BASE_CMD=(docker exec "${CONTAINER}" psql -U postgres -d stock -v ON_ERROR_STOP=1)
total=0
success=0
failed=0

echo "container: ${CONTAINER}"
echo "root:      ${ROOT}"

docker exec "${CONTAINER}" test -d "${ROOT}" || {
  echo "目录不存在: ${ROOT}"
  exit 1
}

run_sql_file() {
  local file="$1"
  ((total += 1))
  echo "执行文件: ${file}"
  if "${PSQL_BASE_CMD[@]}" -f "${file}"; then
    ((success += 1))
    echo "结果: SUCCESS - ${file}"
  else
    ((failed += 1))
    echo "结果: FAILED  - ${file}"
    exit 1
  fi
}

# 先执行顶层 SQL 文件
# 注意：当顶层没有匹配文件时，[ -e "$f" ] 会返回 1；这里显式 `true`，避免 set -e 提前退出。
top_files="$(docker exec "${CONTAINER}" sh -lc "for f in \"${ROOT}\"/*.sql; do [ -e \"\$f\" ] && printf '%s\n' \"\$f\"; done; true")"
if [[ -n "${top_files}" ]]; then
  while IFS= read -r file; do
    [[ -n "${file}" ]] || continue
    run_sql_file "${file}"
  done <<< "${top_files}"
fi

# 再执行子目录 SQL 文件
sub_files="$(docker exec "${CONTAINER}" sh -lc "find \"${ROOT}\" -mindepth 2 -type f -name '*.sql' | LC_ALL=C sort")"
if [[ -n "${sub_files}" ]]; then
  while IFS= read -r file; do
    [[ -n "${file}" ]] || continue
    run_sql_file "${file}"
  done <<< "${sub_files}"
fi

if [[ "${total}" -eq 0 ]]; then
  echo "未找到任何 SQL 文件: ${ROOT}"
  exit 1
fi

echo "执行完成: total=${total}, success=${success}, failed=${failed}"
