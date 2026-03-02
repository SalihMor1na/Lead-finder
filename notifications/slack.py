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

# Visuell poängindikator
def _score_emoji(score: float) -> str:
    if score >= 0.80:
        return "🟢"
    if score >= 0.60:
        return "🟡"
    return "🔴"


SOURCE_LABELS: dict[str, str] = {
    "jobtech_api": "Arbetsförmedlingen (jobbannons)",
    "google_search": "Google-sökning",
    "rss_feed": "Mynewsdesk / RSS",
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
                                    "🟢 Hög · 🟡 Medel · 🔴 Låg"
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
        desc = lead.description[:300] + "…" if len(lead.description) > 300 else lead.description

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *<{lead.url}|{lead.name}>*\n{tags_text}",
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Öppna länk", "emoji": True},
                    "url": lead.url,
                    "action_id": "open_lead",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Relevansscore:* {lead.score:.0%}"},
                    {"type": "mrkdwn", "text": f"*Källa:* {source_label}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"_{desc}_"},
            },
            {"type": "divider"},
        ]

    def _post(self, payload: dict):
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            log.error(f"Slack-notis misslyckades: {e}")
