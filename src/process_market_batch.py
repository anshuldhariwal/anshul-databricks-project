# Databricks notebook source
from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

# MAGIC %run ./market_common

# COMMAND ----------

market_schema = StructType(
    [
        StructField("source", StringType(), nullable=False),
        StructField("asset_type", StringType(), nullable=False),
        StructField("symbol", StringType(), nullable=False),
        StructField("price", StringType(), nullable=False),
        StructField("volume", StringType(), nullable=False),
        StructField("event_time", StringType(), nullable=False),
        StructField("ingestion_time", StringType(), nullable=False),
        StructField("batch_id", StringType(), nullable=False),
    ]
)


bundle_target = dbutils.widgets.get("bundle_target")
(
    current_principal,
    bronze_table,
    silver_table,
    gold_table,
    gold_top_stock_table,
    gold_top_crypto_table,
) = market_table_names(bundle_target)
root_path = bundle_root()
latest_batch_path = root_path / "sample_data" / "latest_market_batch.jsonl"
sample_batch_path = root_path / "sample_data" / "sample_market_batch.jsonl"
input_batch_path = latest_batch_path if latest_batch_path.exists() else sample_batch_path

print("Market batch processing started.")
print(f"Bundle target: {bundle_target}")
print(f"Current principal: {current_principal}")
print(f"Input batch: {input_batch_path}")

bronze_df = (
    spark.read.schema(market_schema)
    .json(str(input_batch_path))
    .withColumn("source_file", F.lit(input_batch_path.name))
)

bronze_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    bronze_table
)

silver_df = (
    spark.table(bronze_table)
    .withColumn("source", F.lower(F.trim(F.col("source"))))
    .withColumn("asset_type", F.lower(F.trim(F.col("asset_type"))))
    .withColumn("symbol", F.upper(F.trim(F.col("symbol"))))
    .withColumn("price", F.col("price").cast(DoubleType()))
    .withColumn("volume", F.col("volume").cast(DoubleType()))
    .withColumn("event_time", F.to_timestamp("event_time"))
    .withColumn("ingestion_time", F.to_timestamp("ingestion_time"))
    .where(F.col("source").isin("nasdaq", "coinbase"))
    .where(F.col("asset_type").isin("stock", "crypto"))
    .where(F.col("symbol").isNotNull() & (F.col("symbol") != ""))
    .where(F.col("price").isNotNull() & (F.col("price") > 0))
    .where(F.col("volume").isNotNull() & (F.col("volume") > 0))
    .where(F.col("event_time").isNotNull())
    .dropDuplicates(["batch_id", "symbol", "event_time"])
)

silver_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    silver_table
)

latest_window = Window.partitionBy("symbol").orderBy(F.col("event_time").desc())
summary_df = (
    spark.table(silver_table)
    .withColumn("rank", F.row_number().over(latest_window))
    .where(F.col("rank") == 1)
    .groupBy("symbol", "asset_type")
    .agg(
        F.first("price").alias("latest_price"),
        F.first("volume").alias("volume"),
        F.max("event_time").alias("last_updated"),
        F.min("price").alias("low"),
        F.max("price").alias("high"),
    )
    .withColumn("previous_price", F.lit(None).cast(DoubleType()))
    .withColumn("price_change", F.lit(None).cast(DoubleType()))
    .withColumn("price_change_percent", F.lit(None).cast(DoubleType()))
    .select(
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
    )
)

summary_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    gold_table
)

rank_window = Window.partitionBy("asset_type").orderBy(F.col("transaction_value").desc())
top_transactions_df = (
    spark.table(silver_table)
    .withColumn("transaction_value", F.col("price") * F.col("volume"))
    .withColumn("rank", F.row_number().over(rank_window))
    .where(F.col("rank") <= 5)
    .select(
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
    )
)

top_transactions_df.where(F.col("asset_type") == "stock").write.format("delta").mode(
    "overwrite"
).option("overwriteSchema", "true").saveAsTable(gold_top_stock_table)

top_transactions_df.where(F.col("asset_type") == "crypto").write.format("delta").mode(
    "overwrite"
).option("overwriteSchema", "true").saveAsTable(gold_top_crypto_table)

print("Bronze market table:", bronze_table)
print("Silver market table:", silver_table)
print("Gold market table:", gold_table)
print("Gold top stock transactions table:", gold_top_stock_table)
print("Gold top crypto transactions table:", gold_top_crypto_table)
print("Market batch processing complete.")
