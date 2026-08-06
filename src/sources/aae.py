import re
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


class AaeSource(JobSource):
    """Scrape mechanical-engineering vacancies from AAE."""

    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config.get("name", "AAE Careers")
        self.url = config.get(
            "url",
            "https://join.aae.tech/option/teampaginas/engineering-r-d",
        )
        self.keywords = [
            keyword.casefold()
            for keyword in config.get("keywords", ["mechanical"])
        ]
        self.timeout_ms = int(config.get("timeout_ms", 45_000))

    def fetch_jobs(self) -> list[Job]:
        jobs_by_id: dict[str, Job] = {}

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)

                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/126 Safari/537.36"
                    )
                )

                page.goto(
                    self.url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )

                page.wait_for_selector(
                    'a[href*="/vacature/"]',
                    timeout=self.timeout_ms,
                )

                links = page.locator('a[href*="/vacature/"]')

                for index in range(links.count()):
                    link = links.nth(index)

                    href = link.get_attribute("href") or ""
                    match = re.search(r"/vacature/(\d+)(?:/|$)", href)

                    if not match:
                        continue

                    title = " ".join(link.inner_text().split())

                    if not title:
                        continue

                    title_lower = title.casefold()

                    if not any(
                        keyword in title_lower
                        for keyword in self.keywords
                    ):
                        continue

                    job_id = match.group(1)
                    job_url = urljoin(self.url, href)

                    jobs_by_id[job_id] = Job(
                        source_id=self.source_id,
                        source_name=self.source_name,
                        job_id=job_id,
                        title=title,
                        url=job_url,
                        company="AAE",
                        location="Helmond",
                    )

                browser.close()

        except PlaywrightTimeoutError as error:
            raise RuntimeError(
                "AAE loaded, but its vacancy links did not appear."
            ) from error

        return sorted(
            jobs_by_id.values(),
            key=lambda job: job.title.casefold(),
        )