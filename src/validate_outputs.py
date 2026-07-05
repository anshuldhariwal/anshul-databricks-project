# Databricks notebook source
from hashlib import sha1
import re


def table_names(bundle_target):
    current_principal = spark.sql("SELECT current_user() AS current_user").first()["current_user"]
    principal_key = re.sub(r"[^a-z0-9_]", "_", current_principal.lower())
    principal_hash = sha1(current_principal.encode("utf-8")).hexdigest()[:8]
    target_key = re.sub(r"[^a-z0-9_]", "_", bundle_target.lower())
    table_suffix = f"{target_key}_{principal_key[:32]}_{principal_hash}"
    return (
        current_principal,
        f"proof_bronze_orders_{table_suffix}",
        f"proof_silver_orders_{table_suffix}",
    )


bundle_target = dbutils.widgets.get("bundle_target")
current_principal, bronze_table, silver_table = table_names(bundle_target)

print("Databricks bundle proof validation started.")
print(f"Bundle target: {bundle_target}")
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

duplicate_bronze_orders = bronze_df.groupBy("order_id").count().where("count > 1").count()

if duplicate_bronze_orders != 0:
    raise ValueError(f"Found {duplicate_bronze_orders} duplicate order_id values in Bronze")

null_required_bronze_rows = bronze_df.where(
    "order_id IS NULL OR customer IS NULL OR status IS NULL OR amount IS NULL"
).count()

if null_required_bronze_rows != 0:
    raise ValueError(f"Found {null_required_bronze_rows} Bronze rows with null required fields")

invalid_bronze_amount_rows = bronze_df.where("amount <= 0").count()

if invalid_bronze_amount_rows != 0:
    raise ValueError(f"Found {invalid_bronze_amount_rows} Bronze rows with non-positive amounts")

invalid_silver_amount_rows = silver_df.where("amount <= 0").count()

if invalid_silver_amount_rows != 0:
    raise ValueError(f"Found {invalid_silver_amount_rows} Silver rows with non-positive amounts")

invalid_amount_bucket_rows = silver_df.where(
    "(amount >= 50 AND amount_bucket != 'high') OR (amount < 50 AND amount_bucket != 'standard')"
).count()

if invalid_amount_bucket_rows != 0:
    raise ValueError(f"Found {invalid_amount_bucket_rows} Silver rows with invalid amount_bucket values")

expected_silver_order_ids = {row["order_id"] for row in bronze_df.where("status = 'complete'").select("order_id").collect()}
actual_silver_order_ids = {row["order_id"] for row in silver_df.select("order_id").collect()}

if expected_silver_order_ids != actual_silver_order_ids:
    raise ValueError(
        "Silver order_id set does not match complete Bronze orders: "
        f"expected={sorted(expected_silver_order_ids)}, actual={sorted(actual_silver_order_ids)}"
    )

print("Bronze Delta table:", bronze_table)
print("Silver Delta table:", silver_table)
print(f"Validation passed: bronze_count={bronze_count}, silver_count={silver_count}")
