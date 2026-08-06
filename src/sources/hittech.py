from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from src.models import Job
from src.sources.base import JobSource


class HittechSource(JobSource):
    """Scrape relevant vacancies from Hittech location pages."""

    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config.get(
            "name",
            "Hittech Careers",
        )

        self.pages = config.get("pages", [])

        self.keywords = [
            keyword.strip().casefold()
            for keyword in config.get(
                "keywords",
                ["mechanical", "project"],
            )
            if keyword.strip()
        ]

        self.timeout_ms = int(
            config.get("timeout_ms", 45_000)
        )

        if not self.pages:
            raise ValueError(
                "Hittech source requires at least one page."
            )

    def fetch_jobs(self) -> list[Job]:
        jobs_by_id: dict[str, Job] = {}
        loaded_pages = 0
        failed_pages: list[str] = []

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/127 Safari/537.36"
                ),
                viewport={
                    "width": 1440,
                    "height": 1200,
                },
            )

            try:
                for page_config in self.pages:
                    page_id = page_config["id"]
                    page_url = page_config["url"]
                    company = page_config["company"]
                    location = page_config.get(
                        "location",
                        "",
                    )

                    try:
                        page.goto(
                            page_url,
                            wait_until="domcontentloaded",
                            timeout=self.timeout_ms,
                        )

                        page.wait_for_timeout(2500)

                        body_text = (
                            page.locator("body")
                            .inner_text()
                            .casefold()
                        )

                        if (
                            "request is being verified"
                            in body_text
                        ):
                            failed_pages.append(company)
                            continue

                        loaded_pages += 1

                        links = page.locator(
                            "h2 a[href]"
                        )

                        for index in range(links.count()):
                            link = links.nth(index)

                            href = (
                                link.get_attribute("href")
                                or ""
                            ).strip()

                            title = " ".join(
                                link.inner_text().split()
                            )

                            if not href or not title:
                                continue

                            title_lower = title.casefold()

                            if not any(
                                keyword in title_lower
                                for keyword in self.keywords
                            ):
                                continue

                            job_url = urljoin(
                                page_url,
                                href,
                            )

                            job_slug = (
                                urlparse(job_url)
                                .path.rstrip("/")
                                .split("/")[-1]
                            )

                            if not job_slug:
                                continue

                            job_id = (
                                f"{page_id}:"
                                f"{job_slug.casefold()}"
                            )

                            jobs_by_id[job_id] = Job(
                                source_id=self.source_id,
                                source_name=self.source_name,
                                job_id=job_id,
                                title=title,
                                url=job_url,
                                company=company,
                                location=location,
                            )

                    except Exception as error:
                        failed_pages.append(
                            f"{company}: {error}"
                        )

            finally:
                browser.close()

        if loaded_pages == 0:
            failed_text = "; ".join(failed_pages)

            raise RuntimeError(
                "No Hittech location page could be "
                f"scraped successfully. {failed_text}"
            )

        for failed_page in failed_pages:
            print(
                f"Hittech warning: skipped {failed_page}"
            )

        return sorted(
            jobs_by_id.values(),
            key=lambda job: job.title.casefold(),
        )