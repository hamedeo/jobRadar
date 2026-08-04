import re
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


HASKONING_BASE_URL = "https://www.haskoning.com"


class HaskoningSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "Haskoning")
        self.url = config["url"]

    def fetch_jobs(self) -> list[Job]:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/127 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 1200},
            )

            try:
                page.goto(
                    self.url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                page.wait_for_timeout(8000)

                links = page.locator(
                    'a[href*="/en/careers/vacancies/"]'
                )

                jobs_by_id: dict[str, Job] = {}

                for index in range(links.count()):
                    link = links.nth(index)
                    href = link.get_attribute("href")

                    if not href:
                        continue

                    job_url = urljoin(HASKONING_BASE_URL, href)
                    parsed_url = urlparse(job_url)
                    path = parsed_url.path.rstrip("/")

                    id_match = re.search(
                        r"-(\d+)$",
                        path,
                    )

                    if not id_match:
                        continue

                    job_id = id_match.group(1)
                    card_text = self._extract_card_text(link)
                    title = self._extract_title(link, card_text)

                    if not title:
                        continue

                    jobs_by_id[job_id] = Job(
                        source_id=self.source_id,
                        source_name=self.source_name,
                        job_id=job_id,
                        title=title,
                        company=self.company,
                        location=self._extract_location(card_text),
                        url=job_url,
                    )

                jobs = list(jobs_by_id.values())

                if jobs:
                    return jobs

                page_text = page.locator("body").inner_text().casefold()

                no_results_messages = [
                    "show 0 vacancies",
                    "no vacancies found",
                    "0 vacancies",
                ]

                if any(
                    message in page_text
                    for message in no_results_messages
                ):
                    return []

                raise RuntimeError(
                    "Haskoning loaded, but no vacancy links or "
                    "recognized zero-results message were found."
                )

            finally:
                browser.close()

    @staticmethod
    def _extract_card_text(link) -> str:
        selectors = [
            "xpath=ancestor::article[1]",
            "xpath=ancestor::li[1]",
            (
                "xpath=ancestor::div["
                ".//a[contains(@href, '/careers/vacancies/')]][1]"
            ),
        ]

        for selector in selectors:
            try:
                container = link.locator(selector)

                if container.count() > 0:
                    text = container.inner_text().strip()

                    if text:
                        return text

            except Exception:
                continue

        return link.inner_text().strip()

    @staticmethod
    def _extract_title(link, card_text: str) -> str:
        selectors = [
            "xpath=ancestor::article[1]",
            "xpath=ancestor::li[1]",
            (
                "xpath=ancestor::div["
                ".//a[contains(@href, '/careers/vacancies/')]][1]"
            ),
        ]

        for selector in selectors:
            try:
                container = link.locator(selector)
                heading = container.locator(
                    "h1, h2, h3, h4, h5"
                ).first

                if heading.count() > 0:
                    title = heading.inner_text().strip()

                    if title:
                        return title

            except Exception:
                continue

        text = link.inner_text().strip()

        if text:
            return text.splitlines()[0].strip()

        for line in card_text.splitlines():
            candidate = line.strip()

            if candidate:
                return candidate

        return ""

    @staticmethod
    def _extract_location(card_text: str) -> str:
        locations = [
            "Netherlands",
            "Germany",
            "United Kingdom",
            "Amsterdam",
            "Rotterdam",
            "Eindhoven",
            "Nijmegen",
            "Amersfoort",
            "The Hague",
            "Delft",
            "Utrecht",
            "Birmingham",
            "London",
            "Frankfurt",
            "Berlin",
            "Hamburg",
        ]

        matches = [
            location
            for location in locations
            if location.casefold() in card_text.casefold()
        ]

        return ", ".join(matches)