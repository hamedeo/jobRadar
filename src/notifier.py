import os

import requests

from src.models import Job


TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramNotificationError(RuntimeError):
    pass


def send_telegram_job(job: Job) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token:
        raise TelegramNotificationError(
            "TELEGRAM_BOT_TOKEN is not configured."
        )

    if not chat_id:
        raise TelegramNotificationError(
            "TELEGRAM_CHAT_ID is not configured."
        )

    message_lines = [
        "🆕 <b>New job posted</b>",
        "",
        f"<b>{escape_html(job.title)}</b>",
        f"Company: {escape_html(job.company)}",
    ]

    if job.location:
        message_lines.append(
            f"Location: {escape_html(job.location)}"
        )

    message_lines.append(
        f"Source: {escape_html(job.source_name)}"
    )

    response = requests.post(
        f"{TELEGRAM_API_URL}/bot{bot_token}/sendMessage",
        timeout=30,
        json={
            "chat_id": chat_id,
            "text": "\n".join(message_lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "Open vacancy",
                            "url": job.url,
                        }
                    ]
                ]
            },
        },
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise TelegramNotificationError(
            f"Telegram returned HTTP {response.status_code}: "
            f"{response.text}"
        ) from error

    payload = response.json()

    if not payload.get("ok"):
        raise TelegramNotificationError(
            f"Telegram rejected the message: {payload}"
        )


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
