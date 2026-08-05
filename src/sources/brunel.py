import re
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


BRUNEL_BASE_URL = "https://www.brunel.net"


class BrunelSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "Brunel")
        self.url = config["url"]

        self.required_title_text = config.get(
            "requiredTitleText",
            "Mechanical",
        ).casefold()

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
                    'a[href*="/en-nl/jobs/"][href*="-tr-"]'
                )

                jobs_by_id: dict[str, Job] = {}

                for index in range(links.count()):
                    link = links.nth(index)
                    href = link.get_attribute("href")

                    if not href:
                        continue

                    job_url = urljoin(BRUNEL_BASE_URL, href)
                    path = urlparse(job_url).path.rstrip("/")

                    id_match = re.search(
                        r"(TR-\d+)$",
                        path,
                        re.IGNORECASE,
                    )

                    if not id_match:
                        continue

                    job_id = id_match.group(1).upper()
                    card_text = self._extract_card_text(link)
                    title = self._extract_title(link, card_text)

                    if not title:
                        continue

                    if (
                        self.required_title_text
                        not in title.casefold()
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

                if not jobs:
                    raise RuntimeError(
                        "Brunel loaded, but no vacancy titles containing "
                        "'Mechanical' were extracted."
                    )

                return jobs

            finally:
                browser.close()

    @staticmethod
    def _extract_card_text(link) -> str:
        selectors = [
            "xpath=ancestor::article[1]",
            "xpath=ancestor::li[1]",
            (
                "xpath=ancestor::div["
                ".//a[contains(@href, '-tr-')]][1]"
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
            text = link.inner_text().strip()

            if text:
                first_line = text.splitlines()[0].strip()

                if first_line:
                    return first_line
        except Exception:
            pass

        for line in card_text.splitlines():
            candidate = line.strip()

            if candidate:
                return candidate

        return ""

    @staticmethod
    def _extract_location(card_text: str) -> str:
        locations = [
            "Utrecht",
            "Eindhoven",
            "Amsterdam",
            "Rotterdam",
            "Veldhoven",
            "Amersfoort",
            "Delft",
            "Enschede",
            "Arnhem",
            "Hengelo",
            "Netherlands",
            "Nederland",
        ]

        matches = [
            location
            for location in locations
            if location.casefold() in card_text.casefold()
        ]

        return ", ".join(matches)