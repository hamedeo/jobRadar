import re
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


DEMCON_BASE_URL = "https://careersatdemcon.com"


class DemconSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "DEMCON")
        self.url = config["url"]

        self.required_expertises = {
            value.casefold()
            for value in config.get(
                "requiredExpertises",
                ["Engineering"],
            )
        }

        self.required_functions = {
            value.casefold()
            for value in config.get(
                "requiredFunctions",
                ["Mechanical engineer"],
            )
        }

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

                page.wait_for_timeout(7000)

                links = page.locator('a[href*="/vacancy/"]')
                jobs_by_id: dict[str, Job] = {}

                for index in range(links.count()):
                    link = links.nth(index)
                    href = link.get_attribute("href")

                    if not href:
                        continue

                    job_url = urljoin(DEMCON_BASE_URL, href)
                    parsed_url = urlparse(job_url)

                    match = re.search(
                        r"/vacancy/(\d+)/([^/?#]+)",
                        parsed_url.path,
                        re.IGNORECASE,
                    )

                    if not match:
                        continue

                    job_id = match.group(1)
                    card_text = self._extract_card_text(link)

                    if not card_text:
                        continue

                    normalized_text = card_text.casefold()
                    title = self._extract_title(link, card_text)

                    if not title:
                        continue

                    normalized_title = title.casefold()

                    if not any(
                        required_function in normalized_title
                        for required_function in self.required_functions
                    ):
                        continue

                    if not any(
                        expertise in normalized_text
                        for expertise in self.required_expertises
                    ):
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
                    "there are currently no related vacancies available",
                    "no related vacancies available",
                ]

                if any(
                    message in page_text
                    for message in no_results_messages
                ):
                    return []

                raise RuntimeError(
                    "DEMCON loaded, but no matching vacancy cards "
                    "were extracted. The page structure may have changed."
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
                ".//a[contains(@href, '/vacancy/')]][1]"
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
        try:
            container = link.locator(
                "xpath=ancestor::*[self::article or self::li or self::div][1]"
            )

            heading = container.locator("h1, h2, h3, h4").first

            if heading.count() > 0:
                title = heading.inner_text().strip()

                if title:
                    return title

        except Exception:
            pass

        ignored_lines = {
            "view vacancy",
            "bekijk vacature",
            "apply",
        }

        for line in card_text.splitlines():
            candidate = line.strip()

            if (
                candidate
                and candidate.casefold() not in ignored_lines
            ):
                return candidate

        return ""

    @staticmethod
    def _extract_location(card_text: str) -> str:
        locations = [
            "Enschede",
            "Eindhoven",
            "Delft",
            "Groningen",
            "Scheveningen",
        ]

        matches = [
            location
            for location in locations
            if location.casefold() in card_text.casefold()
        ]

        return ", ".join(matches)
