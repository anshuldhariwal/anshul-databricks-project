# Databricks notebook source
# MAGIC %run ./market_common


bundle_target = dbutils.widgets.get("bundle_target")
current_principal, proof_bronze_table, proof_silver_table = proof_order_table_names(bundle_target)
(
    _,
    market_bronze_table,
    market_silver_table,
    market_gold_table,
    market_gold_top_stock_table,
    market_gold_top_crypto_table,
) = market_table_names(bundle_target)

tables_to_drop = [
    proof_bronze_table,
    proof_silver_table,
    market_bronze_table,
    market_silver_table,
    market_gold_table,
    market_gold_top_stock_table,
    market_gold_top_crypto_table,
]

print("Proof table cleanup started.")
print(f"Bundle target: {bundle_target}")
print(f"Current principal: {current_principal}")

for table_name in tables_to_drop:
    spark.sql(f"DROP TABLE IF EXISTS `{table_name}`")
    print(f"Dropped table if it existed: {table_name}")

print("Proof table cleanup complete.")
