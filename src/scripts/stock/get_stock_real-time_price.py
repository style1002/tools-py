#!/Users/wangwei/test_venv/.venv/bin/python3

import akshare as ak
from datetime import datetime, timedelta, time

# 你要监控的一只股票（仅港股此实现）
TARGET_STOCK = ("01810", "小米集团")

def in_hk_trading_time(now=None):
    """判断当前是否为港股交易时间（不含节假日，仅时间段约束）"""
    if now is None:
        now = datetime.now()
    today_time = now.time()
    morning_open = time(9, 0)
    morning_close = time(12, 1)
    afternoon_open = time(13, 0)
    afternoon_close = time(16, 9)

    if (morning_open <= today_time < morning_close) or (afternoon_open <= today_time < afternoon_close):
        # 港股周一到周五
        if now.weekday() < 5:
            return True
    return False

def get_hk_stock_price(code):
    """获取港股实时价格 - 使用 stock_hk_hist 获取最近数据"""
    today = datetime.now()
    start_date = (today - timedelta(days=5)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    df = ak.stock_hk_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="")
    if df.empty:
        raise ValueError(f"未找到股票 {code} 数据")
    latest = df.iloc[-1]
    price = float(latest['收盘'])
    # 获取涨跌幅
    if '涨跌幅' in latest:
        pct = float(latest['涨跌幅'])
    elif '涨跌额' in latest and price > 0:
        change = float(latest['涨跌额'])
        pct = (change / (price - change)) * 100 if (price - change) > 0 else 0
    else:
        pct = 0.0
    return price, pct

def main():
    code, name = TARGET_STOCK
    now = datetime.now()
    now_str = now.strftime("%H:%M")
    if not in_hk_trading_time(now):
        print(f"⏳")
        print("---")
        print("CLOSED")
        print("---")
        print("Refresh | refresh=true")
        return
    try:
        price, pct = get_hk_stock_price(code)
    except Exception as e:
        print(f"📡 {now_str}")
        print("---")
        print("ERROR")
        # print(f"错误: {str(e)}")
        print("---")
        print("Refresh | refresh=true")
        return

    # 输出格式：价格与涨幅，涨幅用颜色表示
    if pct < 0:
        color = "green"
    elif pct > 0:
        color = "red"
    else:
        color = "gray"
    print(f"HKD {price:.3f}| color={color}")
    print("---")
    print(f"{name}")
    print(f"HKD {price:.3f}")
    print(f"Gain/Loss {abs(pct):.2f}%")
    print("---")
    print("Refresh | refresh=true")

if __name__ == "__main__":
    main()