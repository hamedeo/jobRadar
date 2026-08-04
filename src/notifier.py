import os
from typing import Any

import requests

from src.models import Job


TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramNotificationError(RuntimeError):
    """Raised when a Telegram notification cannot be delivered."""


def escape_html(value: str | None) -> str:
    """Escape text before inserting it into a Telegram HTML message."""
    if value is None:
        return ""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def get_telegram_destinations() -> list[dict[str, Any]]:
    """
    Build the list of Telegram destinations.

    Supported destinations:
    1. A private Telegram chat.
    2. A topic inside a Telegram forum group.
    """
    private_chat_id = os.environ.get("TELEGRAM_PRIVATE_CHAT_ID", "").strip()
    group_chat_id = os.environ.get("TELEGRAM_GROUP_CHAT_ID", "").strip()
    group_topic_id = os.environ.get("TELEGRAM_GROUP_TOPIC_ID", "").strip()

    destinations: list[dict[str, Any]] = []

    if private_chat_id:
        destinations.append(
            {
                "name": "private chat",
                "chat_id": private_chat_id,
            }
        )

    if group_chat_id:
        group_destination: dict[str, Any] = {
            "name": "group topic",
            "chat_id": group_chat_id,
        }

        if group_topic_id:
            try:
                group_destination["message_thread_id"] = int(group_topic_id)
            except ValueError as error:
                raise TelegramNotificationError(
                    "TELEGRAM_GROUP_TOPIC_ID must be a number."
                ) from error

        destinations.append(group_destination)

    if not destinations:
        raise TelegramNotificationError(
            "No Telegram destinations are configured. Set "
            "TELEGRAM_PRIVATE_CHAT_ID and/or TELEGRAM_GROUP_CHAT_ID."
        )

    return destinations


def build_message(job: Job) -> str:
    """Create the Telegram message for a job vacancy."""
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

    if job.source_name:
        message_lines.append(
            f"Source: {escape_html(job.source_name)}"
        )

    return "\n".join(message_lines)


def send_telegram_job(job: Job) -> None:
    """Send one job notification to every configured Telegram destination."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

    if not bot_token:
        raise TelegramNotificationError(
            "TELEGRAM_BOT_TOKEN is not configured."
        )

    destinations = get_telegram_destinations()
    message = build_message(job)

    failures: list[str] = []

    for destination in destinations:
        payload: dict[str, Any] = {
            "chat_id": destination["chat_id"],
            "text": message,
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
        }

        if "message_thread_id" in destination:
            payload["message_thread_id"] = destination[
                "message_thread_id"
            ]

        try:
            response = requests.post(
                f"{TELEGRAM_API_URL}/bot{bot_token}/sendMessage",
                json=payload,
                timeout=30,
            )

            response_data = response.json()

            if not response.ok or not response_data.get("ok"):
                error_description = response_data.get(
                    "description",
                    response.text,
                )

                raise TelegramNotificationError(
                    f"{response.status_code}: {error_description}"
                )

            print(
                "Telegram notification sent to "
                f"{destination['name']} "
                f"({destination['chat_id']})."
            )

        except requests.RequestException as error:
            failures.append(
                f"{destination['name']} "
                f"({destination['chat_id']}): {error}"
            )

        except ValueError:
            failures.append(
                f"{destination['name']} "
                f"({destination['chat_id']}): "
                f"Telegram returned invalid JSON: {response.text}"
            )

        except TelegramNotificationError as error:
            failures.append(
                f"{destination['name']} "
                f"({destination['chat_id']}): {error}"
            )

    if failures:
        raise TelegramNotificationError(
            "Some Telegram destinations failed:\n- "
            + "\n- ".join(failures)
        )