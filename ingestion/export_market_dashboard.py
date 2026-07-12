from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha1
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class DatabricksExportError(RuntimeError):
    pass


def request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: Any = None) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=30) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DatabricksExportError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except URLError as exc:
        raise DatabricksExportError(f"Could not reach {url}: {exc.reason}") from exc

    return json.loads(raw_body) if raw_body else {}


def databricks_host() -> str:
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    if not host:
        raise DatabricksExportError("DATABRICKS_HOST is required.")
    return host


def databricks_token() -> str:
    token = os.environ.get("DATABRICKS_ACCESS_TOKEN")
    if token:
        return token

    client_id = os.environ.get("DATABRICKS_CLIENT_ID")
    client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise DatabricksExportError(
            "Set DATABRICKS_ACCESS_TOKEN or DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET."
        )

    host = databricks_host()
    token_payload = urlencode(
        {
            "grant_type": "client_credentials",
            "scope": "all-apis",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    request = Request(
        f"{host}/oidc/v1/token",
        data=token_payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DatabricksExportError(f"Could not get Databricks OAuth token: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise DatabricksExportError(f"Could not reach Databricks OAuth endpoint: {exc.reason}") from exc

    access_token = payload.get("access_token")
    if not access_token:
        raise DatabricksExportError(f"Databricks OAuth response did not include access_token: {payload}")
    return access_token


def statement_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def execute_statement(sql: str, *, warehouse_id: str, token: str) -> dict[str, Any]:
    host = databricks_host()
    statement = request_json(
        f"{host}/api/2.0/sql/statements",
        method="POST",
        headers=statement_headers(token),
        body={
            "warehouse_id": warehouse_id,
            "statement": sql,
            "wait_timeout": "10s",
            "on_wait_timeout": "CONTINUE",
        },
    )
    statement_id = statement.get("statement_id")
    state = statement.get("status", {}).get("state")

    while state in {"PENDING", "RUNNING"}:
        if not statement_id:
            raise DatabricksExportError(f"Statement did not return statement_id: {statement}")
        time.sleep(2)
        statement = request_json(
            f"{host}/api/2.0/sql/statements/{statement_id}",
            headers=statement_headers(token),
        )
        state = statement.get("status", {}).get("state")

    if state != "SUCCEEDED":
        raise DatabricksExportError(f"Statement failed: {statement}")

    return statement


def rows_from_statement(statement: dict[str, Any]) -> list[dict[str, Any]]:
    columns = [
        column.get("name")
        for column in statement.get("manifest", {}).get("schema", {}).get("columns", [])
    ]
    data_array = statement.get("result", {}).get("data_array", [])
    return [dict(zip(columns, row)) for row in data_array]


def scalar(sql: str, *, warehouse_id: str, token: str) -> str:
    rows = rows_from_statement(execute_statement(sql, warehouse_id=warehouse_id, token=token))
    if not rows:
        raise DatabricksExportError(f"Scalar query returned no rows: {sql}")
    return str(next(iter(rows[0].values())))


def table_suffix(bundle_target: str, current_principal: str) -> str:
    principal_key = re.sub(r"[^a-z0-9_]", "_", current_principal.lower())
    principal_hash = sha1(current_principal.encode("utf-8")).hexdigest()[:8]
    target_key = re.sub(r"[^a-z0-9_]", "_", bundle_target.lower())
    return f"{target_key}_{principal_key[:32]}_{principal_hash}"


def table_names(bundle_target: str, current_principal: str) -> dict[str, str]:
    suffix = table_suffix(bundle_target, current_principal)
    return {
        "bronze": f"bronze_market_events_{suffix}",
        "summary": f"gold_market_summary_{suffix}",
        "top_stocks": f"gold_top_stock_transactions_{suffix}",
        "top_crypto": f"gold_top_crypto_transactions_{suffix}",
    }


def query_rows(sql: str, *, warehouse_id: str, token: str) -> list[dict[str, Any]]:
    return rows_from_statement(execute_statement(sql, warehouse_id=warehouse_id, token=token))


def build_dashboard_payload(bundle_target: str, warehouse_id: str, token: str) -> dict[str, Any]:
    current_principal = scalar("SELECT current_user() AS current_user", warehouse_id=warehouse_id, token=token)
    names = table_names(bundle_target, current_principal)

    bronze_rows = query_rows(
        f"""
        SELECT source, asset_type, symbol, price, volume, event_time, ingestion_time, batch_id, source_file
        FROM `{names["bronze"]}`
        ORDER BY ingestion_time DESC, event_time DESC
        LIMIT 10
        """,
        warehouse_id=warehouse_id,
        token=token,
    )
    summary_rows = query_rows(
        f"""
        SELECT symbol, asset_type, latest_price, volume, high, low, last_updated
        FROM `{names["summary"]}`
        ORDER BY asset_type, symbol
        LIMIT 10
        """,
        warehouse_id=warehouse_id,
        token=token,
    )
    top_stock_rows = query_rows(
        f"""
        SELECT rank, symbol, price, volume, transaction_value, event_time
        FROM `{names["top_stocks"]}`
        ORDER BY rank
        LIMIT 5
        """,
        warehouse_id=warehouse_id,
        token=token,
    )
    top_crypto_rows = query_rows(
        f"""
        SELECT rank, symbol, price, volume, transaction_value, event_time
        FROM `{names["top_crypto"]}`
        ORDER BY rank
        LIMIT 5
        """,
        warehouse_id=warehouse_id,
        token=token,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_target": bundle_target,
        "principal": current_principal,
        "tables": names,
        "bronze": {
            "latest_records": bronze_rows,
        },
        "gold": {
            "latest_summary": summary_rows,
            "top_stock_transactions": top_stock_rows,
            "top_crypto_transactions": top_crypto_rows,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a compact Databricks market dashboard JSON.")
    parser.add_argument("--target", default=os.environ.get("BUNDLE_TARGET", "dev"))
    parser.add_argument("--output", default="frontend/latest_market_summary.json")
    parser.add_argument("--warehouse-id", default=os.environ.get("DATABRICKS_WAREHOUSE_ID"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.warehouse_id:
        raise DatabricksExportError("DATABRICKS_WAREHOUSE_ID is required.")

    token = databricks_token()
    payload = build_dashboard_payload(args.target, args.warehouse_id, token)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote dashboard JSON to {output_path}")


if __name__ == "__main__":
    main()
