"""
Poängsätter leads baserat på hur sannolikt det är att de köper talare.

Logiken baseras på nyckelord och signaler som indikerar att ett bolag:
  - Arrangerar konferenser, event och kick-offs
  - Söker eller bokar föreläsare/talare
  - Är en branschorganisation, eventbyrå eller HR-avdelning
  - Aktivt rekryterar event-personal (starkt signal)
"""
from leads.models import Lead

# ── Positiva signaler ──────────────────────────────────────────────────────────

# Ord kopplade till event-arrangering
EVENT_KEYWORDS: dict[str, float] = {
    "konferens": 0.20,
    "conference": 0.20,
    "kongress": 0.20,
    "symposium": 0.15,
    "seminarium": 0.15,
    "seminar": 0.15,
    "summit": 0.15,
    "event": 0.10,
    "evenemang": 0.10,
    "kick-off": 0.20,
    "kick off": 0.20,
    "kickoff": 0.20,
    "årskonferens": 0.25,
    "bolagsstämma": 0.10,
    "galakväll": 0.10,
    "gala": 0.10,
    "mässa": 0.10,
}

# Ord kopplade till talare och föreläsningar
SPEAKER_KEYWORDS: dict[str, float] = {
    "talare": 0.30,
    "föreläsare": 0.30,
    "keynote": 0.25,
    "speaker": 0.25,
    "inspirationstalare": 0.35,
    "föredrag": 0.20,
    "föreläsning": 0.20,
    "boka talare": 0.40,
    "book speaker": 0.40,
    "moderator": 0.15,
    "paneldebatt": 0.15,
    "panelsamtal": 0.15,
}

# Ord som identifierar bolagets typ som eventrelaterat
ORGANIZER_KEYWORDS: dict[str, float] = {
    "arrangerar": 0.20,
    "anordnar": 0.20,
    "arrangör": 0.25,
    "eventbolag": 0.30,
    "eventbyrå": 0.30,
    "event management": 0.30,
    "konferensarrangör": 0.35,
    "mässarrangör": 0.25,
    "mötesbyrå": 0.25,
}

# Branscher som ofta köper talare
INDUSTRY_KEYWORDS: dict[str, float] = {
    "förbund": 0.15,
    "riksförbund": 0.20,
    "branschorganisation": 0.20,
    "riksorganisation": 0.20,
    "fackförbund": 0.15,
    "intresseorganisation": 0.15,
    "hr": 0.10,
    "human resources": 0.10,
    "ledarskap": 0.15,
    "ledarutveckling": 0.20,
    "talangutveckling": 0.15,
    "kompetensutveckling": 0.15,
    "pr-byrå": 0.15,
    "kommunikationsbyrå": 0.15,
    "marknadsföringsbyrå": 0.15,
}

# ── Negativa signaler ──────────────────────────────────────────────────────────

# Ord som indikerar konkurrent eller irrelevant aktör
NEGATIVE_KEYWORDS: dict[str, float] = {
    "talarförmedling": -0.50,
    "talarbyrå": -0.50,
    "speakers bureau": -0.50,
    "röstcoach": -0.20,
    "retorikutbildning": -0.15,
}


class LeadScorer:
    """Poängsätter ett Lead mellan 0.0 och 1.0."""

    def score(self, lead: Lead) -> Lead:
        text = f"{lead.name} {lead.description}".lower()
        total = 0.0
        tags: list[str] = []

        # Event-arrangemang
        event_score = sum(w for kw, w in EVENT_KEYWORDS.items() if kw in text)
        if event_score > 0:
            total += min(event_score, 0.35)
            tags.append("event-arrangör")

        # Talare/föreläsare
        speaker_score = sum(w for kw, w in SPEAKER_KEYWORDS.items() if kw in text)
        if speaker_score > 0:
            total += min(speaker_score, 0.40)
            tags.append("talare-relaterat")

        # Eventbolag/-byrå
        organizer_score = sum(w for kw, w in ORGANIZER_KEYWORDS.items() if kw in text)
        if organizer_score > 0:
            total += min(organizer_score, 0.30)
            tags.append("eventbolag")

        # Relevant bransch
        industry_score = sum(w for kw, w in INDUSTRY_KEYWORDS.items() if kw in text)
        if industry_score > 0:
            total += min(industry_score, 0.25)
            tags.append("relevant-bransch")

        # Bonus: hämtat från JobTech = aktivt rekryterar event-personal
        if lead.source == "jobtech_api":
            total += 0.15
            tags.append("aktiv-rekrytering")

        # Negativa signaler
        for kw, w in NEGATIVE_KEYWORDS.items():
            if kw in text:
                total += w  # w är negativt
                tags.append("trolig-konkurrent")

        lead.score = max(0.0, min(total, 1.0))
        lead.tags = list(set(tags))
        return lead
