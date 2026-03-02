"""Lead-datamodell för Sveriges Talare kundupptäckt."""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Lead:
    name: str
    url: str
    description: str
    source: str
    score: float = 0.0
    industry: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    found_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def url_hash(self) -> str:
        """Unikt fingeravtryck baserat på URL - används för deduplicering."""
        normalized = self.url.lower().rstrip("/").strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
