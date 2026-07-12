from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class CloudflareUploadError(RuntimeError):
    pass


def upload_kv_value(input_path: Path, key_name: str) -> None:
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    namespace_id = os.environ.get("CLOUDFLARE_KV_NAMESPACE_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")

    if not account_id or not namespace_id or not api_token:
        raise CloudflareUploadError(
            "CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_KV_NAMESPACE_ID, and CLOUDFLARE_API_TOKEN are required."
        )

    body = input_path.read_bytes()
    request = Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key_name}",
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CloudflareUploadError(f"Cloudflare KV upload failed: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise CloudflareUploadError(f"Could not reach Cloudflare API: {exc.reason}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload dashboard JSON to Cloudflare KV.")
    parser.add_argument("--input", default="frontend/latest_market_summary.json")
    parser.add_argument("--key", default=os.environ.get("CLOUDFLARE_MARKET_SUMMARY_KEY", "latest_market_summary.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    upload_kv_value(Path(args.input), args.key)
    print(f"Uploaded {args.input} to Cloudflare KV key {args.key}")


if __name__ == "__main__":
    main()
