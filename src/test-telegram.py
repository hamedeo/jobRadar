from dotenv import load_dotenv

from src.models import Job
from src.notifier import send_telegram_job


def main() -> None:
    load_dotenv()

    test_job = Job(
        source_id="test",
        source_name="Job Radar Test",
        job_id="telegram-test",
        title="Mechanical Engineer — Telegram Test",
        company="Test Company",
        location="Eindhoven, Netherlands",
        url="https://example.com/test-job",
    )

    send_telegram_job(test_job)
    print("Telegram test message sent successfully.")


if __name__ == "__main__":
    main()
