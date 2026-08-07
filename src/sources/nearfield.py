from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.models import Job
from src.sources.base import JobSource


class NearfieldSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get(
            "company",
            "Nearfield Instruments",
        )
        self.url = config["url"]

        self.keywords = [
            keyword.strip().casefold()
            for keyword in config.get("keywords", [])
            if keyword.strip()
        ]

    def fetch_jobs(self) -> list[Job]:
        response = requests.get(
            self.url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        jobs_by_url: dict[str, Job] = {}

        for link in soup.select('a[href*="/o/"]'):
            href = str(link.get("href", "")).strip()

            title = " ".join(
                link.get_text(" ", strip=True).split()
            )

            if not href or not title:
                continue

            if title.casefold() == "view job":
                continue

            if self.keywords and not any(
                keyword in title.casefold()
                for keyword in self.keywords
            ):
                continue

            job_url = urljoin(self.url, href)
            path = urlparse(job_url).path.rstrip("/")

            if "/o/" not in path.casefold():
                continue

            job_slug = path.split("/")[-1].casefold()

            jobs_by_url[job_url] = Job(
                source_id=self.source_id,
                source_name=self.source_name,
                job_id=job_slug,
                title=title,
                url=job_url,
                company=self.company,
                location="Rotterdam",
            )

        if not jobs_by_url:
            raise RuntimeError(
                "Nearfield Instruments loaded, "
                "but no matching jobs were extracted."
            )

        return sorted(
            jobs_by_url.values(),
            key=lambda job: job.title.casefold(),
        )