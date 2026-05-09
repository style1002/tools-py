#!/bin/bash

# 执行之前需要先手动修改两脚本里的参数

STOCK_CODES="00664 01989 02635 02661 03881 06651"
QUERY_SCRIPT="/Users/wangwei/PythonProject/tools-py/src/scripts/stock/get_stock_holder.py"
INSERT_SCRIPT="/Users/wangwei/PythonProject/tools-py/out/scripts/stock/insert_to_pg.sh"

# 第一步：查询数据，构建 SQL 语句
for code in $STOCK_CODES; do
  STOCK_CODE=$code /Users/wangwei/PythonProject/tools-py/.venv/bin/python $QUERY_SCRIPT
done

# 第二步：插入数据至 DB
for code in $STOCK_CODES; do
  $INSERT_SCRIPT $code
done