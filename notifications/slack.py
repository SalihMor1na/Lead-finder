"""
Slack-notiser via Incoming Webhook.

Skickar snyggt formaterade meddelanden med Block Kit för varje nytt lead.

Inställning:
  1. Gå till https://api.slack.com/apps
  2. Skapa ny app → Incoming Webhooks → Lägg till webhook
  3. Kopiera webhook-URL till SLACK_WEBHOOK_URL i .env
"""
import logging

import requests

from leads.models import Lead

log = logging.getLogger(__name__)

def _score_emoji(score: float) -> str:
    if score >= 0.80:
        return ":large_green_circle:"
    if score >= 0.55:
        return ":large_yellow_circle:"
    return ":large_orange_circle:"


def _valid_url(url: str) -> bool:
    """True om URL:en är giltig för Slack-knappar (måste vara http/https)."""
    return bool(url) and (url.startswith("http://") or url.startswith("https://"))


SOURCE_LABELS: dict[str, str] = {
    "jobtech_api": "Arbetsförmedlingen (jobbannons)",
    "google_search": "Google-sökning",
    "rss_feed": "RSS-nyheter",
}


class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_batch(self, leads: list[Lead]):
        """Skickar en sammanfattning följt av individuella lead-kort (max 10)."""
        if not leads:
            return

        self._post(
            {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Sveriges Talare – {len(leads)} nya potentiella kunder!",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": (
                                    f"Visar topp *{min(len(leads), 10)}* leads "
                                    "sorterade efter relevansscore. "
                                    ":large_green_circle: Hög · :large_yellow_circle: Medel · :large_orange_circle: Lägre"
                                ),
                            }
                        ],
                    },
                ]
            }
        )

        for lead in leads[:10]:
            self._post({"blocks": self._build_lead_blocks(lead)})

    def send_lead(self, lead: Lead):
        """Skickar ett enskilt lead-kort."""
        self._post({"blocks": self._build_lead_blocks(lead)})

    def _build_lead_blocks(self, lead: Lead) -> list[dict]:
        emoji = _score_emoji(lead.score)
        source_label = SOURCE_LABELS.get(lead.source, lead.source)
        tags_text = (
            "  ".join(f"`{t}`" for t in lead.tags) if lead.tags else "_inga taggar_"
        )
        desc = lead.description[:280] + "..." if len(lead.description) > 280 else lead.description
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        has_valid_url = _valid_url(lead.url)
        name_text = (
            f"*<{lead.url}|{lead.name}>*" if has_valid_url else f"*{lead.name}*"
        )

        header_section: dict = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} {name_text}\n{tags_text}",
            },
        }
        if has_valid_url:
            header_section["accessory"] = {
                "type": "button",
                "text": {"type": "plain_text", "text": "Oppna", "emoji": False},
                "url": lead.url[:2000],
                "action_id": f"open_{lead.url_hash}",
            }

        blocks = [
            header_section,
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Relevansscore:* {lead.score:.0%}"},
                    {"type": "mrkdwn", "text": f"*Kalla:* {source_label}"},
                ],
            },
        ]
        if desc:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": f"_{desc}_"}}
            )
        blocks.append({"type": "divider"})
        return blocks

    def _post(self, payload: dict):
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            log.error(f"Slack-notis misslyckades: {e}")
