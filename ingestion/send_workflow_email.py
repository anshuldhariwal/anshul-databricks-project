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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a workflow notification email through SMTP.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    send_email(args.subject, args.body)
    print("Email notification sent.")


if __name__ == "__main__":
    main()
