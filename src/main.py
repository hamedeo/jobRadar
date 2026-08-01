import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.models import Job
from src.notifier import send_telegram_job
from src.sources.generic_html import GenericHtmlSource
from src.storage import (
    find_new_jobs,
    load_seen_job_ids,
    save_seen_job_ids,
)


SOURCES_FILE = Path("config/sources.json")


def load_source_configs() -> list[dict]:
    if not SOURCES_FILE.exists():
        raise FileNotFoundError(
            f"Source configuration was not found: {SOURCES_FILE}"
        )

    data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("config/sources.json must contain a JSON list.")

    return data


def create_source(config: dict):
    source_type = config.get("type")

    if source_type == "generic_html":
        return GenericHtmlSource(config)

    raise ValueError(
        f"Unsupported source type: {source_type!r} "
        f"for source {config.get('name', config.get('id'))!r}"
    )


def collect_jobs() -> list[Job]:
    jobs: list[Job] = []

    for config in load_source_configs():
        if not config.get("enabled", True):
            continue

        source_name = config.get("name", config.get("id", "Unknown source"))

        try:
            source = create_source(config)
            source_jobs = source.fetch_jobs()
            jobs.extend(source_jobs)

            print(f"{source_name}: found {len(source_jobs)} jobs")

        except Exception as error:
            print(f"{source_name}: failed: {error}")

    return jobs


def main() -> None:
    load_dotenv()

    current_jobs = collect_jobs()

    if not current_jobs:
        print("No jobs were collected.")
        return

    seen_job_ids = load_seen_job_ids()
    first_run = len(seen_job_ids) == 0

    new_jobs = find_new_jobs(current_jobs, seen_job_ids)

    print(f"Current jobs: {len(current_jobs)}")
    print(f"New jobs: {len(new_jobs)}")

    if first_run:
        print(
            "First run detected. Existing jobs will be saved "
            "without sending notifications."
        )
    else:
        for job in new_jobs:
            send_telegram_job(job)
            print(f"Notification sent: {job.title}")

    updated_seen_ids = seen_job_ids | {
        job.unique_id()
        for job in current_jobs
    }

    save_seen_job_ids(updated_seen_ids)


if __name__ == "__main__":
    main()
