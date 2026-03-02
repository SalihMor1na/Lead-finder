from abc import ABC, abstractmethod
from leads.models import Lead


class LeadSource(ABC):
    @abstractmethod
    def fetch_leads(self) -> list[Lead]:
        """Hämtar leads från denna källa. Returnerar en lista av Lead-objekt."""
        pass
