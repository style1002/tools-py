#!/bin/bash
set -euo pipefail

# 用法: stock_holder_pipeline.sh [<QUERY_DATE> <HOLDING_DATE_REAL>]
# 示例: stock_holder_pipeline.sh 2026-05-19 2026-05-15
# 不传参则使用下方默认日期；QUERY_DATE 与入库 D 为同一天（YYYY-MM-DD -> YYYYMMDD）

DEFAULT_QUERY_DATE="2026-05-19"
DEFAULT_HOLDING_DATE_REAL="2026-05-15"

usage() {
  cat >&2 <<EOF
用法: $0 [<QUERY_DATE> <HOLDING_DATE_REAL>]
  传两个参数指定日期；不传则使用默认: ${DEFAULT_QUERY_DATE} / ${DEFAULT_HOLDING_DATE_REAL}
示例: $0 2026-05-19 2026-05-15
EOF
  exit 1
}

case $# in
  0)
    QUERY_DATE="$DEFAULT_QUERY_DATE"
    HOLDING_DATE_REAL="$DEFAULT_HOLDING_DATE_REAL"
    echo "使用默认日期: QUERY_DATE=$QUERY_DATE HOLDING_DATE_REAL=$HOLDING_DATE_REAL"
    ;;
  2)
    QUERY_DATE="$1"
    HOLDING_DATE_REAL="$2"
    ;;
  *)
    usage
    ;;
esac
INSERT_D="${QUERY_DATE//-/}"
INSERT_YM="${INSERT_D:0:4}-${INSERT_D:4:2}"

STOCK_CODES="00664 01989 02635 02661 03881 06651"
QUERY_SCRIPT="/Users/wangwei/PythonProject/tools-py/src/scripts/stock/get_stock_holder.py"
INSERT_SCRIPT="/Users/wangwei/PythonProject/tools-py/out/scripts/stock/insert_to_pg.sh"
PYTHON_VENV="/Users/wangwei/PythonProject/tools-py/.venv/bin/python"

# 第一步：查询数据，构建 SQL 语句
for code in $STOCK_CODES; do
  QUERY_DATE="$QUERY_DATE" \
  HOLDING_DATE_REAL="$HOLDING_DATE_REAL" \
  STOCK_CODE="$code" \
  "$PYTHON_VENV" "$QUERY_SCRIPT"
done

# 第二步：插入数据至 DB
for code in $STOCK_CODES; do
  "$INSERT_SCRIPT" "$code" "$INSERT_YM" "$INSERT_D"
done
