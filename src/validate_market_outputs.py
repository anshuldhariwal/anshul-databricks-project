# Databricks notebook source
from pyspark.sql import functions as F

# MAGIC %run ./market_common


def require(condition, message):
    if not condition:
        raise ValueError(message)


bundle_target = dbutils.widgets.get("bundle_target")
(
    current_principal,
    bronze_table,
    silver_table,
    gold_table,
    gold_top_stock_table,
    gold_top_crypto_table,
) = market_table_names(bundle_target)

print("Market output validation started.")
print(f"Bundle target: {bundle_target}")
print(f"Current principal: {current_principal}")

bronze_df = spark.table(bronze_table)
silver_df = spark.table(silver_table)
gold_df = spark.table(gold_table)
gold_top_stock_df = spark.table(gold_top_stock_table)
gold_top_crypto_df = spark.table(gold_top_crypto_table)

required_bronze_columns = {
    "source",
    "asset_type",
    "symbol",
    "price",
    "volume",
    "event_time",
    "ingestion_time",
    "batch_id",
    "source_file",
}
required_silver_columns = {
    "source",
    "asset_type",
    "symbol",
    "price",
    "volume",
    "event_time",
    "ingestion_time",
    "batch_id",
    "source_file",
}
required_gold_columns = {
    "symbol",
    "asset_type",
    "latest_price",
    "previous_price",
    "price_change",
    "price_change_percent",
    "volume",
    "high",
    "low",
    "last_updated",
}
required_top_transaction_columns = {
    "rank",
    "source",
    "asset_type",
    "symbol",
    "price",
    "volume",
    "transaction_value",
    "event_time",
    "ingestion_time",
    "batch_id",
    "source_file",
}

require(set(bronze_df.columns) == required_bronze_columns, f"Unexpected Bronze columns: {bronze_df.columns}")
require(set(silver_df.columns) == required_silver_columns, f"Unexpected Silver columns: {silver_df.columns}")
require(set(gold_df.columns) == required_gold_columns, f"Unexpected Gold columns: {gold_df.columns}")
require(
    set(gold_top_stock_df.columns) == required_top_transaction_columns,
    f"Unexpected Gold stock transaction columns: {gold_top_stock_df.columns}",
)
require(
    set(gold_top_crypto_df.columns) == required_top_transaction_columns,
    f"Unexpected Gold crypto transaction columns: {gold_top_crypto_df.columns}",
)

bronze_count = bronze_df.count()
silver_count = silver_df.count()
gold_count = gold_df.count()
gold_top_stock_count = gold_top_stock_df.count()
gold_top_crypto_count = gold_top_crypto_df.count()

require(bronze_count > 0, "Bronze market table is empty.")
require(silver_count > 0, "Silver market table is empty.")
require(gold_count > 0, "Gold market summary is empty.")

null_required_count = silver_df.where(
    F.col("source").isNull()
    | F.col("asset_type").isNull()
    | F.col("symbol").isNull()
    | F.col("price").isNull()
    | F.col("volume").isNull()
    | F.col("event_time").isNull()
    | F.col("ingestion_time").isNull()
    | F.col("batch_id").isNull()
).count()
require(null_required_count == 0, f"Silver has {null_required_count} rows with null required fields.")

invalid_source_count = silver_df.where(~F.col("source").isin("alpha_vantage", "binance")).count()
invalid_asset_count = silver_df.where(~F.col("asset_type").isin("stock", "crypto")).count()
invalid_numeric_count = silver_df.where((F.col("price") <= 0) | (F.col("volume") <= 0)).count()

require(invalid_source_count == 0, f"Silver has {invalid_source_count} invalid sources.")
require(invalid_asset_count == 0, f"Silver has {invalid_asset_count} invalid asset types.")
require(invalid_numeric_count == 0, f"Silver has {invalid_numeric_count} invalid price/volume rows.")

duplicate_count = (
    silver_df.groupBy("batch_id", "symbol", "event_time")
    .count()
    .where(F.col("count") > 1)
    .count()
)
require(duplicate_count == 0, f"Silver has {duplicate_count} duplicate market ticks.")

gold_invalid_count = gold_df.where(
    F.col("symbol").isNull()
    | F.col("asset_type").isNull()
    | F.col("latest_price").isNull()
    | F.col("volume").isNull()
    | F.col("last_updated").isNull()
    | (F.col("latest_price") <= 0)
    | (F.col("volume") <= 0)
).count()
require(gold_invalid_count == 0, f"Gold has {gold_invalid_count} invalid rows.")

for table_label, top_df, expected_asset_type in [
    ("Gold top stock transactions", gold_top_stock_df, "stock"),
    ("Gold top crypto transactions", gold_top_crypto_df, "crypto"),
]:
    require(top_df.count() <= 5, f"{table_label} has more than 5 rows.")
    invalid_asset_type_count = top_df.where(F.col("asset_type") != expected_asset_type).count()
    invalid_rank_count = top_df.where((F.col("rank") < 1) | (F.col("rank") > 5)).count()
    invalid_value_count = top_df.where(
        F.col("transaction_value").isNull()
        | (F.col("transaction_value") <= 0)
        | (F.abs(F.col("transaction_value") - (F.col("price") * F.col("volume"))) > 0.0001)
    ).count()
    require(invalid_asset_type_count == 0, f"{table_label} has wrong asset_type rows.")
    require(invalid_rank_count == 0, f"{table_label} has invalid rank values.")
    require(invalid_value_count == 0, f"{table_label} has invalid transaction_value rows.")

print("Bronze market table:", bronze_table)
print("Silver market table:", silver_table)
print("Gold market table:", gold_table)
print("Gold top stock transactions table:", gold_top_stock_table)
print("Gold top crypto transactions table:", gold_top_crypto_table)
print(
    "Validation passed: "
    f"bronze_count={bronze_count}, silver_count={silver_count}, gold_count={gold_count}, "
    f"gold_top_stock_count={gold_top_stock_count}, gold_top_crypto_count={gold_top_crypto_count}"
)
