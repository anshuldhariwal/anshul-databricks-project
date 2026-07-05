from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STOCK_SYMBOLS = ("AAPL", "MSFT", "NVDA", "TSLA", "AMZN")
CRYPTO_PRODUCTS = {
    "BTC-USD": "BTCUSD",
    "ETH-USD": "ETHUSD",
    "SOL-USD": "SOLUSD",
}

NASDAQ_HISTORICAL_BASE_URL = "https://api.nasdaq.com/api/quote"
COINBASE_EXCHANGE_BASE_URL = "https://api.exchange.coinbase.com"


class MarketDataError(RuntimeError):
    pass


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


def fetch_coinbase_crypto_tickers(products: dict[str, str] = CRYPTO_PRODUCTS) -> list[dict[str, Any]]:
    records = []
    for product_id, symbol in products.items():
        payload = _request_json(
            f"{COINBASE_EXCHANGE_BASE_URL}/products/{product_id}/ticker",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )

        if not payload.get("price") or not payload.get("volume") or not payload.get("time"):
            raise MarketDataError(f"Unexpected Coinbase ticker response for {product_id}: {payload}")

        records.append(
            {
                "source": "coinbase",
                "asset_type": "crypto",
                "symbol": symbol,
                "price": payload.get("price"),
                "volume": payload.get("volume"),
                "event_time": payload.get("time"),
            }
        )
    return records


def fetch_market_data(include_stocks: bool = True, include_crypto: bool = True) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if include_stocks:
        records.extend(fetch_nasdaq_daily_stocks())
    if include_crypto:
        records.extend(fetch_coinbase_crypto_tickers())
    return records
