"""
JobTech-källa: Arbetsförmedlingens publika API (JobTech Dev).

Söker efter bolag som aktivt rekryterar event- och konferenskoordinatorer
samt roller inom HR, ledarskap och kommunikation – alla starka signaler
att bolaget arrangerar interna event och kan behöva talare.

API-dokumentation: https://jobsearch.api.jobtechdev.se/
Helt gratis och öppet att använda - kräver ingen registrering.
"""
import logging

import requests

from leads.models import Lead
from leads.sources.base import LeadSource

log = logging.getLogger(__name__)

# Roller som indikerar att bolaget arrangerar event och kan köpa talare
SEARCH_QUERIES = [
    # Direkta event-roller
    "eventansvarig konferens",
    "konferenskoordinator",
    "eventprojektledare",
    "event manager",
    "evenemangsprojektledare",
    "konferensarrangör",
    "eventproducent",
    "mötes- och eventansvarig",
    "eventkoordinator",
    # HR och intern kommunikation – arrangerar ofta kick-offs och personalkonferenser
    "hr-chef konferens",
    "people and culture manager",
    "internal communications",
    "internkommunikation",
    "employer branding",
    # Ledarskaps- och kompetensutveckling – köper föreläsare
    "ledarutveckling",
    "kompetensutvecklingschef",
    "learning and development",
    # Kommunikation och PR – arrangerar presskonferenser och branschevent
    "kommunikationschef",
    "pr-chef",
    "marknadskoordinator event",
]

API_BASE = "https://jobsearch.api.jobtechdev.se/search"
COUNTRY_SWEDEN = "199"  # Landskod för Sverige i JobTech API


class JobTechSource(LeadSource):
    """
    Söker i Arbetsförmedlingens platsbank efter bolag som anställer
    event-, HR- och kommunikationspersonal – ett starkt tecken på att
    de arrangerar event och kan vara intresserade av att boka talare.
    """

    def fetch_leads(self) -> list[Lead]:
        leads: list[Lead] = []
        seen_employers: set[str] = set()

        for query in SEARCH_QUERIES:
            jobs = self._search(query)
            for job in jobs:
                employer = job.get("employer", {})
                company_name = (employer.get("name") or "").strip()
                if not company_name or company_name in seen_employers:
                    continue
                seen_employers.add(company_name)

                url = (
                    employer.get("url")
                    or job.get("webpage_url")
                    or f"https://arbetsformedlingen.se/platsbanken/annonser/{job.get('id', '')}"
                )
                headline = job.get("headline", "")
                raw_desc = job.get("description", {}).get("text", "") or ""
                description = f"Söker: {headline}. {raw_desc[:500]}"

                leads.append(
                    Lead(
                        name=company_name,
                        url=url.strip(),
                        description=description.strip(),
                        source="jobtech_api",
                    )
                )

        log.info(f"JobTech API: {len(leads)} unika arbetsgivare hittade")
        return leads

    def _search(self, query: str) -> list[dict]:
        try:
            resp = requests.get(
                API_BASE,
                params={"q": query, "limit": 50, "country": COUNTRY_SWEDEN},
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("hits", [])
        except Exception as e:
            log.warning(f"JobTech API fel för '{query}': {e}")
            return []
