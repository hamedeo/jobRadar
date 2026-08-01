from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


TMC_BASE_URL = "https://www.themembercompany.com"


class TmcSource(JobSource):
    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config["name"]
        self.company = config.get("company", "The Member Company")
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

                # Give the vacancy list time to render.
                page.wait_for_timeout(7000)

                # Match both relative and absolute vacancy URLs.
                links = page.locator('a[href*="/careers/"]')

                jobs_by_url: dict[str, Job] = {}

                for index in range(links.count()):
                    link = links.nth(index)

                    href = link.get_attribute("href")

                    if not href:
                        continue

                    job_url = urljoin(TMC_BASE_URL, href)
                    parsed_url = urlparse(job_url)

                    path_parts = [
                        part
                        for part in parsed_url.path.split("/")
                        if part
                    ]

                    # A vacancy URL should have this structure:
                    # /careers/vacancy-slug
                    if len(path_parts) != 2:
                        continue

                    if path_parts[0].lower() != "careers":
                        continue

                    job_id = path_parts[1]

                    if job_id.lower() in {
                        "graduate-programs",
                        "for-expats",
                        "corporate-vacancies",
                        "all-vacancies",
                    }:
                        continue

                    title = self._extract_title(link)

                    if not title:
                        continue

                    card_text = self._extract_card_text(link)

                    # Apply the requested filters ourselves as a safeguard.
                    normalized_text = card_text.lower()

                    if "netherlands" not in normalized_text:
                        continue

                    if "mechanical" not in normalized_text:
                        continue

                    accepted_experience = (
                        "0 - 2 years" in normalized_text
                        or "2 - 5 years" in normalized_text
                        or "2–5 years" in normalized_text
                    )

                    if not accepted_experience:
                        continue

                    jobs_by_url[job_url] = Job(
                        source_id=self.source_id,
                        source_name=self.source_name,
                        job_id=job_id,
                        title=title,
                        company=self.company,
                        location=self._extract_location(card_text),
                        url=job_url,
                    )

                jobs = list(jobs_by_url.values())

                if not jobs:
                    raise RuntimeError(
                        "TMC loaded, but no vacancies matching "
                        "Netherlands, Mechanical, and the selected "
                        "experience levels were extracted."
                    )

                return jobs

            finally:
                browser.close()

    @staticmethod
    def _extract_title(link) -> str:
        ignored_titles = {
            "",
            "apply now",
            "view vacancy",
            "read more",
        }

        direct_text = link.inner_text().strip()

        if direct_text.lower() not in ignored_titles:
            return direct_text

        try:
            container = link.locator(
                "xpath=ancestor::*[self::article or self::li or self::div][1]"
            )

            heading = container.locator("h1, h2, h3, h4").first

            if heading.count() > 0:
                return heading.inner_text().strip()

        except Exception:
            pass

        return ""

    @staticmethod
    def _extract_card_text(link) -> str:
        try:
            container = link.locator(
                "xpath=ancestor::*[self::article or self::li][1]"
            )

            if container.count() > 0:
                return container.inner_text().strip()

            # Fallback for cards constructed from nested div elements.
            container = link.locator(
                "xpath=ancestor::div[count(.//a[@href]) <= 4][1]"
            )

            if container.count() > 0:
                return container.inner_text().strip()

        except Exception:
            pass

        return link.inner_text().strip()

    @staticmethod
    def _extract_location(card_text: str) -> str:
        known_locations = [
            "Eindhoven",
            "Veldhoven",
            "Arnhem",
            "Hengelo",
            "Delft",
            "Amsterdam",
            "Rotterdam",
            "Utrecht",
            "Almere",
            "Deventer",
            "Netherlands",
        ]

        matches = [
            location
            for location in known_locations
            if location.lower() in card_text.lower()
        ]

        return ", ".join(matches)
