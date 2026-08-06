from urllib.parse import (
    parse_qs,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests
from bs4 import BeautifulSoup, Tag

from src.models import Job
from src.sources.base import JobSource


class DafSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "DAF Trucks")
        self.url = config["url"]
        self.max_pages = int(config.get("max_pages", 10))

        self.keywords = [
            keyword.strip().casefold()
            for keyword in config.get("keywords", [])
            if keyword.strip()
        ]

    def fetch_jobs(self) -> list[Job]:
        jobs_by_id: dict[str, Job] = {}
        all_page_urls: set[str] = set()
        vacancy_links_found = 0

        listing_path = urlparse(self.url).path.rstrip("/")

        for page_number in range(1, self.max_pages + 1):
            page_url = self._page_url(page_number)

            response = requests.get(
                page_url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            current_page_urls: set[str] = set()

            for link in soup.select(
                'h3 a[href*="/working-at-daf/vacancies/"]'
            ):
                href = str(link.get("href", "")).strip()
                title = " ".join(
                    link.get_text(" ", strip=True).split()
                )

                if not href or not title:
                    continue

                job_url = urljoin(page_url, href)
                path = urlparse(job_url).path.rstrip("/")

                if not path.startswith(f"{listing_path}/"):
                    continue

                job_slug = path.split("/")[-1].casefold()

                if not job_slug:
                    continue

                current_page_urls.add(job_url)
                vacancy_links_found += 1

                if self.keywords and not any(
                    keyword in title.casefold()
                    for keyword in self.keywords
                ):
                    continue

                jobs_by_id[job_slug] = Job(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    job_id=job_slug,
                    title=title,
                    url=job_url,
                    company=self.company,
                    location=self._extract_location(link),
                )

            if not current_page_urls:
                break

            if current_page_urls.issubset(all_page_urls):
                break

            all_page_urls.update(current_page_urls)

        if vacancy_links_found == 0:
            raise RuntimeError(
                "DAF loaded, but no vacancy links were extracted."
            )

        return sorted(
            jobs_by_id.values(),
            key=lambda job: job.title.casefold(),
        )

    def _page_url(self, page_number: int) -> str:
        parsed = urlparse(self.url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        query["Page"] = [str(page_number)]

        return urlunparse(
            parsed._replace(
                query=urlencode(query, doseq=True)
            )
        )

    @staticmethod
    def _extract_location(link: Tag) -> str:
        for parent in link.parents:
            if not isinstance(parent, Tag):
                continue

            job_links = parent.select(
                'h3 a[href*="/working-at-daf/vacancies/"]'
            )
            metadata = parent.select("ul li")

            if len(job_links) == 1 and metadata:
                return " ".join(
                    metadata[0]
                    .get_text(" ", strip=True)
                    .split()
                )

        return ""