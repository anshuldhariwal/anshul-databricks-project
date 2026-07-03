# Databricks Automation Project

Goal: build a small but production-shaped Databricks Asset Bundle workflow while staying inside free-tier boundaries.

Current constraints:
- Use Databricks Free Edition.
- Use serverless job compute only.
- Auto-run validation from GitHub Actions on pushes to `main`.
- Deploy and run jobs only from manually triggered GitHub Actions runs.
- Avoid custom clusters, pipelines, model serving, scheduled triggers, and paid/admin-only setup.
- Authenticate GitHub Actions with Databricks service-principal OAuth secrets.
- Prefer local OAuth through the Databricks CLI `DEFAULT` profile.

Milestone 1 complete:
- One Databricks Asset Bundle.
- One ingest/transform notebook task that reads `resources/sample_orders.csv` and writes tiny managed Bronze and Silver Delta tables.
- One validation notebook task that checks row counts, schemas, and Silver filtering.
- Target- and principal-specific table names to avoid dev/prod and local/CI ownership conflicts.
- One GitHub Actions workflow using `databricks/setup-cli`.
- Manual `workflow_dispatch` deploy/run for `dev` and `prod`.
- `dev` and `prod` bundle targets with separate workspace root paths, job names, and table names.

Milestone 2 target:
- Treat GitHub Actions as the deployment controller.
- On push to `main`, automatically validate the `dev` target only.
- On manual workflow runs, select `dev` or `prod` and choose whether to deploy/run.
- Use GitHub Environments named `dev` and `prod`; configure required reviewers on `prod` in GitHub settings.
- Keep production runs explicit and approval-gated while keeping development validation automatic.

Milestone 2 next work:
- Add richer data quality checks in `src/validate_outputs.py`.
- Add a small failure-mode sample or validation test case.
- Add README instructions for GitHub Environment setup.
- Consider a lightweight cleanup notebook/task for old proof tables if free-tier storage becomes noisy.
