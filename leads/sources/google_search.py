"""
Google Custom Search-källa.

Använder Googles officiella Custom Search API (lagligt, kräver API-nyckel).
Gratiskvota: 100 sökningar per dag. Betalplan tillgänglig vid behov.

Skapa nyckel: https://console.cloud.google.com/apis/credentials
Skapa sökmotor: https://programmablesearchengine.google.com/
"""
import logging

import requests

from leads.models import Lead
from leads.sources.base import LeadSource

log = logging.getLogger(__name__)

# Svenska sökfrågor riktade mot bolag som arrangerar event med talare
SEARCH_QUERIES: list[str] = [
    "konferens arrangör talare Sverige 2025",
    "event management boka föreläsare Sverige",
    "kick-off företagsevent talare keynote",
    "ledarskapskonferens föreläsare Sverige",
    "HR-konferens talare bokning",
    "årskonferens boka talare",
    "branschevent talare keynote Sverige",
    "inspirationsföreläsare företagsevent boka",
]

API_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchSource(LeadSource):
    """
    Söker via Google Custom Search API efter bolag som arrangerar
    svenska event och konferenser med talare.
    """

    def __init__(self, api_key: str, cse_id: str):
        self.api_key = api_key
        self.cse_id = cse_id

    def fetch_leads(self) -> list[Lead]:
        leads: list[Lead] = []
        for query in SEARCH_QUERIES:
            for item in self._search(query):
                url = item.get("link", "").strip()
                if not url:
                    continue
                leads.append(
                    Lead(
                        name=item.get("title", "").strip(),
                        url=url,
                        description=item.get("snippet", "").strip(),
                        source="google_search",
                    )
                )
        return leads

    def _search(self, query: str) -> list[dict]:
        try:
            resp = requests.get(
                API_URL,
                params={
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query,
                    "num": 10,
                    "gl": "se",         # Land: Sverige
                    "hl": "sv",         # Språk: svenska
                    "dateRestrict": "m3",  # Senaste 3 månaderna
                },
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            log.warning(f"Google Search fel för '{query}': {e}")
            return []
