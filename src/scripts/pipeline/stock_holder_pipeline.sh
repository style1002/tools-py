#!/bin/bash
set -euo pipefail

# 用法: stock_holder_pipeline.sh <QUERY_DATES> <HOLDING_DATE_REAL> <STOCK_CODES>
# 参数均为逗号分隔；日期格式 YYYY-MM-DD；股票代码为 5 位纯数字（如 00664,06715）
# 示例（单日多股）: stock_holder_pipeline.sh 2026-05-20 2026-05-18 00664,01989
# 示例（多日多股）: stock_holder_pipeline.sh 2026-05-19,2026-05-20 2026-05-18,2026-05-19 00664,01989

join_csv() {
  local IFS=,
  echo "$*"
}

trim_date_arrays() {
  local i
  for i in "${!QUERY_DATES_ARR[@]}"; do
    QUERY_DATES_ARR[$i]="${QUERY_DATES_ARR[$i]// /}"
  done
  for i in "${!HOLDING_DATE_REAL_ARR[@]}"; do
    HOLDING_DATE_REAL_ARR[$i]="${HOLDING_DATE_REAL_ARR[$i]// /}"
  done
}

usage() {
  cat >&2 <<EOF
用法: $0 <QUERY_DATES> <HOLDING_DATE_REAL> <STOCK_CODES>
  三个参数均为必传，逗号分隔：
    QUERY_DATES       - 查询日期（YYYY-MM-DD）
    HOLDING_DATE_REAL - 实际持股日期（YYYY-MM-DD）
    STOCK_CODES       - 股票代码（5位纯数字，如 00664,06715）
示例（单日多股）: $0 2026-05-20 2026-05-18 00664,01989
示例（多日多股）: $0 2026-05-19,2026-05-20 2026-05-18,2026-05-19 00664,01989
EOF
  exit 1
}

if (($# != 3)); then
  echo "❌ 需要 3 个参数，实际传入 $# 个" >&2
  usage
fi

IFS=',' read -r -a QUERY_DATES_ARR <<< "$1"
IFS=',' read -r -a HOLDING_DATE_REAL_ARR <<< "$2"
IFS=',' read -r -a STOCK_CODES_ARR <<< "$3"
trim_date_arrays

if ((${#QUERY_DATES_ARR[@]} != ${#HOLDING_DATE_REAL_ARR[@]})); then
  echo "❌ QUERY_DATES 与 HOLDING_DATE_REAL 元素个数不一致: ${#QUERY_DATES_ARR[@]} != ${#HOLDING_DATE_REAL_ARR[@]}" >&2
  exit 1
fi

if ((${#STOCK_CODES_ARR[@]} == 0)); then
  echo "❌ STOCK_CODES 不能为空" >&2
  exit 1
fi

export QUERY_DATES="$(join_csv "${QUERY_DATES_ARR[@]}")"
export HOLDING_DATE_REAL="$(join_csv "${HOLDING_DATE_REAL_ARR[@]}")"
QUERY_SCRIPT="/Users/wangwei/PythonProject/tools-py/src/scripts/stock/get_stock_holder.py"
INSERT_SCRIPT="/Users/wangwei/PythonProject/tools-py/out/scripts/stock/insert_to_pg.sh"
PYTHON_VENV="/Users/wangwei/PythonProject/tools-py/.venv/bin/python"

# 第一步：查询数据，构建 SQL 语句
for code in "${STOCK_CODES_ARR[@]}"; do
  STOCK_CODE="$code" "$PYTHON_VENV" "$QUERY_SCRIPT"
done

# 第二步：插入数据至 DB（按每个 QUERY_DATE 循环）
for query_date in "${QUERY_DATES_ARR[@]}"; do
  INSERT_D="${query_date//-/}"
  INSERT_YM="${INSERT_D:0:4}-${INSERT_D:4:2}"
  for code in "${STOCK_CODES_ARR[@]}"; do
    "$INSERT_SCRIPT" "$code" "$INSERT_YM" "$INSERT_D"
  done
done
