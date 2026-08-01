import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


ASML_BASE_URL = "https://www.asml.com"


class AsmlSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "ASML")
        self.url = config["url"]

    def fetch_jobs(self) -> list[Job]:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/127 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 1000},
            )

            try:
                page.goto(
                    self.url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                page.wait_for_timeout(5000)

                links = page.locator(
                    'a[href*="/careers/find-your-job/"]'
                )

                jobs_by_id: dict[str, Job] = {}

                for index in range(links.count()):
                    link = links.nth(index)

                    href = link.get_attribute("href")
                    title = link.inner_text().strip()

                    if not href or not title:
                        continue

                    job_url = urljoin(ASML_BASE_URL, href)

                    job_id_match = re.search(
                        r"J-?\d{8}",
                        job_url,
                        re.IGNORECASE,
                    )

                    if not job_id_match:
                        continue

                    job_id = job_id_match.group(0).upper()

                    if not job_id.startswith("J-"):
                        job_id = f"J-{job_id[1:]}"

                    location = self._extract_location(link)

                    jobs_by_id[job_id] = Job(
                        source_id=self.source_id,
                        source_name=self.source_name,
                        job_id=job_id,
                        title=title,
                        company=self.company,
                        location=location,
                        url=job_url,
                    )

                jobs = list(jobs_by_id.values())

                if jobs:
                    return jobs

                page_text = page.locator("body").inner_text().lower()

                no_results_messages = [
                    "0 active results",
                    "sorry, we were not able to find a match",
                ]

                if any(
                    message in page_text
                    for message in no_results_messages
                ):
                    return []

                raise RuntimeError(
                    "ASML returned no vacancy links and did not display "
                    "a recognized zero-results message."
                )

            finally:
                browser.close()

    @staticmethod
    def _extract_location(link) -> str:
        try:
            container = link.locator(
                "xpath=ancestor::*[self::article or self::li][1]"
            )

            if container.count() == 0:
                return ""

            text = container.inner_text()

            locations = [
                "Veldhoven",
                "Eindhoven",
                "Delft",
                "Netherlands",
            ]

            matches = [
                location
                for location in locations
                if location.lower() in text.lower()
            ]

            return ", ".join(matches)

        except Exception:
            return ""
