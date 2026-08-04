import os

import requests

from src.models import Job


TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramNotificationError(RuntimeError):
    pass


def send_telegram_job(job: Job) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids_value = os.environ.get("TELEGRAM_CHAT_IDs", "")

    if not bot_token:
        raise TelegramNotificationError(
            "TELEGRAM_BOT_TOKEN is not configured."
        )

    chat_ids = [
        value.strip()
        for value in chat_ids_value.split(",")
        if value.strip()
    ]

    if not chat_ids:
        raise TelegramNotificationError(
            "TELEGRAM_CHAT_IDS is not configured."
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

    failures: list[str] = []

    for chat_id in chat_ids:
        try:
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

            response.raise_for_status()
            payload = response.json()

            if not payload.get("ok"):
                raise TelegramNotificationError(
                    f"Telegram rejected the message: {payload}"
                )

        except Exception as error:
            failures.append(f"{chat_id}: {error}")

    if failures:
        raise TelegramNotificationError(
            "Some Telegram destinations failed: "
            + " | ".join(failures)
        )


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )