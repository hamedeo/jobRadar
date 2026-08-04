from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from src.models import Job
from src.sources.base import JobSource


INNOFLEX_BASE_URL = "https://www.innoflexbv.com"


class InnoflexSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "InnoFlex")
        self.url = config["url"]

        self.required_title_text = config.get(
            "requiredTitleText",
            "Mechanical Engineer",
        ).casefold()

    def fetch_jobs(self) -> list[Job]:
        response = requests.get(
            self.url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; JobRadar/1.0; "
                    "+https://github.com/hamedeo/job-radar)"
                )
            },
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        jobs_by_id: dict[str, Job] = {}

        for link in soup.select('a[href*="/positions/"]'):
            href = link.get("href")

            if not href:
                continue

            card = self._find_job_card(link)

            if card is None:
                continue

            heading = card.select_one("h1, h2, h3, h4, h5, h6")

            if heading is None:
                continue

            title = heading.get_text(" ", strip=True)

            if (
                self.required_title_text
                and self.required_title_text not in title.casefold()
            ):
                continue

            job_url = urljoin(INNOFLEX_BASE_URL, href)
            job_id = urlparse(job_url).path.rstrip("/").split("/")[-1]

            jobs_by_id[job_id] = Job(
                source_id=self.source_id,
                source_name=self.source_name,
                job_id=job_id,
                title=title,
                company=self.company,
                location="Eindhoven",
                url=job_url,
            )

        jobs = list(jobs_by_id.values())

        if not jobs:
            raise RuntimeError(
                "InnoFlex loaded successfully, but no vacancy title "
                "containing 'Mechanical Engineer' was extracted."
            )

        return jobs

    @staticmethod
    def _find_job_card(link: Tag) -> Tag | None:
        current = link.parent

        while isinstance(current, Tag):
            heading = current.select_one("h1, h2, h3, h4, h5, h6")

            if heading is not None:
                return current

            current = current.parent

        return None