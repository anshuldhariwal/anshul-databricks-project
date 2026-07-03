# Databricks notebook source
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

run_timestamp = datetime.now(timezone.utc).isoformat()
bronze_table = "proof_bronze_orders"
silver_table = "proof_silver_orders"

print("GitHub Actions to Databricks proof started.")
print(f"UTC time: {run_timestamp}")

orders_schema = StructType(
    [
        StructField("order_id", IntegerType(), nullable=False),
        StructField("customer", StringType(), nullable=False),
        StructField("status", StringType(), nullable=False),
        StructField("amount", DoubleType(), nullable=False),
    ]
)

raw_orders = [
    (1001, "Anshul", "complete", 49.99),
    (1002, "Maya", "pending", 15.50),
    (1003, "Ravi", "complete", 84.20),
    (1004, "Anshul", "cancelled", 12.00),
]

bronze_orders = (
    spark.createDataFrame(raw_orders, schema=orders_schema)
    .withColumn("ingested_at_utc", F.lit(run_timestamp))
)

bronze_orders.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    bronze_table
)

silver_orders = (
    spark.table(bronze_table)
    .where(F.col("status") == "complete")
    .withColumn("amount_bucket", F.when(F.col("amount") >= 50, "high").otherwise("standard"))
    .select("order_id", "customer", "amount", "amount_bucket", "ingested_at_utc")
)

silver_orders.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    silver_table
)

bronze_count = spark.table(bronze_table).count()
silver_count = spark.table(silver_table).count()

if bronze_count != 4:
    raise ValueError(f"Expected 4 Bronze rows, found {bronze_count}")

if silver_count != 2:
    raise ValueError(f"Expected 2 Silver rows, found {silver_count}")

required_silver_columns = {"order_id", "customer", "amount", "amount_bucket", "ingested_at_utc"}
actual_silver_columns = set(spark.table(silver_table).columns)

if required_silver_columns != actual_silver_columns:
    raise ValueError(f"Unexpected Silver columns: {sorted(actual_silver_columns)}")

print("Bronze Delta table:", bronze_table)
print("Silver Delta table:", silver_table)
print(f"Validation passed: bronze_count={bronze_count}, silver_count={silver_count}")
