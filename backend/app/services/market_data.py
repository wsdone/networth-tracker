import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_price import MarketPrice
from app.models.holding import Holding

logger = logging.getLogger(__name__)

MARKET_TYPES = {
    "SSE": "a_stock",
    "SZSE": "a_stock",
    "HKSE": "hk_stock",
    "NYSE": "us_stock",
    "NASDAQ": "us_stock",
    "OTC": "fund",
    "SHFE": "futures",
    "DCE": "futures",
    "CZCE": "futures",
    "CFFEX": "futures",
    "INE": "futures",
    "GFEX": "futures",
}


def _classify_symbol(symbol: str, exchange: str | None) -> str:
    if exchange:
        return MARKET_TYPES.get(exchange, "a_stock")
    if symbol.isdigit():
        if symbol.startswith("6") or symbol.startswith("0") or symbol.startswith("3"):
            return "a_stock"
        if len(symbol) == 5:
            return "hk_stock"
    if symbol.isalpha() and len(symbol) <= 5:
        return "us_stock"
    return "a_stock"


def _parse_sina_fields(raw: str) -> dict | None:
    """Parse a single sina hq line like: var hq_str_sh600519="name,open,yclose,price,...\""""
    try:
        parts = raw.split('="')
        if len(parts) < 2:
            return None
        symbol_raw = parts[0].split("str_")[-1]
        values = parts[1].rstrip('"; \n').split(",")
        if len(values) < 4:
            return None
        name = values[0]
        price = float(values[3]) if values[3] else 0
        prev_close = float(values[2]) if values[2] else 0
        # Non-trading hours: price is 0, fall back to prev_close
        if price == 0 and prev_close > 0:
            price = prev_close
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        prefix = "sh" if symbol_raw.startswith("sh") else "sz"
        clean_symbol = symbol_raw[2:]
        return {
            "symbol": clean_symbol,
            "name": name,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "currency": "CNY",
            "source": "sina",
        }
    except Exception:
        return None


def _parse_sina_us_fields(raw: str) -> dict | None:
    """Parse sina US stock line: var hq_str_gb_mu="name,price,change_pct,...,prev_close"
    Fields: 0=name, 1=price, 2=change_pct, ..., 29=prev_close (last field)
    """
    try:
        parts = raw.split('="')
        if len(parts) < 2:
            return None
        symbol_raw = parts[0].split("str_")[-1]  # e.g. "gb_mu"
        values = parts[1].rstrip('"; \n').split(",")
        if len(values) < 30:
            return None
        name = values[0]
        price = float(values[1]) if values[1] else 0
        prev_close = float(values[29]) if values[29] else 0
        change_pct = float(values[2]) if values[2] else 0
        change = price - prev_close if price and prev_close else 0
        clean_symbol = symbol_raw[3:]  # strip "gb_"
        return {
            "symbol": clean_symbol,
            "name": name,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "currency": "USD",
            "source": "sina_us",
        }
    except Exception:
        return None


async def fetch_a_stock_quotes_sina(symbols: list[str]) -> dict[str, dict]:
    """Fetch A-share quotes from Sina Finance."""
    if not symbols:
        return {}
    try:
        codes = []
        for s in symbols:
            if s.startswith("6"):
                codes.append(f"sh{s}")
            else:
                codes.append(f"sz{s}")
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        result = {}
        for line in resp.text.strip().split("\n"):
            parsed = _parse_sina_fields(line)
            if parsed and parsed["symbol"] in symbols:
                result[parsed["symbol"]] = parsed
        return result
    except Exception as e:
        logger.error(f"Sina A-stock fetch failed: {e}")
        return {}


