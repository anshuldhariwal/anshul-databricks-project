from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


TARGET_FIELDS = (
    "source",
    "asset_type",
    "symbol",
    "price",
    "volume",
    "event_time",
    "ingestion_time",
    "batch_id",
)


def _decimal_string(value: Any) -> str:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid numeric value: {value!r}") from exc

    if decimal_value <= 0:
        raise ValueError(f"Expected positive numeric value, got {value!r}")

    return format(decimal_value, "f")


def normalize_records(records: Iterable[dict[str, Any]], batch_id: str | None = None) -> list[dict[str, str]]:
    resolved_batch_id = batch_id or str(uuid4())
    ingestion_time = datetime.now(timezone.utc).isoformat()
    normalized = []

    for record in records:
        source = str(record.get("source", "")).strip().lower()
        asset_type = str(record.get("asset_type", "")).strip().lower()
        symbol = str(record.get("symbol", "")).strip().upper()
        event_time = str(record.get("event_time", "")).strip()

        if source not in {"nasdaq", "coinbase"}:
            raise ValueError(f"Unsupported source: {source!r}")
        if asset_type not in {"stock", "crypto"}:
            raise ValueError(f"Unsupported asset_type: {asset_type!r}")
        if not symbol:
            raise ValueError("Symbol is required.")
        if not event_time:
            raise ValueError(f"event_time is required for {symbol}.")

        normalized.append(
            {
                "source": source,
                "asset_type": asset_type,
                "symbol": symbol,
                "price": _decimal_string(record.get("price")),
                "volume": _decimal_string(record.get("volume")),
                "event_time": event_time,
                "ingestion_time": ingestion_time,
                "batch_id": resolved_batch_id,
            }
        )

    return normalized


def write_jsonl(records: Iterable[dict[str, str]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True))
            output_file.write("\n")
    return output_path
