"""
RSS-källa: Publika nyhetsflöden om event och konferenser i Sverige.

Använder enbart publikt tillgängliga RSS-flöden – helt lagligt.
Mynewsdesk är Sveriges ledande PR-tjänst och deras sökning är öppen.
"""
import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from leads.models import Lead
from leads.sources.base import LeadSource

log = logging.getLogger(__name__)

# Söktermer på Mynewsdesk – pressmeddelanden om event med talare
_Q = quote  # alias för kortare rader

DEFAULT_FEED_URLS: list[str] = [
    f"https://www.mynewsdesk.com/search/pressreleases.rss?q={_Q('konferens talare')}",
    f"https://www.mynewsdesk.com/search/pressreleases.rss?q={_Q('föreläsare event')}",
    f"https://www.mynewsdesk.com/search/pressreleases.rss?q={_Q('keynote speaker')}&country=se",
    f"https://www.mynewsdesk.com/search/pressreleases.rss?q={_Q('kick-off talare')}",
    f"https://www.mynewsdesk.com/search/pressreleases.rss?q={_Q('årskonferens föreläsare')}",
]

HEADERS = {
    "User-Agent": "Sveriges-Talare-LeadFinder/1.0",
}


class RSSFeedSource(LeadSource):
    """
    Hämtar och tolkar publika RSS-flöden för att hitta bolag som
    annonserar om konferenser och event med talare.
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

            if not link:
                continue

            leads.append(
                Lead(
                    name=title,
                    url=link,
                    description=desc,
                    source="rss_feed",
                )
            )

        log.info(f"RSS {feed_url[:60]}…: {len(leads)} poster hämtade")
        return leads
