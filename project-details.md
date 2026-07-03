# Databricks Free Automation Proof

Goal: prove that GitHub Actions can validate, deploy, and manually run a small Databricks Asset Bundle while staying inside free-tier boundaries.

Current constraints:
- Use Databricks Free Edition.
- Use serverless job compute only.
- Run from GitHub Actions only when manually triggered.
- Avoid custom clusters, pipelines, model serving, scheduled triggers, and paid/admin-only setup.
- Authenticate with a Databricks workspace personal access token stored as a GitHub secret.

Proof target:
- One Databricks Asset Bundle.
- One ingest/transform notebook task that reads `resources/sample_orders.csv` and writes tiny managed Bronze and Silver Delta tables.
- One validation notebook task that checks row counts, schemas, and Silver filtering.
- Principal-specific table names to avoid local user and CI service-principal ownership conflicts.
- One GitHub Actions workflow using `databricks/setup-cli`.
- Manual `workflow_dispatch` trigger only.
