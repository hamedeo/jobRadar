import re
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


VDL_BASE_URL = "https://www.werkenbijvdl.nl"


class VdlSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "VDL Groep")
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

                links = page.locator('a[href*="/vacature/"]')
                jobs_by_id: dict[str, Job] = {}

                for index in range(links.count()):
                    link = links.nth(index)
                    href = link.get_attribute("href")

                    if not href:
                        continue

                    job_url = urljoin(VDL_BASE_URL, href)
                    job_id = self._extract_job_id(job_url)

                    if not job_id:
                        continue

                    card_text = self._extract_card_text(link)
                    title = self._extract_title(link, card_text)

                    if not title:
                        continue

                    if (
                        self.required_title_text
                        not in title.casefold()
                    ):
                        continue

                    company = self._extract_company(card_text)
                    location = self._extract_location(card_text)

                    jobs_by_id[job_id] = Job(
                        source_id=self.source_id,
                        source_name=self.source_name,
                        job_id=job_id,
                        title=title,
                        company=company or self.company,
                        location=location,
                        url=job_url,
                    )

                jobs = list(jobs_by_id.values())

                if jobs:
                    return jobs

                page_text = page.locator("body").inner_text().casefold()

                no_result_messages = [
                    "0 resultaten",
                    "geen vacatures gevonden",
                    "geen passende vacature gevonden",
                ]

                if any(
                    message in page_text
                    for message in no_result_messages
                ):
                    return []

                raise RuntimeError(
                    "VDL loaded, but no Mechanical "
                    "vacancies were extracted."
                )

            finally:
                browser.close()

    @staticmethod
    def _extract_job_id(job_url: str) -> str:
        path = urlparse(job_url).path.rstrip("/")

        match = re.search(
            r"/vacature/(\d+)(?:/|$)",
            path,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return ""

    @staticmethod
    def _extract_card_text(link) -> str:
        selectors = [
            "xpath=ancestor::article[1]",
            "xpath=ancestor::li[1]",
            (
                "xpath=ancestor::div["
                ".//a[contains(@href, '/vacature/')]][1]"
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

        try:
            return link.inner_text().strip()
        except Exception:
            return ""

    @staticmethod
    def _extract_title(link, card_text: str) -> str:
        selectors = [
            "xpath=ancestor::article[1]",
            "xpath=ancestor::li[1]",
            (
                "xpath=ancestor::div["
                ".//a[contains(@href, '/vacature/')]][1]"
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

        try:
            link_text = link.inner_text().strip()

            if link_text:
                return link_text.splitlines()[0].strip()

        except Exception:
            pass

        ignored_lines = {
            "",
            "bekijk vacature",
            "lees meer",
            "solliciteer",
            "solliciteer direct",
        }

        for line in card_text.splitlines():
            candidate = line.strip()

            if candidate.casefold() not in ignored_lines:
                return candidate

        return ""

    @staticmethod
    def _extract_location(card_text: str) -> str:
        locations = [
            "Eindhoven",
            "Veldhoven",
            "Helmond",
            "Hapert",
            "Bergeijk",
            "Boxtel",
            "Uden",
            "Oss",
            "Tilburg",
            "Best",
            "Eersel",
            "Valkenswaard",
            "Enschede",
            "Almelo",
            "Nederland",
            "Netherlands",
        ]

        matches = [
            location
            for location in locations
            if location.casefold() in card_text.casefold()
        ]

        return ", ".join(dict.fromkeys(matches))

    @staticmethod
    def _extract_company(card_text: str) -> str:
        lines = [
            line.strip()
            for line in card_text.splitlines()
            if line.strip()
        ]

        for line in lines:
            if line.casefold().startswith("vdl "):
                return line

        return ""