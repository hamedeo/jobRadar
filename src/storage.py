import json
from pathlib import Path

from src.models import Job


SEEN_JOBS_FILE = Path("data/seen_jobs.json")


def load_seen_job_ids() -> set[str]:
    if not SEEN_JOBS_FILE.exists():
        return set()

    try:
        content = SEEN_JOBS_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
    except (json.JSONDecodeError, OSError):
        return set()

    if not isinstance(data, list):
        return set()

    return set(str(item) for item in data)


def save_seen_job_ids(job_ids: set[str]) -> None:
    SEEN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

    SEEN_JOBS_FILE.write_text(
        json.dumps(sorted(job_ids), indent=2),
        encoding="utf-8",
    )


def find_new_jobs(
    current_jobs: list[Job],
    seen_job_ids: set[str],
) -> list[Job]:
    return [
        job
        for job in current_jobs
        if job.unique_id() not in seen_job_ids
    ]
