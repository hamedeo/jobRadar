from urllib.parse import urljoin

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

    def fetch_jobs(self) -> list[Job]:
        response = requests.get(
            self.url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; JobRadar/1.0; "
                    "+https://github.com/hamedeo/job-radar)"
                )
            },
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
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
                job_id = str(
                    element.get(job_id_attribute, "")
                ).strip()

            if not job_id:
                job_id = job_url

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