async def fetch_a_stock_quotes_akshare(symbols: list[str]) -> dict[str, dict]:
    """Fallback: A-share from akshare/eastmoney."""
    if not symbols:
        return {}
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
        result = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if code in symbols:
                result[code] = {
                    "symbol": code,
                    "name": str(row.get("名称", "")),
                    "price": float(row.get("最新价", 0) or 0),
                    "prev_close": float(row.get("昨收", 0) or 0),
                    "change": float(row.get("涨跌额", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "currency": "CNY",
                    "source": "eastmoney",
                }
        return result
    except Exception as e:
        logger.error(f"akshare A-stock fetch failed: {e}")
        return {}


async def fetch_a_stock_quotes(symbols: list[str]) -> dict[str, dict]:
    """Try Sina first, then akshare fallback."""
    result = await fetch_a_stock_quotes_sina(symbols)
    if result:
        return result
    return await fetch_a_stock_quotes_akshare(symbols)


async def fetch_fund_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch fund NAV from Sina or akshare."""
    if not symbols:
        return {}
    try:
        import akshare as ak

        result = {}
        for symbol in symbols:
            try:
                df = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) >= 2 else latest
                    nav = float(latest.iloc[1])
                    prev_nav = float(prev.iloc[1])
                    result[symbol] = {
                        "symbol": symbol,
                        "name": symbol,
                        "price": nav,
                        "prev_close": prev_nav,
                        "change": nav - prev_nav,
                        "change_pct": ((nav - prev_nav) / prev_nav * 100) if prev_nav else 0,
                        "currency": "CNY",
                        "source": "eastmoney_fund",
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch fund {symbol}: {e}")
        return result
    except Exception as e:
        logger.error(f"Fund fetch failed: {e}")
        return {}


async def fetch_hk_stock_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch HK stock quotes from Sina HK."""
    if not symbols:
        return {}
    try:
        codes = [f"hk{s}" for s in symbols]
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        result = {}
        for line in resp.text.strip().split("\n"):
            parsed = _parse_sina_fields(line)
            if parsed and parsed["symbol"] in symbols:
                parsed["currency"] = "HKD"
                parsed["source"] = "sina_hk"
                result[parsed["symbol"]] = parsed
        if result:
            return result
    except Exception as e:
        logger.warning(f"Sina HK fetch failed: {e}")

    # Fallback to akshare
    try:
        import akshare as ak

        df = ak.stock_hk_spot_em()
        hk_result = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", ""))
            if code in symbols:
                hk_result[code] = {
                    "symbol": code,
                    "name": str(row.get("名称", "")),
                    "price": float(row.get("最新价", 0) or 0),
                    "prev_close": float(row.get("昨收", 0) or 0),
                    "change": float(row.get("涨跌额", 0) or 0),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                    "currency": "HKD",
                    "source": "eastmoney_hk",
                }
        return hk_result
    except Exception as e:
        logger.error(f"HK stock fetch failed: {e}")
        return {}


async def fetch_us_stock_quotes_sina(symbols: list[str]) -> dict[str, dict]:
    """Fetch US stock quotes from Sina Finance (gb_ prefix)."""
    if not symbols:
        return {}
    try:
        # Strip .US suffix for Sina API: "MU.US" -> "mu", "AAPL" -> "aapl"
        clean_map = {}  # clean_lower -> original_symbol
        for s in symbols:
            clean = s.replace(".US", "").replace(".us", "")
            clean_map[clean.lower()] = s

        codes = [f"gb_{c}" for c in clean_map.keys()]
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        result = {}
        for line in resp.text.strip().split("\n"):
            parsed = _parse_sina_us_fields(line)
            if parsed:
                clean = parsed["symbol"].lower()
                if clean in clean_map:
                    parsed["symbol"] = clean_map[clean]  # Use original symbol like "MU.US"
                    result[clean_map[clean]] = parsed
        return result
    except Exception as e:
        logger.warning(f"Sina US stock fetch failed: {e}")
        return {}


async def fetch_us_stock_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch US stock quotes: Sina first, then yfinance fallback."""
    if not symbols:
        return {}
    # Try Sina first
    result = await fetch_us_stock_quotes_sina(symbols)
    if result:
        return result
    # Fallback to yfinance
    try:
        import yfinance as yf

        yf_result = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                if len(hist) >= 1:
                    latest = hist.iloc[-1]
                    prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else float(latest["Close"])
                    price = float(latest["Close"])
                    yf_result[symbol] = {
                        "symbol": symbol,
                        "name": getattr(ticker.fast_info, "shortName", symbol) or symbol,
                        "price": price,
                        "prev_close": prev_close,
                        "change": price - prev_close,
                        "change_pct": ((price - prev_close) / prev_close * 100) if prev_close else 0,
                        "currency": "USD",
                        "source": "yfinance",
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch US stock {symbol}: {e}")
        return yf_result
    except Exception as e:
        logger.error(f"US stock fetch failed: {e}")
        return {}


def _parse_futures_sina(symbol: str, raw: str) -> dict | None:
    """Parse a single sina futures quote line.
    Format: var hq_str_nf_RB2610="螺纹钢2610,持仓量,开盘,最高,最低,昨收,买,卖,最新,..."
    """
    try:
        parts = raw.split('="')
        if len(parts) < 2:
            return None
        values = parts[1].rstrip('"; \n').split(",")
        if len(values) < 19:
            return None
        name = values[0]
        price = float(values[8]) if values[8] else 0
        prev_close = float(values[5]) if values[5] else 0
        # Non-trading: price might be 0, use open or last known
        if price == 0:
            price = float(values[2]) if values[2] else prev_close
        if prev_close == 0:
            prev_close = price
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 4),
            "prev_close": round(prev_close, 4),
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "currency": "CNY",
            "source": "sina_futures",
        }
    except Exception:
        return None


async def fetch_futures_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch domestic futures quotes from Sina. Supports both main contract (RB0) and specific months (RB2610)."""
    if not symbols:
        return {}
    result = {}
    # Build sina codes: nf_ + uppercase symbol
    symbol_map = {}
    for s in symbols:
        code = f"nf_{s.upper()}"
        symbol_map[code] = s

    codes = list(symbol_map.keys())
    try:
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        for line in resp.text.strip().split("\n"):
            if '=""' in line:
                continue
            # Extract the sina code from var hq_str_nf_RB2610
            raw_code = line.split("str_")[-1].split("=")[0] if "str_" in line else ""
            orig_symbol = symbol_map.get(raw_code)
            if not orig_symbol:
                continue
            parsed = _parse_futures_sina(orig_symbol, line)
            if parsed and parsed["price"] > 0:
                result[orig_symbol] = parsed
    except Exception as e:
        logger.warning(f"Sina futures batch fetch failed: {e}")

    # Fallback to akshare for any symbols not found (main contract historical)
    missing = [s for s in symbols if s not in result]
    for symbol in missing:
        try:
            import akshare as ak
            # For main contracts like "RB0", try akshare
            df = ak.futures_main_sina(symbol=symbol, start_date="20260501", end_date="20991231")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) >= 2 else latest
                price = float(latest["收盘价"])
                prev_close = float(prev["收盘价"])
                result[symbol] = {
                    "symbol": symbol,
                    "name": symbol,
                    "price": price,
                    "prev_close": prev_close,
                    "change": round(price - prev_close, 2),
                    "change_pct": round((price - prev_close) / prev_close * 100, 4) if prev_close else 0,
                    "currency": "CNY",
                    "source": "akshare_futures",
                }
        except Exception as e2:
            logger.warning(f"Futures fallback for {symbol} failed: {e2}")

    return result


# Foreign futures symbol map: user-facing code → sina code
FOREIGN_FUTURES_MAP = {
    "GC": "GC", "SI": "SI", "HG": "HG",  # COMEX: 黄金、白银、铜
    "CL": "CL", "NG": "NG",  # NYMEX: 原油、天然气
    "XAU": "XAU", "XAG": "XAG",  # 伦敦金/银
    "OIL": "OIL",  # 布伦特原油
    "S": "S", "W": "W", "C": "C",  # CBOT: 黄豆、小麦、玉米
    "CT": "CT",  # NYBOT棉花
    "BTC": "BTC",  # CME比特币
}


async def fetch_foreign_futures_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch foreign futures real-time prices from Sina."""
    if not symbols:
        return {}
    result = {}
    try:
        import akshare as ak
        codes = [FOREIGN_FUTURES_MAP.get(s, s) for s in symbols]
        df = ak.futures_foreign_commodity_realtime(symbol=codes)
        if df is not None and not df.empty:
            # Map code → original symbol for reverse lookup
            code_to_symbol = {}
            for s in symbols:
                code_to_symbol[FOREIGN_FUTURES_MAP.get(s, s)] = s

            # akshare returns rows in same order as input codes
            for idx, row in df.iterrows():
                name = str(row.get("名称", ""))
                price = float(row.get("最新价", 0) or 0)
                prev_close = float(row.get("昨日结算价", 0) or 0)
                change = float(row.get("涨跌额", 0) or 0)
                change_pct = float(row.get("涨跌幅", 0) or 0)
                # Match by index position to input codes
                matched_symbol = symbols[idx] if idx < len(symbols) else None
                if not matched_symbol:
                    # Fallback: try matching by code
                    for code, orig in code_to_symbol.items():
                        if code in name:
                            matched_symbol = orig
                            break
                if matched_symbol and price > 0:
                    result[matched_symbol] = {
                        "symbol": matched_symbol,
                        "name": name,
                        "price": price,
                        "prev_close": prev_close,
                        "change": round(change, 4),
                        "change_pct": round(change_pct, 4),
                        "currency": "USD",
                        "source": "sina_foreign_futures",
                    }
    except Exception as e:
        logger.warning(f"Foreign futures fetch failed: {e}")
    return result


async def fetch_money_fund_quotes(symbols: list[str]) -> dict[str, dict]:
    """Fetch money fund daily yield (万份收益) and 7-day annualized rate from akshare."""
    if not symbols:
        return {}
    try:
        import akshare as ak

        df = ak.fund_money_fund_daily_em()
        # Columns: 基金代码, 基金简称, YYYY-MM-DD-万份收益, YYYY-MM-DD-7日年化%, ...
        symbol_set = set(symbols)
        result = {}
        for _, row in df.iterrows():
            code = str(row.get("基金代码", ""))
            if code not in symbol_set:
                continue
            name = str(row.get("基金简称", code))
            # Find the latest 万份收益 and 7日年化 columns
            yield_col = [c for c in df.columns if "万份收益" in c]
            rate_col = [c for c in df.columns if "7日年化" in c]
            daily_yield = float(row[yield_col[0]]) if yield_col else 0
            annualized = float(str(row[rate_col[0]]).replace("%", "")) if rate_col else 0
            result[code] = {
                "symbol": code,
                "name": name,
                "price": daily_yield,  # 万份收益 as price
                "prev_close": daily_yield,
                "change": 0,
                "change_pct": annualized,  # 7日年化收益率
                "currency": "CNY",
                "source": "eastmoney_money_fund",
            }
        # Fallback: for symbols not found in daily list, try individual query
        missing = symbol_set - set(result.keys())
        for symbol in missing:
            try:
                info = ak.fund_money_fund_info_em(symbol=symbol)
                if info is not None and not info.empty:
                    latest = info.iloc[-1]
                    daily_yield = float(latest.get("每万份收益", 0))
                    annualized = float(latest.get("7日年化收益率", 0))
                    result[symbol] = {
                        "symbol": symbol,
                        "name": symbol,
                        "price": daily_yield,
                        "prev_close": daily_yield,
                        "change": 0,
                        "change_pct": annualized,
                        "currency": "CNY",
                        "source": "eastmoney_money_fund",
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch money fund {symbol}: {e}")
        return result
    except Exception as e:
        logger.error(f"Money fund fetch failed: {e}")
        return {}


async def refresh_market_prices(db: AsyncSession) -> int:
    """Refresh all market prices for active holdings."""
    result = await db.execute(select(Holding))
    holdings = result.scalars().all()

    classified: dict[str, list[str]] = {
        "a_stock": [],
        "hk_stock": [],
        "us_stock": [],
        "fund": [],
        "money_fund": [],
        "futures": [],
        "foreign_futures": [],
    }
    for h in holdings:
        if h.asset_type == "money_fund":
            mtype = "money_fund"
        elif h.asset_type == "futures":
            # Check if foreign futures
            domestic_exchanges = {"SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"}
            if h.exchange and h.exchange not in domestic_exchanges:
                mtype = "foreign_futures"
            elif h.symbol in FOREIGN_FUTURES_MAP:
                mtype = "foreign_futures"
            else:
                mtype = "futures"
        else:
            mtype = _classify_symbol(h.symbol, h.exchange)
        if h.symbol not in classified[mtype]:
            classified[mtype].append(h.symbol)

    all_quotes = {}
    all_quotes.update(await fetch_a_stock_quotes(classified["a_stock"]))
    all_quotes.update(await fetch_hk_stock_quotes(classified["hk_stock"]))
    all_quotes.update(await fetch_us_stock_quotes(classified["us_stock"]))
    all_quotes.update(await fetch_fund_quotes(classified["fund"]))
    all_quotes.update(await fetch_money_fund_quotes(classified["money_fund"]))
    all_quotes.update(await fetch_futures_quotes(classified["futures"]))
    all_quotes.update(await fetch_foreign_futures_quotes(classified["foreign_futures"]))

    count = 0
    for symbol, quote in all_quotes.items():
        existing = await db.execute(select(MarketPrice).where(MarketPrice.symbol == symbol))
        mp = existing.scalar_one_or_none()
        if mp:
            # Skip update if new price is 0 but we have existing data
            if quote["price"] == 0 and float(mp.price) > 0:
                mp.updated_at = datetime.utcnow()
                count += 1
                continue
            mp.price = quote["price"]
            mp.name = quote["name"]
            mp.prev_close = quote["prev_close"]
            mp.change = quote["change"]
            mp.change_pct = quote["change_pct"]
            mp.currency = quote["currency"]
            mp.source = quote["source"]
            mp.updated_at = datetime.utcnow()
        else:
            mp = MarketPrice(**quote)
            db.add(mp)
        count += 1

    await db.commit()
    return count
