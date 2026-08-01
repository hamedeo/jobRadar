from abc import ABC, abstractmethod

from src.models import Job


class JobSource(ABC):
    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        """Return all jobs currently listed by this source."""
        raise NotImplementedError
