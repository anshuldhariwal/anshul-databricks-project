from __future__ import annotations

import argparse
from email.message import EmailMessage
import os
import smtplib
import ssl


class EmailNotificationError(RuntimeError):
    pass


def env(name: str, *, required: bool = True) -> str:
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise EmailNotificationError(f"{name} is required.")
    return value


def send_email(subject: str, body: str) -> None:
    smtp_host = env("SMTP_HOST")
    smtp_port = int(env("SMTP_PORT"))
    smtp_username = env("SMTP_USERNAME")
    smtp_password = env("SMTP_PASSWORD")
    alert_to = env("ALERT_EMAIL_TO")
    alert_from = env("ALERT_EMAIL_FROM", required=False) or smtp_username

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = alert_from
    message["To"] = alert_to
    message.set_content(body)

    context = ssl.create_default_context()
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.send_message(message)


def optional_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def run_kind(bundle_job: str, automation_test: str) -> str:
    if automation_test == "true":
        return "Automation test"
    if bundle_job == "cleanup_proof_tables":
        return "Cleanup"
    if bundle_job == "market_data_job":
        return "Market refresh"
    if bundle_job == "proof_job":
        return "Bundle proof"
    return bundle_job or "Workflow run"


def run_url() -> str:
    server_url = optional_env("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = optional_env("GITHUB_REPOSITORY")
    run_id = optional_env("GITHUB_RUN_ID")
    if not repository or not run_id:
        return ""
    return f"{server_url}/{repository}/actions/runs/{run_id}"


def build_workflow_email(
    *,
    status: str,
    bundle_result: str = "",
    pages_result: str = "",
) -> tuple[str, str]:
    target = optional_env("BUNDLE_TARGET", "unknown")
    bundle_job = optional_env("BUNDLE_JOB", "unknown")
    automation_test = optional_env("AUTOMATION_TEST", "false")
    event_name = optional_env("GITHUB_EVENT_NAME", "unknown")
    event_schedule = optional_env("WORKFLOW_EVENT_SCHEDULE")
    workflow = optional_env("GITHUB_WORKFLOW", "unknown")
    repository = optional_env("GITHUB_REPOSITORY", "unknown")
    run_id = optional_env("GITHUB_RUN_ID", "unknown")
    run_attempt = optional_env("GITHUB_RUN_ATTEMPT", "unknown")
    kind = run_kind(bundle_job, automation_test)

    if status == "started":
        subject = f"{kind} started: {target}"
        intro = f"{kind} started for the {target} Databricks target."
    elif status == "completed":
        result = bundle_result or "unknown"
        subject = f"{kind} completed: {result}"
        intro = f"{kind} completed for the {target} Databricks target."
    else:
        raise EmailNotificationError(f"Unsupported status: {status}")

    detail_lines = [
        intro,
        "",
        f"Run type: {kind}",
        f"Bundle target: {target}",
        f"Bundle job: {bundle_job}",
        f"Trigger: {event_name}",
    ]
    if event_schedule:
        detail_lines.append(f"Cron schedule: {event_schedule}")
    if status == "completed":
        detail_lines.extend(
            [
                f"Bundle workflow result: {bundle_result or 'unknown'}",
                f"GitHub Pages result: {pages_result or 'skipped/not applicable'}",
            ]
        )
    detail_lines.extend(
        [
            f"Repository: {repository}",
            f"Workflow: {workflow}",
            f"Run ID: {run_id}",
            f"Run attempt: {run_attempt}",
        ]
    )
    url = run_url()
    if url:
        detail_lines.extend(["", f"Run URL: {url}"])

    return subject, "\n".join(detail_lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a workflow notification email through SMTP.")
    parser.add_argument("--subject")
    parser.add_argument("--body")
    parser.add_argument("--status", choices=("started", "completed"))
    parser.add_argument("--bundle-result", default="")
    parser.add_argument("--pages-result", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.status:
        subject, body = build_workflow_email(
            status=args.status,
            bundle_result=args.bundle_result,
            pages_result=args.pages_result,
        )
    else:
        if not args.subject or not args.body:
            raise EmailNotificationError("Set --status or both --subject and --body.")
        subject = args.subject
        body = args.body

    send_email(subject, body)
    print("Email notification sent.")


if __name__ == "__main__":
    main()
