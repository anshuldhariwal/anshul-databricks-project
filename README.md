# Anshul Databricks Project

This repository starts with a free-tier proof of automation for Databricks Free Edition.
The proof deploys and runs a Databricks Asset Bundle job that writes a tiny managed Bronze Delta table, derives a cleaned managed Silver Delta table, and validates the output.
Table names include a suffix derived from the current Databricks principal so local OAuth runs and GitHub service-principal runs do not fight over table ownership.

## GitHub Secrets

Add these repository secrets before running the workflow:

- `DATABRICKS_HOST`: your Databricks workspace URL, for example `https://dbc-xxxx.cloud.databricks.com`
- `DATABRICKS_CLIENT_ID`: the application/client ID for a Databricks service principal assigned to the workspace
- `DATABRICKS_CLIENT_SECRET`: an OAuth secret generated for that service principal

Personal access tokens can fail for bundle automation in CI because the Databricks CLI calls workspace identity APIs during validation. Use service-principal OAuth for GitHub Actions.

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
databricks bundle validate --target dev --profile DEFAULT
databricks bundle deploy --target dev --profile DEFAULT
databricks bundle run --target dev --profile DEFAULT proof_job
```
