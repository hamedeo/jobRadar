import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from src.models import Job
from src.sources.base import JobSource


class NeitracoSource(JobSource):
    """Scrape relevant vacancies from Neitraco Groep."""

    def __init__(self, config: dict):
        self.source_id = config["id"]
        self.source_name = config.get(
            "name",
            "Neitraco Groep Careers",
        )
        self.company = config.get(
            "company",
            "Neitraco Groep",
        )
        self.url = config["url"]

        self.keywords = [
            keyword.strip().casefold()
            for keyword in config.get(
                "keywords",
                ["mechanical", "project"],
            )
            if keyword.strip()
        ]

        self.known_locations = [
            location.strip()
            for location in config.get(
                "locations",
                [],
            )
            if location.strip()
        ]

    def fetch_jobs(self) -> list[Job]:
        try:
            response = requests.get(
                self.url,
                timeout=30,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/127.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()

        except requests.RequestException as error:
            raise RuntimeError(
                "Neitraco vacancies page could not be loaded."
            ) from error

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        jobs_by_url: dict[str, Job] = {}
        vacancy_cards_found = 0

        listing_path = (
            urlparse(self.url)
            .path.rstrip("/")
            .casefold()
        )

        for link in soup.select(
            'a[href*="/technische-vacatures/"]'
        ):
            href = str(
                link.get("href", "")
            ).strip()

            if not href:
                continue

            job_url = urljoin(
                self.url,
                href,
            )

            parsed_url = urlparse(job_url)
            path = parsed_url.path.rstrip("/")
            path_lower = path.casefold()

            # Ignore the general vacancy listing page.
            if path_lower == listing_path:
                continue

            if not path_lower.startswith(
                "/technische-vacatures/"
            ):
                continue

            job_slug = path.split("/")[-1].strip()

            if not job_slug:
                continue

            card, heading = self._find_vacancy_card(link)

            if card is None or heading is None:
                continue

            title = self._clean_text(
                heading.get_text(
                    " ",
                    strip=True,
                )
            )

            if not title:
                continue

            vacancy_cards_found += 1

            title_lower = title.casefold()

            if self.keywords and not any(
                keyword in title_lower
                for keyword in self.keywords
            ):
                continue

            location = self._extract_location(card)

            jobs_by_url[job_url] = Job(
                source_id=self.source_id,
                source_name=self.source_name,
                job_id=job_slug.casefold(),
                title=title,
                url=job_url,
                company=self.company,
                location=location,
            )

        if vacancy_cards_found == 0:
            raise RuntimeError(
                "Neitraco loaded successfully, but no "
                "vacancy cards were extracted. The website "
                "structure may have changed."
            )

        return sorted(
            jobs_by_url.values(),
            key=lambda job: (
                job.title.casefold(),
                job.location.casefold(),
            ),
        )

    @staticmethod
    def _find_vacancy_card(
        link: Tag,
    ) -> tuple[Tag | None, Tag | None]:
        """
        Find the nearest parent containing the vacancy title.

        The link text is normally 'Bekijk de vacature',
        while the title is in a heading in the same card.
        """

        for parent in link.parents:
            if not isinstance(parent, Tag):
                continue

            heading = parent.find(
                ["h2", "h3", "h4", "h5"]
            )

            if heading is None:
                continue

            vacancy_links = parent.select(
                'a[href*="/technische-vacatures/"]'
            )

            # A single card may contain a title link and
            # a separate "Bekijk de vacature" link.
            if len(vacancy_links) <= 2:
                return parent, heading

        return None, None

    def _extract_location(
        self,
        card: Tag,
    ) -> str:
        # First try elements whose class describes a location.
        location_element = card.select_one(
            '[class*="location"], '
            '[class*="plaats"], '
            '[class*="city"]'
        )

        if location_element is not None:
            location = self._clean_text(
                location_element.get_text(
                    " ",
                    strip=True,
                )
            )

            if location:
                return location

        # Fallback to the known locations from sources.json.
        card_text = self._clean_text(
            card.get_text(
                " ",
                strip=True,
            )
        )

        for location in self.known_locations:
            pattern = (
                rf"(?<!\w)"
                rf"{re.escape(location)}"
                rf"(?!\w)"
            )

            if re.search(
                pattern,
                card_text,
                flags=re.IGNORECASE,
            ):
                return location

        return ""

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())