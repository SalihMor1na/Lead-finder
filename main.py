"""
Sveriges Talare – Automatisk Kundupptäckt

Hittar potentiella kunder via lagliga, öppna datakällor och skickar
notiser till Slack. Körs antingen en gång eller schemalagt.

Datakällor (alla lagliga och öppna):
  • Arbetsförmedlingens JobTech API – bolag som rekryterar event-personal
  • Mynewsdesk RSS – pressmeddelanden om konferenser och event
  • Google Custom Search API – webbsökning efter eventarrangörer (valfri)

Kör:
  python main.py --once        # Kör en gång och avsluta
  python main.py --dry-run     # Testa utan att spara eller notifiera
  python main.py               # Schemalagd körning (standard: var 24h)
"""
import logging
import sys
import time
from argparse import ArgumentParser

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv är valfritt; använd systemets miljövariabler

from config import load_config
from leads.scorer import LeadScorer
from leads.sources.jobtech import JobTechSource
from leads.sources.rss_feeds import RSSFeedSource
from leads.sources.google_search import GoogleSearchSource
from notifications.slack import SlackNotifier
from storage.database import LeadDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run_discovery(config, dry_run: bool = False) -> int:
    """
    Kör en omgång av kundupptäckt.
    Returnerar antal nya kvalificerade leads som hittades.
    """
    log.info("── Startar kundupptäckt ──────────────────────────────")

    db = LeadDatabase(config.db_path)
    scorer = LeadScorer()
    notifier = SlackNotifier(config.slack_webhook_url)

    # Bygg lista med aktiva datakällor
    sources = [JobTechSource(), RSSFeedSource(config.rss_feed_urls or None)]
    if config.google_api_key and config.google_cse_id:
        sources.append(GoogleSearchSource(config.google_api_key, config.google_cse_id))
        log.info("Google Custom Search aktiverat")
    else:
        log.info("Google Custom Search avstängt (GOOGLE_API_KEY/GOOGLE_CSE_ID saknas)")

    new_leads = []
    total_fetched = 0

    for source in sources:
        source_name = type(source).__name__
        log.info(f"Hämtar leads från {source_name}…")
        try:
            leads = source.fetch_leads()
            total_fetched += len(leads)

            for lead in leads:
                if db.is_seen(lead):
                    continue  # Redan sett – hoppa över

                lead = scorer.score(lead)

                if lead.score >= config.min_score_threshold:
                    new_leads.append(lead)
                    if not dry_run:
                        db.mark_seen(lead)

        except Exception as e:
            log.error(f"Fel vid hämtning från {source_name}: {e}")

    # Sortera efter poäng, bästa leads först
    new_leads.sort(key=lambda l: l.score, reverse=True)

    stats = db.get_stats()
    log.info(
        f"Hämtade {total_fetched} leads totalt · "
        f"{len(new_leads)} nya · "
        f"{stats['total']} i databas totalt"
    )

    if new_leads:
        if dry_run:
            log.info("DRY-RUN – skickar inte till Slack. Nya leads:")
            for lead in new_leads:
                log.info(f"  [{lead.score:.0%}] {lead.name} ({lead.source})")
                log.info(f"         {lead.url}")
                log.info(f"         Taggar: {', '.join(lead.tags)}")
        else:
            log.info(f"Skickar {len(new_leads)} leads till Slack…")
            notifier.send_batch(new_leads)
            log.info("Slack-notiser skickade!")
    else:
        log.info("Inga nya kvalificerade leads hittades.")

    log.info("── Klar ──────────────────────────────────────────────")
    return len(new_leads)


def main():
    parser = ArgumentParser(description="Sveriges Talare – Automatisk Kundupptäckt")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Kör utan att spara till databas eller skicka till Slack",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Kör en gång och avsluta (annars körs det schemalagt)",
    )
    args = parser.parse_args()

    try:
        config = load_config()
    except ValueError as e:
        log.error(f"Konfigurationsfel: {e}")
        log.error("Kontrollera .env-filen. Se .env.example för alla variabler.")
        sys.exit(1)

    if args.once or args.dry_run:
        run_discovery(config, dry_run=args.dry_run)
    else:
        log.info(f"Schemalagd körning var {config.search_interval_hours}:e timme. Ctrl+C för att avsluta.")
        while True:
            run_discovery(config)
            interval = config.search_interval_hours * 3600
            log.info(f"Nästa körning om {config.search_interval_hours} timmar…")
            time.sleep(interval)


if __name__ == "__main__":
    main()
