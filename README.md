# Anshul Databricks Project

This repository starts with a free-tier proof of automation for Databricks Free Edition.
The proof deploys and runs a Databricks Asset Bundle job that reads a committed sample CSV, writes a tiny managed Bronze Delta table, derives a cleaned managed Silver Delta table, and validates the output in a separate task.
Table names include a suffix derived from the bundle target and current Databricks principal so `dev`, `prod`, local OAuth runs, and GitHub service-principal runs stay isolated.

## GitHub Secrets

Add these repository secrets before running the workflow:

- `DATABRICKS_HOST`: your Databricks workspace URL, for example `https://dbc-xxxx.cloud.databricks.com`
- `DATABRICKS_CLIENT_ID`: the application/client ID for a Databricks service principal assigned to the workspace
- `DATABRICKS_CLIENT_SECRET`: an OAuth secret generated for that service principal

Personal access tokens can fail for bundle automation in CI because the Databricks CLI calls workspace identity APIs during validation. Use service-principal OAuth for GitHub Actions.

## Run The Proof

Pushes to `main` automatically validate the `dev` bundle target. They do not deploy or run the Databricks job.

To deploy and run manually:

1. Open Actions.
2. Select `Databricks Bundle Proof`.
3. Choose `Run workflow`.
4. Select `dev` or `prod`.
5. Leave `run_job` as `true` to validate, deploy, and run the proof job.

For production-like approval, create GitHub Environments named `dev` and `prod`, then add required reviewers to `prod`.

## Local Commands

If the Databricks CLI is installed locally and authenticated:

```bash
databricks bundle validate --target dev --profile DEFAULT
databricks bundle deploy --target dev --profile DEFAULT
databricks bundle run --target dev --profile DEFAULT proof_job
```

Use `--target prod` for the production target after validating the development target.
