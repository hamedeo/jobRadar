from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from src.models import Job
from src.sources.base import JobSource


class NobleoSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get(
            "company",
            "Nobleo Technology",
        )
        self.url = config["url"]

        self.keywords = [
            keyword.casefold()
            for keyword in config.get(
                "keywords",
                ["mechanical", "project"],
            )
            if keyword.strip()
        ]

    def fetch_jobs(self) -> list[Job]:
        response = requests.get(
            self.url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        jobs_by_url: dict[str, Job] = {}
        vacancy_links_found = 0

        for link in soup.select(
            'a[href*="/careers/"]'
        ):
            href = str(link.get("href", "")).strip()

            if not href:
                continue

            heading = self._find_heading(link)

            if heading is None:
                continue

            title = " ".join(
                heading.get_text(" ", strip=True).split()
            )

            if not title:
                continue

            job_url = urljoin(self.url, href)
            parsed_url = urlparse(job_url)
            path = parsed_url.path.rstrip("/")

            # Ignore the general careers page.
            if path == "/careers":
                continue

            vacancy_links_found += 1

            title_lower = title.casefold()

            if self.keywords and not any(
                keyword in title_lower
                for keyword in self.keywords
            ):
                continue

            job_id = path.split("/")[-1]

            if not job_id:
                continue

            jobs_by_url[job_url] = Job(
                source_id=self.source_id,
                source_name=self.source_name,
                job_id=job_id,
                title=title,
                url=job_url,
                company=self.company,
                location="Eindhoven",
            )

        if vacancy_links_found == 0:
            raise RuntimeError(
                "Nobleo loaded successfully, but no vacancy "
                "links were extracted. The website structure "
                "may have changed."
            )

        return sorted(
            jobs_by_url.values(),
            key=lambda job: job.title.casefold(),
        )

    @staticmethod
    def _find_heading(link: Tag) -> Tag | None:
        # Handles:
        # <h3><a href="...">Job title</a></h3>
        heading = link.find_parent(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        )

        if heading is not None:
            return heading

        # Also handles:
        # <a href="..."><h3>Job title</h3></a>
        return link.find(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        )