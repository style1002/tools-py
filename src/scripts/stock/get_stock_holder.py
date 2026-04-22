import os
import random
import re
import time
import warnings
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import unescape
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 可选：抑制 macOS LibreSSL 环境下 urllib3 v2 的告警噪音（推荐做法仍是 requirements 里 pin urllib3<2）
warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL.*")

import requests  # pyright: ignore[reportMissingModuleSource]
import pandas as pd  # pyright: ignore[reportMissingImports]

# 描述：抓取披露易 https://www3.hkexnews.hk/sdw/search/searchsdw_c.aspx



# 銅師傅
# STOCK_CODE = "00664"

# 諾比侃
# STOCK_CODE = "02635"

# 輕鬆健康
# STOCK_CODE = "02661"

# 希迪智駕
# STOCK_CODE = "03881"

# 五一视界
# STOCK_CODE = "06651"

# 卓越睿新
# STOCK_CODE = "02687"


# 手动指定要处理的日期数组（格式：YYYY-MM-DD）
# 单日：QUERY_DATES = ["2025-07-15"]
# 多日：QUERY_DATES = ["2025-07-01", "2025-07-02", "2025-07-03", ...]

QUERY_DATES = [
    '2026-04-21'
]

OUTPUT_DIR = Path(f"out/scripts/stock/{STOCK_CODE}") # 输出目录

API_URL = "https://www3.hkexnews.hk/sdw/search/searchsdw_c.aspx"

# 重要：不要用“...“截断 UA；很多站点会直接当作异常请求处理
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Referer": API_URL,
}

DEFAULT_TIMEOUT: Tuple[int, int] = (10, 60)  # (connect, read)
DEFAULT_MAX_RETRIES = 4

# 输出 SQL 时，created_at/updated_at 默认使用“holding_date 次日 00:00:00”，与你示例一致
DEFAULT_TIMESTAMP_MODE = "next_day_midnight"  # or "now"

def _extract_all_hidden_fields(html: str) -> Dict[str, str]:
    """
    从 ASP.NET 页面里提取隐藏字段（viewstate / eventvalidation / today / sort 等）。
    这是模拟 WebForm 的 __doPostBack 搜索的关键。
    """
    out: Dict[str, str] = {}
    for m in re.finditer(r"<input\b[^>]*\btype\s*=\s*['\"]hidden['\"][^>]*>", html, flags=re.IGNORECASE):
        tag = m.group(0)
        name_m = re.search(r"\bname\s*=\s*['\"]([^'\"]+)['\"]", tag, flags=re.IGNORECASE)
        if not name_m:
            continue
        name = name_m.group(1)
        value_m = re.search(r"\bvalue\s*=\s*['\"]([^'\"]*)['\"]", tag, flags=re.IGNORECASE)
        value = value_m.group(1) if value_m else ""
        out[name] = value
    return out


