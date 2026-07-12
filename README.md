# Anshul Databricks Project

This repository starts with a free-tier proof of automation for Databricks Free Edition.
The proof deploys and runs a Databricks Asset Bundle job that reads a committed sample CSV, writes a tiny managed Bronze Delta table, derives a cleaned managed Silver Delta table, and validates the output in a separate task.
Table names include a suffix derived from the bundle target and current Databricks principal so `dev`, `prod`, local OAuth runs, and GitHub service-principal runs stay isolated.

## GitHub Secrets

Add these repository secrets before running the workflow:

- `DATABRICKS_HOST`: your Databricks workspace URL, for example `https://dbc-xxxx.cloud.databricks.com`
- `DATABRICKS_CLIENT_ID`: the application/client ID for a Databricks service principal assigned to the workspace
- `DATABRICKS_CLIENT_SECRET`: an OAuth secret generated for that service principal
- `DATABRICKS_WAREHOUSE_ID`: SQL warehouse ID used to export compact dashboard JSON
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID for dashboard JSON upload
- `CLOUDFLARE_KV_NAMESPACE_ID`: Cloudflare KV namespace ID for dashboard JSON
- `CLOUDFLARE_API_TOKEN`: Cloudflare API token with write access to that KV namespace

Personal access tokens can fail for bundle automation in CI because the Databricks CLI calls workspace identity APIs during validation. Use service-principal OAuth for GitHub Actions.
Cloudflare KV upload is optional. If the Cloudflare secrets are not present, the workflow still deploys the static dashboard to GitHub Pages.

## Run The Proof

Pushes to `main` automatically validate the `dev` bundle target. They do not deploy or run the Databricks job.

Scheduled runs are intentionally paused until the dashboard export/upload flow is fully concrete. The workflow contains commented schedule entries for:

- Hourly market refresh at minute 17 UTC.
- Daily cleanup at 02:43 UTC.

To deploy and run manually:

1. Open Actions.
2. Select `Databricks Bundle Proof`.
3. Choose `Run workflow`.
4. Select `dev` or `prod`.
5. Leave `run_job` as `true` to validate, deploy, and run the selected bundle job.
6. Choose `proof_job`, `market_data_job`, or `cleanup_proof_tables`.

For production-like approval, create GitHub Environments named `dev` and `prod`, then add required reviewers to `prod`.

## Local Commands

If the Databricks CLI is installed locally and authenticated:

```bash
databricks bundle validate --target dev --profile DEFAULT
databricks bundle deploy --target dev --profile DEFAULT
databricks bundle run --target dev --profile DEFAULT proof_job
```

Use `--target prod` for the production target after validating the development target.

## Market Data Milestone

Milestone 3 starts the portfolio lakehouse shape from `project-details.md` without changing the existing GitHub Actions workflow yet.

Data providers:

- Stocks: Nasdaq historical quote data
- Crypto: Coinbase Exchange ticker API

The API calls run outside Databricks. Databricks processes a normalized JSONL batch with this schema:

- `source`
- `asset_type`
- `symbol`
- `price`
- `volume`
- `event_time`
- `ingestion_time`
- `batch_id`

Create a local crypto-only test batch without secrets:

```bash
python ingestion/run_pipeline.py --crypto-only
```

Create a stock + crypto batch:

```bash
python ingestion/run_pipeline.py
```

The stock fetch uses delayed Nasdaq historical quote data and does not require an API key. The crypto fetch uses Coinbase Exchange public ticker data.

In GitHub Actions, select `market_data_job` from the manual `bundle_job` input. The workflow fetches a fresh `sample_data/latest_market_batch.jsonl` before deploying the bundle, then Databricks processes that batch.

After the market job succeeds, GitHub Actions queries Databricks through the SQL Statement API, writes `frontend/latest_market_summary.json`, and uploads that compact JSON to Cloudflare KV.
The same `frontend/` directory is deployed to GitHub Pages so the existing portfolio can link to this project page without needing a public trigger endpoint.

The dashboard JSON stays small:

- latest Bronze sample records: up to 10 rows
- Gold latest summary: up to 10 rows
- Gold top stock transactions: up to 5 rows
- Gold top crypto transactions: up to 5 rows

The committed replay batch is `sample_data/sample_market_batch.jsonl`. The Databricks market job reads that file from the deployed bundle and writes:

- Bronze: raw market events
- Silver: typed, cleaned, deduplicated market ticks
- Gold: latest market summary
- Gold: top 5 stock transactions by `price * volume`
- Gold: top 5 crypto transactions by `price * volume`

Run the market batch job locally:

```bash
databricks bundle validate --target dev --profile DEFAULT
databricks bundle deploy --target dev --profile DEFAULT
databricks bundle run --target dev --profile DEFAULT market_data_job
```

Run cleanup manually when proof tables get noisy:

```bash
databricks bundle run --target dev --profile DEFAULT cleanup_proof_tables
```

Do not store Databricks, Cloudflare, or other secrets in this repository.
