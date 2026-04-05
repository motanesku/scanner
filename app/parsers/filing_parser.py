# File: app/parsers/filing_parser.py

FILING_BULLISH_KEYWORDS = [
    "agreement",
    "contract",
    "approval",
    "acquisition",
    "partnership",
    "award",
    "positive"
]

FILING_BEARISH_KEYWORDS = [
    "offering",
    "dilution",
    "shelf",
    "bankruptcy",
    "termination",
    "lawsuit",
    "default"
]


def parse_filings(filings):
    """
    Parsează filing-urile SEC și extrage:
    - filing type
    - sentiment
    - risk tags
    """

    parsed = []

    for filing in filings:
        title = str(filing.get("title", "")).lower()
        summary = str(filing.get("summary", "")).lower()
        text = f"{title} {summary}"

        filing_type = detect_filing_type(title)
        sentiment = detect_filing_sentiment(text)
        risk_flags = detect_risk_flags(text)

        parsed.append({
            "title": filing.get("title", ""),
            "summary": filing.get("summary", ""),
            "updated": filing.get("updated", ""),
            "link": filing.get("link", ""),
            "filing_type": filing_type,
            "sentiment": sentiment,
            "risk_flags": risk_flags,
            "source": filing.get("source", "SEC")
        })

    return parsed


def detect_filing_type(title: str):
    if "8-k" in title:
        return "8-K"
    if "s-3" in title:
        return "S-3"
    if "424b" in title:
        return "424B"
    if "10-q" in title:
        return "10-Q"
    if "10-k" in title:
        return "10-K"
    return "OTHER"


def detect_filing_sentiment(text: str):
    bullish_hits = sum(1 for kw in FILING_BULLISH_KEYWORDS if kw in text)
    bearish_hits = sum(1 for kw in FILING_BEARISH_KEYWORDS if kw in text)

    if bullish_hits > bearish_hits:
        return "bullish"
    elif bearish_hits > bullish_hits:
        return "bearish"
    return "neutral"


def detect_risk_flags(text: str):
    flags = []

    if "offering" in text or "shelf" in text:
        flags.append("dilution_risk")

    if "bankruptcy" in text or "default" in text:
        flags.append("financial_distress")

    if "lawsuit" in text:
        flags.append("legal_risk")

    return flags
