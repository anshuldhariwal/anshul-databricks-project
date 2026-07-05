# Databricks notebook source
from hashlib import sha1
from pathlib import Path
import re

from pyspark.sql import SparkSession


spark = SparkSession.builder.getOrCreate()


def bundle_root():
    if "__file__" in globals():
        current_file = Path(__file__).resolve()
    else:
        notebook_path = (
            dbutils.notebook.entry_point.getDbutils()
            .notebook()
            .getContext()
            .notebookPath()
            .get()
        )
        if notebook_path.startswith("/Workspace/"):
            current_file = Path(notebook_path)
        else:
            current_file = Path("/Workspace") / notebook_path.lstrip("/")

    if current_file.parent.name == "src":
        return current_file.parent.parent
    return current_file.parent


def principal_suffix(bundle_target):
    current_principal = spark.sql("SELECT current_user() AS current_user").first()["current_user"]
    principal_key = re.sub(r"[^a-z0-9_]", "_", current_principal.lower())
    principal_hash = sha1(current_principal.encode("utf-8")).hexdigest()[:8]
    target_key = re.sub(r"[^a-z0-9_]", "_", bundle_target.lower())
    return current_principal, f"{target_key}_{principal_key[:32]}_{principal_hash}"


def market_table_names(bundle_target):
    current_principal, table_suffix = principal_suffix(bundle_target)
    return (
        current_principal,
        f"bronze_market_events_{table_suffix}",
        f"silver_market_ticks_{table_suffix}",
        f"gold_market_summary_{table_suffix}",
        f"gold_top_stock_transactions_{table_suffix}",
        f"gold_top_crypto_transactions_{table_suffix}",
    )


def proof_order_table_names(bundle_target):
    current_principal, table_suffix = principal_suffix(bundle_target)
    return (
        current_principal,
        f"proof_bronze_orders_{table_suffix}",
        f"proof_silver_orders_{table_suffix}",
    )
