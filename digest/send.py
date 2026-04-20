"""Send a multipart email via Gmail SMTP + App Password."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from shared.config import env


def send_email(subject: str, html: str, text: str, to: str | None = None) -> None:
    gmail_user = env("GMAIL_USER", required=True)
    gmail_password = env("GMAIL_APP_PASSWORD", required=True)
    recipients_raw = to or env("GMAIL_TO", required=True)
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = ", ".join(recipients)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
