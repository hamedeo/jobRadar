import json
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
from src.sources.asml import AsmlSource
from src.sources.tmc import TmcSource
from src.sources.demcon import DemconSource
from src.sources.innoflex import InnoflexSource
from src.sources.brunel import BrunelSource
from src.sources.asm import AsmSource

SOURCES_FILE = Path("config/sources.json")


def load_source_configs() -> list[dict]:
    if not SOURCES_FILE.exists():
        raise FileNotFoundError(
            f"Source configuration was not found: {SOURCES_FILE}"
        )

    data = json.loads(
        SOURCES_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError(
            "config/sources.json must contain a JSON list."
        )

    return data


def create_source(config: dict):
    source_type = config.get("type")

    if source_type == "generic_html":
        return GenericHtmlSource(config)

    if source_type == "asml":
        return AsmlSource(config)

    if source_type == "tmc":
    	return TmcSource(config)

    if source_type == "demcon":
    	return DemconSource(config)
    
    if source_type == "innoflex":
        return InnoflexSource(config)

    if source_type == "brunel":
        return BrunelSource(config)

    if source_type == "asm":
        return AsmSource(config)

    raise ValueError(
        f"Unsupported source type: {source_type!r} "
        f"for source "
        f"{config.get('name', config.get('id'))!r}"
    )


def collect_jobs() -> tuple[list[Job], int]:
    jobs: list[Job] = []
    failed_sources = 0

    for config in load_source_configs():
        if not config.get("enabled", True):
            continue

        source_name = config.get(
            "name",
            config.get("id", "Unknown source"),
        )

        try:
            source = create_source(config)
            source_jobs = source.fetch_jobs()
            jobs.extend(source_jobs)

            print(
                f"{source_name}: found "
                f"{len(source_jobs)} jobs"
            )

        except Exception as error:
            failed_sources += 1
            print(f"{source_name}: failed: {error}")

    return jobs, failed_sources


def main() -> None:
    load_dotenv()

    current_jobs, failed_sources = collect_jobs()

    if not current_jobs:
        if failed_sources:
            raise RuntimeError(
                "No jobs were collected and at least one "
                "source failed."
            )

        print(
            "No matching jobs are currently available. "
            "The monitored sources were checked successfully."
        )
        return

    seen_job_ids = load_seen_job_ids()
    first_run = len(seen_job_ids) == 0

    new_jobs = find_new_jobs(
        current_jobs,
        seen_job_ids,
    )

    print(f"Current jobs: {len(current_jobs)}")
    print(f"New jobs: {len(new_jobs)}")

    current_job_ids = {
        job.unique_id()
        for job in current_jobs
    }

    if first_run:
        print(
            "First run detected. Existing jobs will be "
            "saved without sending notifications."
        )

        save_seen_job_ids(current_job_ids)
        return

    updated_seen_ids = set(seen_job_ids)

    for job in new_jobs:
        send_telegram_job(job)
        updated_seen_ids.add(job.unique_id())

        save_seen_job_ids(updated_seen_ids)

        print(f"Notification sent: {job.title}")

    updated_seen_ids.update(current_job_ids)
    save_seen_job_ids(updated_seen_ids)


if __name__ == "__main__":
    main()
