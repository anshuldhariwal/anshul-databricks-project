# Databricks notebook source
from datetime import datetime, timezone

print("GitHub Actions to Databricks proof succeeded.")
print(f"UTC time: {datetime.now(timezone.utc).isoformat()}")

spark.range(1).withColumnRenamed("id", "proof_value").show()
