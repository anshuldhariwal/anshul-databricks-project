# Databricks notebook source
from hashlib import sha1
import re


def table_names():
    current_principal = spark.sql("SELECT current_user() AS current_user").first()["current_user"]
    principal_key = re.sub(r"[^a-z0-9_]", "_", current_principal.lower())
    principal_hash = sha1(current_principal.encode("utf-8")).hexdigest()[:8]
    table_suffix = f"{principal_key[:32]}_{principal_hash}"
    return (
        current_principal,
        f"proof_bronze_orders_{table_suffix}",
        f"proof_silver_orders_{table_suffix}",
    )


current_principal, bronze_table, silver_table = table_names()

print("Databricks bundle proof validation started.")
print(f"Current principal: {current_principal}")

bronze_df = spark.table(bronze_table)
silver_df = spark.table(silver_table)

bronze_count = bronze_df.count()
silver_count = silver_df.count()

if bronze_count != 4:
    raise ValueError(f"Expected 4 Bronze rows, found {bronze_count}")

if silver_count != 2:
    raise ValueError(f"Expected 2 Silver rows, found {silver_count}")

required_bronze_columns = {
    "order_id",
    "customer",
    "status",
    "amount",
    "source_file",
    "ingested_at_utc",
}
actual_bronze_columns = set(bronze_df.columns)

if required_bronze_columns != actual_bronze_columns:
    raise ValueError(f"Unexpected Bronze columns: {sorted(actual_bronze_columns)}")

required_silver_columns = {
    "order_id",
    "customer",
    "amount",
    "amount_bucket",
    "source_file",
    "ingested_at_utc",
}
actual_silver_columns = set(silver_df.columns)

if required_silver_columns != actual_silver_columns:
    raise ValueError(f"Unexpected Silver columns: {sorted(actual_silver_columns)}")

invalid_silver_status_count = bronze_df.join(silver_df, "order_id").where("status != 'complete'").count()

if invalid_silver_status_count != 0:
    raise ValueError(f"Found {invalid_silver_status_count} non-complete orders in Silver output")

print("Bronze Delta table:", bronze_table)
print("Silver Delta table:", silver_table)
print(f"Validation passed: bronze_count={bronze_count}, silver_count={silver_count}")
