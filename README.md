# Anshul Databricks Project

This repository starts with a free-tier proof of automation for Databricks Free Edition.

## GitHub Secrets

Add these repository secrets before running the workflow:

- `DATABRICKS_HOST`: your Databricks workspace URL, for example `https://dbc-xxxx.cloud.databricks.com`
- `DATABRICKS_TOKEN`: your Databricks personal access token with all API access

## Run The Proof

1. Push this repository to GitHub.
2. Open Actions.
3. Select `Databricks Bundle Proof`.
4. Choose `Run workflow`.
5. Leave `run_job` as `true` to validate, deploy, and run the proof job.

The workflow is manual only to avoid accidental Databricks Free Edition quota usage.

## Local Commands

If the Databricks CLI is installed locally and authenticated:

```bash
databricks bundle validate --target dev
databricks bundle deploy --target dev
databricks bundle run --target dev proof_job
```
