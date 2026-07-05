from __future__ import annotations

import argparse
from pathlib import Path

from fetch_market_data import fetch_market_data
from normalize_market_data import normalize_records, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and normalize a small market data batch.")
    parser.add_argument(
        "--output",
        default="sample_data/latest_market_batch.jsonl",
        help="JSONL output path for the normalized market batch.",
    )
    parser.add_argument(
        "--crypto-only",
        action="store_true",
        help="Fetch Coinbase crypto data only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_records = fetch_market_data(include_stocks=not args.crypto_only, include_crypto=True)
    normalized_records = normalize_records(raw_records)
    output_path = write_jsonl(normalized_records, Path(args.output))
    print(f"Wrote {len(normalized_records)} normalized records to {output_path}")


if __name__ == "__main__":
    main()