def _dump_debug(content: str, suffix: str, output_dir: Optional[Path] = None, query_date: Optional[str] = None) -> str:
    """
    保存调试文件，文件名包含请求日期和运行时时间戳。
    
    Args:
        content: 文件内容
        suffix: 文件扩展名（如 "html"）
        output_dir: 输出目录
        query_date: 请求的日期（格式：YYYY-MM-DD），会格式化为 YYYYMMDD 加入文件名
    
    Returns:
        文件路径字符串
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 如果提供了请求日期，格式化为 YYYYMMDD 并加入文件名
    if query_date:
        try:
            date_part = datetime.strptime(query_date, "%Y-%m-%d").strftime("%Y%m%d")
            filename = f"hkex_sdw_debug_{date_part}_{ts}.{suffix}"
        except Exception:
            # 如果日期格式解析失败，回退到原格式
            filename = f"hkex_sdw_debug_{ts}.{suffix}"
    else:
        filename = f"hkex_sdw_debug_{ts}.{suffix}"
    
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename
    else:
        filepath = Path(filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return str(filepath)


def _sql_quote(s: Optional[str]) -> str:
    if s is None:
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def _to_int_from_text(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def _extract_input_value(html: str, input_name: str) -> Optional[str]:
    # 支持单/双引号、属性顺序变化
    pattern = (
        r"<input\b[^>]*\bname\s*=\s*['\"]"
        + re.escape(input_name)
        + r"['\"][^>]*\bvalue\s*=\s*['\"]([^'\"]*)['\"][^>]*>"
    )
    m = re.search(pattern, html, flags=re.IGNORECASE)
    return unescape(m.group(1)) if m else None


def extract_sdw_meta(html: str, stock_code: str, query_date: str) -> Dict[str, Any]:
    """
    从 SDW 结果页提取：
    - stock_name
    - holding_date
    - ccass_shareholding（总数）
    - issued_shares（最近更新数目）
    """
    stock_name = _extract_input_value(html, "txtStockName") or ""

    raw_date = _extract_input_value(html, "originalShareholdingDate") or _extract_input_value(html, "txtShareholdingDate")
    holding_date = query_date
    if raw_date:
        holding_date = raw_date.replace("/", "-").strip()

    issued_shares: Optional[int] = None
    m_issued = re.search(
        r"已發行股份/權證/單位[\s\S]*?<div\b[^>]*class=['\"]summary-value['\"][^>]*>\s*([\d,]+)\s*</div>",
        html,
        flags=re.IGNORECASE,
    )
    if m_issued:
        issued_shares = _to_int_from_text(m_issued.group(1))

    ccass_shareholding: Optional[int] = None
    m_total = re.search(
        r"ccass-search-total[\s\S]*?<div\b[^>]*class=['\"]shareholding['\"][^>]*>[\s\S]*?"
        r"<div\b[^>]*class=['\"]value['\"][^>]*>\s*([\d,]+)\s*</div>",
        html,
        flags=re.IGNORECASE,
    )
    if m_total:
        ccass_shareholding = _to_int_from_text(m_total.group(1))

    # 不愿意披露：summary 区块里有单独一行
    non_disclosed_shareholding: Optional[int] = None
    m_non_disclosed = re.search(
        r"不願意披露的投資者戶口持有人[\s\S]*?<div\b[^>]*class=['\"]shareholding['\"][^>]*>[\s\S]*?"
        r"<div\b[^>]*class=['\"]value['\"][^>]*>\s*([\d,]+)\s*</div>",
        html,
        flags=re.IGNORECASE,
    )
    if m_non_disclosed:
        non_disclosed_shareholding = _to_int_from_text(m_non_disclosed.group(1))

    # 其它：通常等于 已发行 - CCASS总数
    others_shareholding: Optional[int] = None
    if issued_shares is not None and ccass_shareholding is not None:
        diff = issued_shares - ccass_shareholding
        if diff >= 0:
            others_shareholding = diff

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "holding_date": holding_date,
        "ccass_shareholding": ccass_shareholding,
        "issued_shares": issued_shares,
        "non_disclosed_shareholding": non_disclosed_shareholding,
        "others_shareholding": others_shareholding,
    }


def _default_timestamps(holding_date: str) -> Tuple[str, str]:
    """
    返回 created_at, updated_at（字符串 'YYYY-MM-DD HH:MM:SS'）
    """
    if DEFAULT_TIMESTAMP_MODE == "now":
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ts, ts

    try:
        d = datetime.strptime(holding_date, "%Y-%m-%d") + timedelta(days=1)
        ts = d.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        return ts, ts
    except Exception:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ts, ts


def df_to_postgres_inserts(
    df: pd.DataFrame,
    *,
    stock_code: str,
    stock_name: str,
    holding_date: str,
    ccass_shareholding: Optional[int],
    issued_shares: Optional[int],
    non_disclosed_shareholding: Optional[int] = None,
    others_shareholding: Optional[int] = None,
    table_schema: str = "public",
    table_name: str = "stock_broker_holdings",
) -> str:
    """
    生成形如（批量）：
    INSERT INTO "public"."stock_broker_holdings" (...) VALUES (...), (...), ...;
    """
    created_at, updated_at = _default_timestamps(holding_date)

    cols = (
        '"stock_code", "stock_name", "broker_id", "broker_name", "holding_date", "share_quantity", '
        '"is_disclosure", "created_at", "updated_at", "ccass_shareholding", "issued_shares", "equity_percentage"'
    )
    value_rows: list[str] = []

    def _equity_percentage(share_quantity: Optional[int], issued: Optional[int]) -> str:
        """
        equity_percentage = share_quantity / issued_shares，保留 6 位小数（numeric 字面量，不加引号）
        """
        if share_quantity is None or issued in (None, 0):
            return "NULL"
        try:
            v = (Decimal(share_quantity) / Decimal(issued)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            return format(v, "f")
        except (InvalidOperation, ZeroDivisionError):
            return "NULL"

    def _values_row(
        *,
        broker_id: str,
        broker_name: str,
        share_quantity: Optional[int],
        is_disclosure: str,
    ) -> str:
        equity_percentage = _equity_percentage(share_quantity, issued_shares)
        values = (
            f"{_sql_quote(stock_code)}, "
            f"{_sql_quote(stock_name)}, "
            f"{_sql_quote(broker_id)}, "
            f"{_sql_quote(broker_name)}, "
            f"{_sql_quote(holding_date)}, "
            f"{share_quantity if share_quantity is not None else 'NULL'}, "
            f"{_sql_quote(is_disclosure)}, "
            f"{_sql_quote(created_at)}, "
            f"{_sql_quote(updated_at)}, "
            f"{ccass_shareholding if ccass_shareholding is not None else 'NULL'}, "
            f"{issued_shares if issued_shares is not None else 'NULL'}, "
            f"{equity_percentage}"
        )
        return f"({values})"

    # 明细表：市场中介者/愿意披露
    for _, row in df.iterrows():
        broker_id = str(row.get("Participant ID") or "").strip()
        broker_name_raw = str(row.get("Participant Name") or "").strip()
        broker_name = broker_name_raw.replace("*", "").strip()
        if not broker_id:
            broker_id = broker_name  # 规则 1：broker_id 为空则用 broker_name
        share_quantity = _to_int_from_text(row.get("Shareholding"))
        value_rows.append(
            _values_row(
                broker_id=broker_id,
                broker_name=broker_name,
                share_quantity=share_quantity,
                is_disclosure="t",
            )
        )

    # 规则 3.1：不愿意披露的投资者户口持有人（从 summary 提取，持股 6616）
    if non_disclosed_shareholding is not None:
        name = "不願意披露的投資者戶口持有人"
        value_rows.append(
            _values_row(
                broker_id=name,
                broker_name=name,
                share_quantity=non_disclosed_shareholding,
                is_disclosure="f",
            )
        )

    # 规则 3.2：其它（通常= issued_shares - ccass_shareholding）
    if others_shareholding is not None:
        name = "其它"
        value_rows.append(
            _values_row(
                broker_id=name,
                broker_name=name,
                share_quantity=others_shareholding,
                is_disclosure="f",
            )
        )

    if not value_rows:
        return ""

    insert_head = f'INSERT INTO "{table_schema}"."{table_name}" ({cols}) VALUES\n'
    return insert_head + ",\n".join(value_rows) + ";\n"


def fetch_broker_holdings(
    stock_code: str,
    date_str: str,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: Tuple[int, int] = DEFAULT_TIMEOUT,
    debug_dump: bool = True,
    output_dir: Optional[Path] = None,
) -> Optional[str]:
    """
    抓取披露易 SDW 的搜索结果页面 HTML。

    说明：`searchsdw_c.aspx` 是 ASP.NET WebForm 页面，“搜尋”按钮会触发 __doPostBack('btnSearch','')，
    返回通常是 HTML（不是 JSON）。因此这里返回 HTML 供后续解析表格。
    """
    session = requests.Session()
    session.headers.update(BASE_HEADERS)

    # 先 GET 一次以建立会话/拿 cookie（以及可能存在的 anti-forgery hidden 字段）
    hidden_fields: Dict[str, str] = {}
    try:
        warmup = session.get(API_URL, timeout=timeout)
        warmup.raise_for_status()
        hidden_fields = _extract_all_hidden_fields(warmup.text)
    except Exception as e:
        # 不阻塞主流程：有些时候不需要 warmup
        print(f"预热请求失败（将继续尝试直接查询）: {e}")

    # 模拟点击“搜尋”按钮：__doPostBack('btnSearch','')
    params: Dict[str, Any] = dict(hidden_fields)
    params.update(
        {
            "__EVENTTARGET": "btnSearch",
            "__EVENTARGUMENT": "",
            # 页面里本来就有这些隐藏字段，存在则沿用；不存在就用默认值
            "sortBy": params.get("sortBy", "shareholding"),
            "sortDirection": params.get("sortDirection", "desc"),
            "alertMsg": params.get("alertMsg", ""),
            "txtShareholdingDate": date_str.replace("-", "/"),  # "2025/12/16"
            "txtStockCode": stock_code,
            "txtStockName": "",
            "txtParticipantID": "",
            "txtParticipantName": "",
            "txtSelPartID": params.get("txtSelPartID", ""),
        }
    )

    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.post(API_URL, data=params, timeout=timeout)
            response.raise_for_status()

            content_type = (response.headers.get("Content-Type") or "").lower()
            if debug_dump:
                filename = _dump_debug(response.text, "html", output_dir, query_date=date_str)
                if not output_dir:
                    print(f"已保存响应页面: {filename}；Content-Type={content_type}")

            # 预期返回 HTML；如果不是，也返回文本方便排查
            return response.text
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
            last_err = e
            sleep_s = min(20.0, (2 ** (attempt - 1)) + random.random())
            print(f"请求超时（第 {attempt}/{max_retries} 次），{sleep_s:.1f}s 后重试 ...")
            time.sleep(sleep_s)
        except Exception as e:
            last_err = e
            # 常见：被限流/503，或返回异常页面
            if attempt < max_retries:
                sleep_s = min(20.0, (2 ** (attempt - 1)) + random.random())
                print(f"请求失败（第 {attempt}/{max_retries} 次）: {e}；{sleep_s:.1f}s 后重试 ...")
                time.sleep(sleep_s)
            else:
                break

    print(f"获取数据失败: {last_err}")
    return None

def parse_broker_html(html: Optional[str], query_date: Optional[str] = None) -> pd.DataFrame:
    """
    解析 SDW 返回的 HTML 页面，从中提取“参与者持股”结果表格为 DataFrame。
    """
    if not html:
        print("数据结构异常或无可用数据（HTML 为空）")
        return pd.DataFrame()

    def _to_int(v: Any) -> Optional[int]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v)
        digits = re.sub(r"[^\d]", "", s)
        return int(digits) if digits else None

    def _to_float(v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace("%", "")
        try:
            return float(s)
        except Exception:
            return None

    def _strip_tags(s: str) -> str:
        s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
        s = re.sub(r"<[^>]+>", "", s)
        return unescape(s).strip()

    def _parse_html_table_fallback(page_html: str) -> pd.DataFrame:
        """
        兜底解析（不依赖 lxml/bs4/html5lib）。
        直接从结果页中定位 table.table-scroll，并按 td 的 class 抽取 mobile-list-body 内容。
        """
        # 先从“结果区标题”附近找表，避免误抓到“使用条款”的 table
        anchor = "市場中介者/願意披露的投資者戶口持有人的紀錄"
        idx = page_html.find(anchor)
        search_html = page_html[idx:] if idx != -1 else page_html

        m_table = re.search(
            r"<table\b[^>]*class=['\"][^'\"]*\btable-scroll\b[^'\"]*['\"][^>]*>(?P<body>[\s\S]*?)</table>",
            search_html,
            flags=re.IGNORECASE,
        )
        if not m_table:
            return pd.DataFrame()

        table_html = m_table.group("body")
        m_tbody = re.search(r"<tbody\b[^>]*>(?P<tbody>[\s\S]*?)</tbody>", table_html, flags=re.IGNORECASE)
        tbody_html = m_tbody.group("tbody") if m_tbody else table_html

        rows: list[dict[str, Any]] = []
        for m_row in re.finditer(r"<tr\b[^>]*>(?P<tr>[\s\S]*?)</tr>", tbody_html, flags=re.IGNORECASE):
            tr_html = m_row.group("tr")

            def _cell_by_col(col_class: str) -> Optional[str]:
                # 更精确地匹配：只提取 mobile-list-body 的内容，排除 mobile-list-heading
                # 先找到对应的 td，然后找到其中的 mobile-list-body div
                td_pattern = (
                    r"<td\b[^>]*class=['\"][^'\"]*\b"
                    + re.escape(col_class)
                    + r"\b[^'\"]*['\"][^>]*>(?P<td_content>[\s\S]*?)</td>"
                )
                m_td = re.search(td_pattern, tr_html, flags=re.IGNORECASE)
                if not m_td:
                    return None
                
                td_content = m_td.group("td_content")
                # 在 td 内容中查找 mobile-list-body，排除 mobile-list-heading
                m_body = re.search(
                    r"<div\b[^>]*class=['\"][^'\"]*\bmobile-list-body\b[^'\"]*['\"][^>]*>(?P<v>[\s\S]*?)</div>",
                    td_content,
                    flags=re.IGNORECASE,
                )
                if not m_body:
                    return None
                
                # 提取并清理内容
                value = m_body.group("v")
                return _strip_tags(value)

            participant_id = _cell_by_col("col-participant-id")
            participant_name = _cell_by_col("col-participant-name")
            address = _cell_by_col("col-address")
            shareholding = _cell_by_col("col-shareholding")
            percentage = _cell_by_col("col-shareholding-percent")

            # 跳过空行
            if not any([participant_id, participant_name, address, shareholding, percentage]):
                continue

            rows.append(
                {
                    "Participant ID": participant_id,
                    "Participant Name": participant_name,
                    "Address": address,
                    "Shareholding": _to_int(shareholding),
                    "Percentage": _to_float(percentage),
                    "Date": query_date or "",
                }
            )

        return pd.DataFrame(rows)

    try:
        # pandas 未来版本不再支持直接传入 literal html string，这里按推荐方式用 StringIO 包一层
        tables = pd.read_html(StringIO(html))
    except Exception as e:
        print(f"HTML 解析失败（pandas.read_html）：{e}")
        # 兜底：不装 lxml 也能跑
        df_fb = _parse_html_table_fallback(html)
        if not df_fb.empty:
            print("已使用兜底解析器（无需 lxml）成功解析结果表格。")
            return df_fb
        print("可尝试安装解析依赖：/Users/wangwei/PyCharmMiscProject/.venv/bin/pip install -r requirements.txt")
        return pd.DataFrame()

    def _normalize_col(c: Any) -> str:
        return str(c).strip()

    target: Optional[pd.DataFrame] = None
    for t in tables:
        cols = [_normalize_col(c) for c in t.columns]
        col_join = " ".join(cols)
        looks_like_result = (
            ("參與者" in col_join or "Participant" in col_join)
            and ("持股" in col_join or "Shareholding" in col_join)
            and ("使用條款" not in col_join)
        )
        if looks_like_result:
            target = t
            break

    if target is None:
        print("页面里未找到“参与者持股”结果表格（可能仍未触发搜索，或页面结构有变）。")
        return pd.DataFrame()

    rename_map: Dict[Any, str] = {}
    for c in target.columns:
        cs = _normalize_col(c)
        if "編號" in cs or cs.lower() in ("participant id", "participantid"):
            rename_map[c] = "Participant ID"
        elif "名稱" in cs or cs.lower() in ("participant name", "participantname", "name"):
            rename_map[c] = "Participant Name"
        elif "地址" in cs or cs.lower() == "address":
            rename_map[c] = "Address"
        elif "持股量" in cs or "持股" in cs or cs.lower() in ("shareholding", "shareholding quantity"):
            rename_map[c] = "Shareholding"
        elif "百分比" in cs or "百分" in cs or cs.lower() in ("percentage", "shareholding percent"):
            rename_map[c] = "Percentage"

    df = target.rename(columns=rename_map).copy()
    
    # 简单清理：只提取冒号后的值（如果包含冒号的话）
    def _extract_after_colon(value: Any) -> Optional[str]:
        if value is None:
            return None
        s = str(value).strip()
        # 如果包含冒号，取冒号后的部分
        if ":" in s or "：" in s:
            parts = re.split(r"[:：]", s, maxsplit=1)
            s = parts[-1].strip() if len(parts) > 1 else s
        return s if s else None
    
    if "Participant ID" in df.columns:
        df["Participant ID"] = df["Participant ID"].apply(_extract_after_colon)
    if "Participant Name" in df.columns:
        df["Participant Name"] = df["Participant Name"].apply(_extract_after_colon)
    if "Address" in df.columns:
        df["Address"] = df["Address"].apply(_extract_after_colon)
    
    if "Shareholding" in df.columns:
        df["Shareholding"] = df["Shareholding"].apply(_to_int)
    if "Percentage" in df.columns:
        df["Percentage"] = df["Percentage"].apply(_to_float)
    if query_date:
        df["Date"] = query_date
    return df


def process_single_date(stock_code: str, date_str: str, output_base_dir: str = OUTPUT_DIR) -> Optional[pd.DataFrame]:
    """
    处理单个日期的数据（原有逻辑，只是把文件保存到 out/ 目录）
    """
    print(f"\n{'='*60}")
    print(f"正在抓取 {stock_code} 在 {date_str} 的中央结算系统参与者持股信息 ...")
    
    # 创建输出目录：out/YYYY-MM/
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month_dir = dt.strftime("%Y-%m")
        output_dir = Path(output_base_dir) / month_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        debug_dir = output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        output_dir = Path(output_base_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        debug_dir = output_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
    
    html = fetch_broker_holdings(stock_code, date_str, debug_dump=True, output_dir=debug_dir)
    df = parse_broker_html(html, query_date=date_str)
    
    if not df.empty:
        df.sort_values(by="Shareholding", ascending=False, inplace=True)
        filename = f"stock_{stock_code}_brokers_{date_str.replace('-', '')}.csv"
        csv_path = output_dir / filename
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"已保存至 {csv_path}\n预览前几行：")
        print(df.head())

        if html:
            meta = extract_sdw_meta(html, stock_code, date_str)
            sql_text = df_to_postgres_inserts(
                df,
                stock_code=meta["stock_code"],
                stock_name=meta["stock_name"],
                holding_date=meta["holding_date"],
                ccass_shareholding=meta["ccass_shareholding"],
                issued_shares=meta["issued_shares"],
                non_disclosed_shareholding=meta.get("non_disclosed_shareholding"),
                others_shareholding=meta.get("others_shareholding"),
            )
            sql_file = f"stock_{stock_code}_brokers_{date_str.replace('-', '')}.sql"
            sql_path = output_dir / sql_file
            with open(sql_path, "w", encoding="utf-8") as f:
                f.write(sql_text)
            print(f"已生成 PostgreSQL INSERT 文件：{sql_path}（共 {len(df)} 行）")
        return df
    else:
        print("未有有效持股信息（请打开最新的 hkex_sdw_debug_*.html 看是否出现结果表格）。")
        return None


def main():
    """
    主函数：处理 QUERY_DATES 数组中的所有日期
    """
    query_dates = globals().get("QUERY_DATES", [])
    
    if not query_dates or not isinstance(query_dates, list) or len(query_dates) == 0:
        print("❌ 请设置 QUERY_DATES 数组，例如：QUERY_DATES = ['2025-07-15']")
        return
    
    print(f"📅 处理 {len(query_dates)} 个日期")
    success_count = 0
    failed_dates = []
    
    for date_str in query_dates:
        try:
            df = process_single_date(STOCK_CODE, date_str, OUTPUT_DIR)
            if df is not None:
                success_count += 1
            else:
                failed_dates.append(date_str)
            # 避免请求过快
            if len(query_dates) > 1:
                time.sleep(2)
        except Exception as e:
            print(f"❌ {date_str}: 处理失败 - {e}")
            failed_dates.append(date_str)
    
    print(f"\n{'='*60}")
    print(f"📊 处理完成：")
    print(f"  ✓ 成功: {success_count}/{len(query_dates)}")
    if failed_dates:
        print(f"  ❌ 失败: {len(failed_dates)} 个日期 - {failed_dates}")
    print(f"📁 输出目录: {Path(OUTPUT_DIR).absolute()}")

if __name__ == "__main__":
    main()