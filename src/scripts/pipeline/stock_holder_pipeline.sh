#!/bin/bash
set -euo pipefail

# 用法: stock_holder_pipeline.sh [<QUERY_DATES> <HOLDING_DATE_REAL>]
# 日期为逗号分隔数组，格式 YYYY-MM-DD；单日可只写一个元素
# 示例（单日）: stock_holder_pipeline.sh 2026-05-20 2026-05-18
# 示例（多日）: stock_holder_pipeline.sh 2026-05-19,2026-05-20 2026-05-18,2026-05-19
# 不传参则使用下方默认数组；每个 QUERY_DATE 与入库 D 为同一天（YYYY-MM-DD -> YYYYMMDD）

DEFAULT_QUERY_DATES=("2026-06-11")
DEFAULT_HOLDING_DATE_REAL=("2026-06-09")

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
  local default_query default_holding
  default_query="$(join_csv "${DEFAULT_QUERY_DATES[@]}")"
  default_holding="$(join_csv "${DEFAULT_HOLDING_DATE_REAL[@]}")"
  cat >&2 <<EOF
用法: $0 [<QUERY_DATES> <HOLDING_DATE_REAL>]
  两个参数均为逗号分隔的日期数组；不传则使用默认:
    QUERY_DATES=${default_query}
    HOLDING_DATE_REAL=${default_holding}
示例（单日）: $0 2026-05-20 2026-05-18
示例（多日）: $0 2026-05-19,2026-05-20 2026-05-18,2026-05-19
EOF
  exit 1
}

case $# in
  0)
    QUERY_DATES_ARR=("${DEFAULT_QUERY_DATES[@]}")
    HOLDING_DATE_REAL_ARR=("${DEFAULT_HOLDING_DATE_REAL[@]}")
    echo "使用默认日期: QUERY_DATES=$(join_csv "${QUERY_DATES_ARR[@]}") HOLDING_DATE_REAL=$(join_csv "${HOLDING_DATE_REAL_ARR[@]}")"
    ;;
  2)
    IFS=',' read -r -a QUERY_DATES_ARR <<< "$1"
    IFS=',' read -r -a HOLDING_DATE_REAL_ARR <<< "$2"
    trim_date_arrays
    ;;
  *)
    usage
    ;;
esac

if ((${#QUERY_DATES_ARR[@]} != ${#HOLDING_DATE_REAL_ARR[@]})); then
  echo "❌ QUERY_DATES 与 HOLDING_DATE_REAL 元素个数不一致: ${#QUERY_DATES_ARR[@]} != ${#HOLDING_DATE_REAL_ARR[@]}" >&2
  exit 1
fi

export QUERY_DATES="$(join_csv "${QUERY_DATES_ARR[@]}")"
export HOLDING_DATE_REAL="$(join_csv "${HOLDING_DATE_REAL_ARR[@]}")"

STOCK_CODES="00664 01989 02635 02661 03881 06651"
QUERY_SCRIPT="/Users/wangwei/PythonProject/tools-py/src/scripts/stock/get_stock_holder.py"
INSERT_SCRIPT="/Users/wangwei/PythonProject/tools-py/out/scripts/stock/insert_to_pg.sh"
PYTHON_VENV="/Users/wangwei/PythonProject/tools-py/.venv/bin/python"

# 第一步：查询数据，构建 SQL 语句
for code in $STOCK_CODES; do
  STOCK_CODE="$code" "$PYTHON_VENV" "$QUERY_SCRIPT"
done

# 第二步：插入数据至 DB（按每个 QUERY_DATE 循环）
for query_date in "${QUERY_DATES_ARR[@]}"; do
  INSERT_D="${query_date//-/}"
  INSERT_YM="${INSERT_D:0:4}-${INSERT_D:4:2}"
  for code in $STOCK_CODES; do
    "$INSERT_SCRIPT" "$code" "$INSERT_YM" "$INSERT_D"
  done
done
