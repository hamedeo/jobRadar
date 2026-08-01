import os

import requests

from src.models import Job


TELEGRAM_API_URL = "https://api.telegram.org"


def send_telegram_job(job: Job) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured."
        )

    message_lines = [
        "🆕 New job posted",
        "",
        f"<b>{escape_html(job.title)}</b>",
        f"Company: {escape_html(job.company)}",
    ]

    if job.location:
        message_lines.append(f"Location: {escape_html(job.location)}")

    message_lines.extend(
        [
            f"Source: {escape_html(job.source_name)}",
            "",
            f'<a href="{escape_html(job.url)}">Open vacancy</a>',
        ]
    )

    response = requests.post(
        f"{TELEGRAM_API_URL}/bot{bot_token}/sendMessage",
        timeout=30,
        json={
            "chat_id": chat_id,
            "text": "\n".join(message_lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )

    response.raise_for_status()


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
