from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Job:
    source_id: str
    source_name: str
    job_id: str
    title: str
    url: str
    company: str = ""
    location: str = ""

    def unique_id(self) -> str:
        return f"{self.source_id}:{self.job_id}"

    def to_dict(self) -> dict:
        return asdict(self)
