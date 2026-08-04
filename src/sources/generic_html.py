from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.models import Job
from src.sources.base import JobSource


class GenericHtmlSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", config["name"])
        self.url = config["url"]
        self.selectors = config["selectors"]
        self.required_title_text = config.get(
            "requiredTitleText",
            "",
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

        if "jobLink" in self.selectors:
            return self._fetch_from_job_links(soup)

        return self._fetch_from_job_cards(soup)

    def _fetch_from_job_links(self, soup: BeautifulSoup) -> list[Job]:
        jobs_by_url: dict[str, Job] = {}

        for link in soup.select(self.selectors["jobLink"]):
            href = link.get("href")
            title = link.get_text(" ", strip=True)

            if (
                self.required_title_text
                and self.required_title_text not in title.casefold()
            ):
                continue

            if not href or not title:
                continue

            job_url = urljoin(self.url, href)

            if job_url.rstrip("/") == self.url.rstrip("/"):
                continue

            job_id = self._job_id_from_url(job_url)

            jobs_by_url[job_url] = Job(
                source_id=self.source_id,
                source_name=self.source_name,
                job_id=job_id,
                title=title,
                url=job_url,
                company=self.company,
                location="",
            )

        return list(jobs_by_url.values())

    def _fetch_from_job_cards(self, soup: BeautifulSoup) -> list[Job]:
        job_elements = soup.select(self.selectors["job"])
        jobs: list[Job] = []

        for element in job_elements:
            title_element = element.select_one(self.selectors["title"])
            link_element = element.select_one(self.selectors["link"])

            if title_element is None or link_element is None:
                continue

            title = title_element.get_text(" ", strip=True)
            href = link_element.get("href")

            if not title or not href:
                continue

            job_url = urljoin(self.url, href)

            location = ""
            location_selector = self.selectors.get("location")

            if location_selector:
                location_element = element.select_one(location_selector)

                if location_element:
                    location = location_element.get_text(" ", strip=True)

            job_id_attribute = self.selectors.get("jobIdAttribute")
            job_id = ""

            if job_id_attribute:
                job_id = str(element.get(job_id_attribute, "")).strip()

            if not job_id:
                job_id = self._job_id_from_url(job_url)

            jobs.append(
                Job(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    job_id=job_id,
                    title=title,
                    url=job_url,
                    company=self.company,
                    location=location,
                )
            )

        return jobs

    @staticmethod
    def _job_id_from_url(url: str) -> str:
        path = urlparse(url).path.rstrip("/")
        return path.split("/")[-1]
