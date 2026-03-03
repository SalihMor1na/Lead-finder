"""
RSS-källa: Svenska nyhets- och pressflöden om event och konferenser.

Använder enbart publikt tillgängliga RSS-flöden – helt lagliga.
Scorern filtrerar sedan ut leads med event/talare-nyckelord.
"""
import logging
import xml.etree.ElementTree as ET

import requests

from leads.models import Lead
from leads.sources.base import LeadSource

log = logging.getLogger(__name__)

DEFAULT_FEED_URLS: list[str] = [
    # DI Digital – Swedish business/tech news (verifierad 200)
    "https://www.di.se/digital/rss",
    # Dagens PS – Swedish business/finance news (verifierad 200)
    "https://www.dagensps.se/feed/",
    # HR Nytt – Swedish HR news, HR-organisationer köper talare (verifierad 200)
    "https://www.hrnytt.se/feed/",
    # Arbetet – Swedish work/labor news, fackliga och org-event (verifierad 200)
    "https://arbetet.se/feed/",
    # Dagens Nyheter – bred svensk nyhetskälla, stora företagsevent (verifierad 200)
    "https://www.dn.se/rss/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LeadFinder/1.0)",
}


class RSSFeedSource(LeadSource):
    """
    Hämtar och tolkar svenska RSS-flöden och letar efter bolag som
    arrangerar konferenser och event med talare.
    """

    def __init__(self, feed_urls: list[str] | None = None):
        self.feed_urls = feed_urls if feed_urls is not None else DEFAULT_FEED_URLS

    def fetch_leads(self) -> list[Lead]:
        leads: list[Lead] = []
        for url in self.feed_urls:
            leads.extend(self._parse_feed(url))
        return leads

    def _parse_feed(self, feed_url: str) -> list[Lead]:
        try:
            resp = requests.get(feed_url, timeout=15, headers=HEADERS)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            log.warning(f"Kunde inte hämta RSS-feed {feed_url}: {e}")
            return []

        leads: list[Lead] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()

            # Ta bort HTML-taggar ur beskrivningen
            import re
            desc = re.sub(r"<[^>]+>", " ", desc).strip()

            if not link:
                continue

            # Tidigt filter: kasta bort poster utan event/talare-koppling
            combined = f"{title} {desc}".lower()
            event_words = {
                "konferens", "event", "evenemang", "talare", "föreläsare",
                "keynote", "speaker", "kick-off", "kickoff", "seminarium",
                "summit", "mässa", "kongress", "symposium", "årskonferens",
                "bolagsstämma", "personaldag", "ledarskapsdag", "fortbildning",
                "kompetensutveckling", "ledarutveckling", "galakväll",
            }
            if not any(w in combined for w in event_words):
                continue  # Irrelevant post – hoppa över

            leads.append(
                Lead(
                    name=title,
                    url=link,
                    description=desc[:600],
                    source="rss_feed",
                )
            )

        log.info(f"RSS {feed_url[:60]}…: {len(leads)} relevanta poster")
        return leads
