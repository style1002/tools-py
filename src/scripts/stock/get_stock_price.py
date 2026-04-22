import akshare as ak  # pyright: ignore[reportMissingImports]
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 铜师傅
# symbol = "00664"
# stock_name = "銅師傅"
# issued_shares = 51917127 # 如果为 None 则尝试从接口获取

# # 诺比侃
# symbol = "02635"
# stock_name = "諾比侃"
# issued_shares = 30434578 # 如果为 None 则尝试从接口获取

# 轻松健康
# symbol = "02661"
# stock_name = "輕鬆健康"
# issued_shares = 206374209 # 如果为 None 则尝试从接口获取

# 希迪智駕
# symbol = "03881"
# stock_name = "希迪智駕"
# issued_shares = 424438920 # 如果为 None 则尝试从接口获取


start_date = "20260410"  # 开始日期 79
end_date = "20260417"    # 结束日期 68

print(f"正在获取港股 {symbol} 的历史数据...")
print(f"日期范围: {start_date} 至 {end_date}")

try:
    # 获取港股历史数据
    # 注意：akshare 的港股接口可能有不同的名称，尝试多种方式
    df = None
    
    # 方法1: stock_hk_hist (如果存在)
    if hasattr(ak, 'stock_hk_hist'):
        try:
            df = ak.stock_hk_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust=""  # ""不复权, "qfq"前复权, "hfq"后复权
            )
        except Exception as e:
            print(f"尝试 stock_hk_hist 失败: {e}")
    
    # 方法2: tool_trade_date_hist_sina (新浪港股接口)
    if df is None or df.empty:
        try:
            if hasattr(ak, 'tool_trade_date_hist_sina'):
                # 港股代码格式可能需要调整
                hk_symbol = f"{symbol}.HK" if not symbol.endswith('.HK') else symbol
                df = ak.tool_trade_date_hist_sina(symbol=hk_symbol, period="daily", adjust="qfq")
                # 过滤日期范围
                if not df.empty and 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
        except Exception as e:
            print(f"尝试 tool_trade_date_hist_sina 失败: {e}")
    
    # 方法3: stock_hk_daily (如果存在)
    if df is None or df.empty:
        try:
            if hasattr(ak, 'stock_hk_daily'):
                df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
                print(f"symbol: {symbol}")
                print(f"stock_name: {stock_name}")
                print(f"issued_shares: {issued_shares}")
                print(f"start_date: {start_date}")
                print(f"end_date: {end_date}")
                print(f"列名: {df.columns.tolist()}")
                print(f"前几行数据:\n{df.head()}")
                # 过滤日期范围
                if not df.empty:
                    date_col = [c for c in df.columns if '日期' in str(c) or 'date' in str(c).lower()][0]
                    df[date_col] = pd.to_datetime(df[date_col])
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]
        except Exception as e:
            print(f"尝试 stock_hk_daily 失败: {e}")
    
    if df is None or df.empty:
        print(f"❌ 未获取到数据，请检查股票代码 {symbol} 是否正确，或检查网络连接")
        print("提示：可能需要安装 akshare: pip install akshare")
        exit(1)
    
    print(f"✓ 成功获取 {len(df)} 条交易日数据")
    
    # 2. 筛选需要的列并重命名
    # 港股列名通常为：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
    available_cols = df.columns.tolist()
    print(f"可用列: {available_cols}")
    
    # 根据实际列名进行映射
    col_mapping = {}
    for col in available_cols:
        col_lower = str(col).lower()
        if '日期' in str(col) or 'date' in col_lower:
            col_mapping['trade_date'] = col
        elif '开盘' in str(col) or 'open' in col_lower:
            col_mapping['open'] = col
        elif '收盘' in str(col) or 'close' in col_lower:
            col_mapping['close'] = col
        elif '最高' in str(col) or 'high' in col_lower:
            col_mapping['high'] = col
        elif '最低' in str(col) or 'low' in col_lower:
            col_mapping['low'] = col
        elif '成交额' in str(col) or ('amount' in col_lower and '成交' in str(col)):
            col_mapping['amount'] = col
        elif '成交量' in str(col) or 'volume' in col_lower:
            col_mapping['volume'] = col
    
    # 选择需要的列（包括成交量）
    needed_cols = ['trade_date', 'open', 'close', 'high', 'low', 'amount', 'volume']
    selected_cols = [col_mapping.get(k) for k in needed_cols if k in col_mapping and col_mapping.get(k) is not None]
    
    if not selected_cols:
        print("❌ 无法识别数据列，使用所有列")
        df_selected = df.copy()
    else:
        df_selected = df[selected_cols].copy()
        # 重命名列
        reverse_mapping = {v: k for k, v in col_mapping.items()}
        df_selected.rename(columns=reverse_mapping, inplace=True)
    
    # 确保有 trade_date 列
    if 'trade_date' not in df_selected.columns:
        date_col = [c for c in df.columns if '日期' in str(c) or 'date' in str(c).lower()]
        if date_col:
            df_selected['trade_date'] = df[date_col[0]]
        else:
            print("❌ 无法找到日期列")
            exit(1)
    
    # 3. 数据格式化
    # 日期转字符串（统一格式为 YYYY-MM-DD）
    if df_selected['trade_date'].dtype == 'object':
        # 尝试解析日期
        try:
            df_selected['trade_date'] = pd.to_datetime(df_selected['trade_date']).dt.strftime('%Y-%m-%d')
        except:
            df_selected['trade_date'] = df_selected['trade_date'].astype(str)
    else:
        df_selected['trade_date'] = pd.to_datetime(df_selected['trade_date']).dt.strftime('%Y-%m-%d')
    
    # 数值列格式化
    numeric_cols = ['open', 'close', 'high', 'low', 'amount']
    for col in numeric_cols:
        if col in df_selected.columns:
            df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')
    
    # 价格保留3位小数（如示例中的 '0.081'）
    price_cols = ['open', 'close', 'high', 'low']
    for col in price_cols:
        if col in df_selected.columns:
            df_selected[col] = df_selected[col].round(3)
    
    # 成交额保留2位小数
    if 'amount' in df_selected.columns:
        df_selected['amount'] = df_selected['amount'].round(2)
    
    # 成交量处理
    if 'volume' in df_selected.columns:
        df_selected['volume'] = pd.to_numeric(df_selected['volume'], errors='coerce')
    else:
        df_selected['volume'] = None
    
    # 尝试获取股票名称和已发行股数（如果未设置）
    current_stock_name = stock_name
    current_issued_shares = issued_shares
    if not current_stock_name:
        # 尝试从 akshare 获取股票信息
        try:
            if hasattr(ak, 'stock_hk_spot_em'):
                spot_df = ak.stock_hk_spot_em()
                if not spot_df.empty and '代码' in spot_df.columns:
                    stock_info = spot_df[spot_df['代码'] == symbol]
                    if not stock_info.empty and '名称' in stock_info.columns:
                        current_stock_name = stock_info.iloc[0]['名称']
        except:
            pass
    
    # 添加股票代码、名称和已发行股数到 DataFrame
    df_selected['stock_code'] = symbol
    df_selected['stock_name'] = current_stock_name
    df_selected['issued_shares'] = current_issued_shares
    
    # 4. 统计交易日情况
    print("\n" + "="*60)
    print("📊 交易日统计信息")
    print("="*60)
    
    total_days = len(df_selected)
    print(f"总交易日数: {total_days} 天")
    
    if total_days > 0:
        first_date = df_selected['trade_date'].min()
        last_date = df_selected['trade_date'].max()
        print(f"最早交易日: {first_date}")
        print(f"最晚交易日: {last_date}")
        
        # 计算日期范围内的所有日期
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates]
        trade_dates_set = set(df_selected['trade_date'].astype(str))
        
        # 统计非交易日（周末和节假日）
        non_trade_days = []
        for date_str in all_dates_str:
            if date_str not in trade_dates_set:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                weekday = dt.weekday()  # 0=Monday, 6=Sunday
                if weekday < 5:  # 周一到周五但不是交易日，可能是节假日
                    non_trade_days.append(date_str)
        
        print(f"日期范围内总天数: {len(all_dates)} 天")
        print(f"非交易日（可能是节假日）: {len(non_trade_days)} 天")
        if len(non_trade_days) > 0 and len(non_trade_days) <= 20:
            print(f"  非交易日列表: {', '.join(non_trade_days[:10])}")
            if len(non_trade_days) > 10:
                print(f"  ... 还有 {len(non_trade_days) - 10} 个非交易日")
        
        # 统计价格信息
        if 'close' in df_selected.columns:
            close_prices = pd.to_numeric(df_selected['close'], errors='coerce')
            print(f"\n收盘价统计:")
            print(f"  最高收盘价: {close_prices.max():.2f}")
            print(f"  最低收盘价: {close_prices.min():.2f}")
            print(f"  平均收盘价: {close_prices.mean():.2f}")
            print(f"  最新收盘价: {close_prices.iloc[-1]:.2f}")
        
        if 'amount' in df_selected.columns:
            amounts = pd.to_numeric(df_selected['amount'], errors='coerce')
            print(f"\n成交额统计:")
            print(f"  最大成交额: {amounts.max():.2f}")
            print(f"  平均成交额: {amounts.mean():.2f}")
            print(f"  总成交额: {amounts.sum():.2f}")
    
    # 生成批量INSERT语句
    def _sql_quote(s):
        """SQL 字符串转义"""
        if s is None:
            return "NULL"
        return "'" + str(s).replace("'", "''") + "'"
    
    def _format_value(val, is_decimal=False, decimal_places=3):
        """格式化数值"""
        if pd.isna(val) or val is None:
            return "NULL"
        if is_decimal:
            return f"{float(val):.{decimal_places}f}"
        return str(int(val)) if isinstance(val, (int, float)) and not pd.isna(val) else "NULL"
    
    # 生成批量插入的 VALUES 部分
    value_rows = []
    for _, row in df_selected.iterrows():
        trade_date = str(row['trade_date'])
        # 计算 created_at 和 updated_at（交易日期次日 00:00:00，或使用当前时间）
        try:
            trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
            next_day = (trade_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0)
            timestamp_str = next_day.strftime('%Y-%m-%d %H:%M:%S')
        except:
            timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 成交额转换为万元（turnover_10k）
        amount_val = row.get('amount')
        turnover_10k = None
        if pd.notna(amount_val) and amount_val is not None:
            turnover_10k = float(amount_val) / 10000.0  # 转换为万元
        
        values = (
            f"{_sql_quote(symbol)}, "  # stock_code
            f"{_sql_quote(current_stock_name)}, "  # stock_name
            f"{current_issued_shares if current_issued_shares is not None else 'NULL'}, "  # issued_shares
            f"{_sql_quote(trade_date)}, "  # trade_date
            f"{_format_value(row.get('open'), is_decimal=True)}, "  # open_price
            f"{_format_value(row.get('close'), is_decimal=True)}, "  # close_price
            f"{_format_value(row.get('high'), is_decimal=True)}, "  # high_price
            f"{_format_value(row.get('low'), is_decimal=True)}, "  # low_price
            f"{_format_value(row.get('volume'), is_decimal=False)}, "  # volume
            f"{_format_value(turnover_10k, is_decimal=True, decimal_places=2)}, "  # turnover_10k
            f"{_sql_quote(timestamp_str)}, "  # created_at
            f"{_sql_quote(timestamp_str)}"  # updated_at
        )
        value_rows.append(f"({values})")
    
    # 生成批量 INSERT 语句
    cols = (
        '"stock_code", "stock_name", "issued_shares", "trade_date", '
        '"open_price", "close_price", "high_price", "low_price", '
        '"volume", "turnover_10k", "created_at", "updated_at"'
    )
    insert_sql = f'INSERT INTO "public"."stock_daily_prices" ({cols})\nVALUES\n\t' + ',\n\t'.join(value_rows) + ';'
    
    # 6. 保存到文件
    output_dir = Path(f"out/scripts/stock/{symbol}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sql_file = output_dir / f"stock_{symbol}_price_{start_date}_{end_date}.sql"
    csv_file = output_dir / f"stock_{symbol}_price_{start_date}_{end_date}.csv"
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(insert_sql)
    
    # 保存 CSV（调整列顺序以匹配数据库表结构）
    csv_df = df_selected.copy()
    # 添加 turnover_10k 列
    if 'amount' in csv_df.columns:
        csv_df['turnover_10k'] = csv_df['amount'] / 10000.0
    csv_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    
    print(f"\n✓ 已生成批量插入SQL（{len(value_rows)} 条记录）")
    print(f"✓ SQL文件: {sql_file}")
    print(f"✓ CSV文件: {csv_file}")
    print("\nSQL预览（前200字符）：")
    preview = insert_sql[:200] + "..." if len(insert_sql) > 200 else insert_sql
    print(f"  {preview}")
    
    # 显示数据预览
    print("\n数据预览（前5条）：")
    print(df_selected.head().to_string())
    
except Exception as e:
    print(f"❌ 获取数据失败: {e}")
    import traceback
    traceback.print_exc()
