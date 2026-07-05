from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STOCK_SYMBOLS = ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN")
CRYPTO_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

NASDAQ_HISTORICAL_BASE_URL = "https://api.nasdaq.com/api/quote"
BINANCE_BASE_URL = "https://api.binance.com"


class MarketDataError(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> Any:
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MarketDataError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise MarketDataError(f"Could not reach {url}: {exc.reason}") from exc

    return json.loads(body)


def _clean_market_number(value: Any) -> str:
    return str(value).replace("$", "").replace(",", "").strip()


def fetch_nasdaq_daily_stocks(symbols: tuple[str, ...] = STOCK_SYMBOLS) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=45)
    records = []
    for symbol in symbols:
        query = urlencode(
            {
                "assetclass": "stocks",
                "fromdate": from_date.isoformat(),
                "todate": today.isoformat(),
                "limit": "5",
            }
        )
        payload = _request_json(
            f"{NASDAQ_HISTORICAL_BASE_URL}/{symbol}/historical?{query}",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )

        status = payload.get("status", {})
        if status.get("rCode") != 200:
            raise MarketDataError(f"Nasdaq error for {symbol}: {payload}")

        rows = payload.get("data", {}).get("tradesTable", {}).get("rows", [])
        rows = [row for row in rows if row.get("date") and row.get("close") and row.get("volume")]
        if not rows:
            raise MarketDataError(f"Nasdaq returned no historical rows for {symbol}: {payload}")

        latest_bar = rows[0]
        event_date = datetime.strptime(latest_bar["date"], "%m/%d/%Y").date()

        records.append(
            {
                "source": "nasdaq",
                "asset_type": "stock",
                "symbol": symbol,
                "price": _clean_market_number(latest_bar["close"]),
                "volume": _clean_market_number(latest_bar["volume"]),
                "event_time": f"{event_date.isoformat()}T00:00:00+00:00",
            }
        )
    return records


def fetch_binance_24hr_tickers(symbols: tuple[str, ...] = CRYPTO_SYMBOLS) -> list[dict[str, Any]]:
    query = urlencode({"symbols": json.dumps(list(symbols), separators=(",", ":"))})
    url = f"{BINANCE_BASE_URL}/api/v3/ticker/24hr?{query}"
    payload = _request_json(url)

    if not isinstance(payload, list):
        raise MarketDataError(f"Unexpected Binance response shape: {payload}")

    records = []
    for ticker in payload:
        close_time_ms = ticker.get("closeTime")
        event_time = (
            datetime.fromtimestamp(close_time_ms / 1000, tz=timezone.utc).isoformat()
            if isinstance(close_time_ms, int)
            else utc_now_iso()
        )
        records.append(
            {
                "source": "binance",
                "asset_type": "crypto",
                "symbol": ticker.get("symbol"),
                "price": ticker.get("lastPrice"),
                "volume": ticker.get("volume"),
                "event_time": event_time,
            }
        )
    return records


def fetch_market_data(include_stocks: bool = True, include_crypto: bool = True) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if include_stocks:
        records.extend(fetch_nasdaq_daily_stocks())
    if include_crypto:
        records.extend(fetch_binance_24hr_tickers())
    return records
