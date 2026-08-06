from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from src.models import Job
from src.sources.base import JobSource


class AxcesSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "Axces")
        self.url = config["url"]

        self.keywords = [
            keyword.strip().casefold()
            for keyword in config.get("keywords", [])
            if keyword.strip()
        ]

        self.locations = config.get(
            "locations",
            ["Netherlands", "Poland", "Singapore"],
        )

    def fetch_jobs(self) -> list[Job]:
        response = requests.get(
            self.url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        jobs_by_url: dict[str, Job] = {}

        for link in soup.select('a[href*="/careers/"]'):
            href = str(link.get("href", "")).strip()

            if not href:
                continue

            job_url = urljoin(self.url, href)
            path = urlparse(job_url).path.rstrip("/")

            if (
                not path.casefold().startswith("/careers/")
                or path.casefold() == "/careers"
            ):
                continue

            card, heading = self._find_card(link)

            if card is None or heading is None:
                continue

            title = " ".join(
                heading.get_text(" ", strip=True).split()
            )

            if not title:
                continue

            title_lower = title.casefold()

            if self.keywords and not any(
                keyword in title_lower
                for keyword in self.keywords
            ):
                continue

            job_slug = path.split("/")[-1].casefold()
            card_text = card.get_text(" ", strip=True)

            location = next(
                (
                    location
                    for location in self.locations
                    if location.casefold() in card_text.casefold()
                ),
                "",
            )

            jobs_by_url[job_url] = Job(
                source_id=self.source_id,
                source_name=self.source_name,
                job_id=job_slug,
                title=title,
                url=job_url,
                company=self.company,
                location=location,
            )

        if not jobs_by_url:
            raise RuntimeError(
                "Axces loaded, but no matching vacancies were extracted."
            )

        return sorted(
            jobs_by_url.values(),
            key=lambda job: job.title.casefold(),
        )

    @staticmethod
    def _find_card(link: Tag) -> tuple[Tag | None, Tag | None]:
        for parent in link.parents:
            if not isinstance(parent, Tag):
                continue

            heading = parent.find(["h2", "h3", "h4"])

            if heading is None:
                continue

            job_paths = {
                urlparse(str(item.get("href", "")))
                .path.rstrip("/")
                .casefold()
                for item in parent.select(
                    'a[href*="/careers/"]'
                )
                if "/careers/" in str(item.get("href", ""))
            }

            if len(job_paths) == 1:
                return parent, heading

        return None, None