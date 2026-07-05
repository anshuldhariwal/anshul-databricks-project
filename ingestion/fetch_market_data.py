from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STOCK_SYMBOLS = ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN")
CRYPTO_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
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


def fetch_alpha_vantage_daily_stocks(symbols: tuple[str, ...] = STOCK_SYMBOLS) -> list[dict[str, Any]]:
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")

    if not api_key:
        raise MarketDataError("ALPHA_VANTAGE_API_KEY is required for stock data.")

    records = []
    for symbol in symbols:
        query = urlencode(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": api_key,
            }
        )
        payload = _request_json(f"{ALPHA_VANTAGE_BASE_URL}?{query}")

        if "Note" in payload or "Information" in payload:
            raise MarketDataError(f"Alpha Vantage rate limit or notice for {symbol}: {payload}")
        if "Error Message" in payload:
            raise MarketDataError(f"Alpha Vantage error for {symbol}: {payload['Error Message']}")

        daily_series = payload.get("Time Series (Daily)")
        if not isinstance(daily_series, dict) or not daily_series:
            raise MarketDataError(f"Unexpected Alpha Vantage response shape for {symbol}: {payload}")

        latest_day = max(daily_series)
        latest_bar = daily_series[latest_day]
        records.append(
            {
                "source": "alpha_vantage",
                "asset_type": "stock",
                "symbol": symbol,
                "price": latest_bar.get("4. close"),
                "volume": latest_bar.get("5. volume"),
                "event_time": f"{latest_day}T00:00:00+00:00",
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
        records.extend(fetch_alpha_vantage_daily_stocks())
    if include_crypto:
        records.extend(fetch_binance_24hr_tickers())
    return records
