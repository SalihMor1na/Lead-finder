"""
DuckDB-lagring för deduplicering av leads.

Håller koll på vilka leads som redan hittats och skickats till Slack,
så att systemet aldrig skickar samma lead två gånger.
"""
import logging
from datetime import datetime, timezone

import duckdb

from leads.models import Lead

log = logging.getLogger(__name__)


class LeadDatabase:
    """
    Lokal DuckDB-databas som lagrar alla leads som redan bearbetats.
    Används för att undvika dubbla notiser i Slack.
    """

    def __init__(self, db_path: str):
        self.conn = duckdb.connect(db_path)
        self._init_schema()
        count = self.conn.execute("SELECT COUNT(*) FROM seen_leads").fetchone()[0]
        log.info(f"Databas öppnad: {db_path} ({count} leads sedan tidigare)")

    def _init_schema(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_leads (
                url_hash  VARCHAR PRIMARY KEY,
                url       VARCHAR NOT NULL,
                name      VARCHAR,
                score     DOUBLE,
                source    VARCHAR,
                found_at  TIMESTAMP
            )
            """
        )

    def is_seen(self, lead: Lead) -> bool:
        """Returnerar True om detta lead redan finns i databasen."""
        result = self.conn.execute(
            "SELECT 1 FROM seen_leads WHERE url_hash = ?",
            [lead.url_hash],
        ).fetchone()
        return result is not None

    def mark_seen(self, lead: Lead):
        """Sparar ett lead i databasen så att det inte skickas igen."""
        if self.is_seen(lead):
            return
        found_at = lead.found_at or datetime.now(timezone.utc)
        self.conn.execute(
            """
            INSERT INTO seen_leads (url_hash, url, name, score, source, found_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                lead.url_hash,
                lead.url,
                lead.name,
                lead.score,
                lead.source,
                found_at.isoformat(),
            ],
        )

    def get_stats(self) -> dict:
        """Returnerar statistik om databasen."""
        total = self.conn.execute("SELECT COUNT(*) FROM seen_leads").fetchone()[0]
        by_source = self.conn.execute(
            "SELECT source, COUNT(*) FROM seen_leads GROUP BY source"
        ).fetchall()
        return {
            "total": total,
            "by_source": {row[0]: row[1] for row in by_source},
        }

    def close(self):
        self.conn.close()
