"""Konfigurationshantering – läser miljövariabler från .env."""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    slack_webhook_url: str
    google_api_key: str = ""
    google_cse_id: str = ""
    db_path: str = "leads.duckdb"
    search_interval_hours: int = 24
    min_score_threshold: float = 0.6
    rss_feed_urls: list[str] = field(default_factory=list)


def load_config() -> Config:
    """
    Laddar konfiguration från miljövariabler.
    Kastar ValueError om obligatoriska variabler saknas.
    """
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not slack_webhook_url:
        raise ValueError(
            "SLACK_WEBHOOK_URL saknas – ange Slack Incoming Webhook-URL i .env"
        )

    rss_raw = os.getenv("RSS_FEED_URLS", "")
    rss_feed_urls = [u.strip() for u in rss_raw.split(",") if u.strip()]

    return Config(
        slack_webhook_url=slack_webhook_url,
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        google_cse_id=os.getenv("GOOGLE_CSE_ID", "").strip(),
        db_path=os.getenv("DB_PATH", "leads.duckdb"),
        search_interval_hours=int(os.getenv("SEARCH_INTERVAL_HOURS", "24")),
        min_score_threshold=float(os.getenv("MIN_SCORE_THRESHOLD", "0.6")),
        rss_feed_urls=rss_feed_urls,
    )
