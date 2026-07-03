# Databricks notebook source
import csv
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import re

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType


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


run_timestamp = datetime.now(timezone.utc).isoformat()
current_principal, bronze_table, silver_table = table_names()
sample_orders_path = bundle_root() / "resources" / "sample_orders.csv"

print("Databricks bundle proof ingest started.")
print(f"UTC time: {run_timestamp}")
print(f"Current principal: {current_principal}")
print(f"Sample input: {sample_orders_path}")

with sample_orders_path.open("r", encoding="utf-8", newline="") as sample_orders_file:
    raw_orders = [
        (
            int(row["order_id"]),
            row["customer"],
            row["status"],
            float(row["amount"]),
        )
        for row in csv.DictReader(sample_orders_file)
    ]

orders_schema = StructType(
    [
        StructField("order_id", IntegerType(), nullable=False),
        StructField("customer", StringType(), nullable=False),
        StructField("status", StringType(), nullable=False),
        StructField("amount", DoubleType(), nullable=False),
    ]
)

bronze_orders = (
    spark.createDataFrame(raw_orders, schema=orders_schema)
    .withColumn("source_file", F.lit(sample_orders_path.name))
    .withColumn("ingested_at_utc", F.lit(run_timestamp))
)

bronze_orders.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    bronze_table
)

silver_orders = (
    spark.table(bronze_table)
    .where(F.col("status") == "complete")
    .withColumn("amount_bucket", F.when(F.col("amount") >= 50, "high").otherwise("standard"))
    .select("order_id", "customer", "amount", "amount_bucket", "source_file", "ingested_at_utc")
)

silver_orders.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    silver_table
)

print("Bronze Delta table:", bronze_table)
print("Silver Delta table:", silver_table)
print("Ingest and transform complete.")
