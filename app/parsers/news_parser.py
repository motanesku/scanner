# File: app/parsers/news_parser.py

import re

THEME_KEYWORDS = {
    "AI Infrastructure": ["ai", "gpu", "datacenter", "inference", "training", "semiconductor"],
    "Semiconductors": ["chip", "semiconductor", "wafer", "fab", "gpu", "cpu"],
    "Energy": ["oil", "gas", "uranium", "nuclear", "lng", "power"],
    "Defense": ["defense", "military", "contract", "pentagon", "weapon"],
    "Biotech": ["fda", "clinical", "trial", "drug", "biotech", "approval"],
    "Copper": ["copper", "mining", "smelter", "metal", "commodity"],
    "Cloud": ["cloud", "saas", "server", "infrastructure", "hyperscaler"]
}

POSITIVE_KEYWORDS = [
    "beat", "surge", "record", "strong", "expands", "approval", "wins",
    "contract", "raises guidance", "growth", "demand", "bullish", "breakout"
]

NEGATIVE_KEYWORDS = [
    "miss", "offering", "dilution", "downgrade", "cuts guidance", "weak",
    "investigation", "delay", "lawsuit", "bearish", "decline"
]


def parse_news(news_items):
    """
    Parsează știri brute și extrage:
    - ticker
    - theme
    - sentiment
    - keywords
    """

    parsed = {}

    for item in news_items:
        title = str(item.get("title", "")).lower()
        summary = str(item.get("summary", "")).lower()
        text = f"{title} {summary}"

        ticker = item.get("ticker", "UNKNOWN")
        theme = detect_theme(text)
        sentiment = detect_sentiment(text)
        matched_keywords = extract_keywords(text)

        parsed_item = {
            "ticker": ticker,
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "theme": theme,
            "sentiment": sentiment,
            "keywords": matched_keywords,
            "source": item.get("source", "unknown"),
            "link": item.get("link", "")
        }

        if ticker not in parsed:
            parsed[ticker] = []

        parsed[ticker].append(parsed_item)

    return parsed


def detect_theme(text: str):
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return theme
    return "General"


def detect_sentiment(text: str):
    positive_hits = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    negative_hits = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    if positive_hits > negative_hits:
        return "bullish"
    elif negative_hits > positive_hits:
        return "bearish"
    return "neutral"


def extract_keywords(text: str):
    found = []
    all_keywords = set(POSITIVE_KEYWORDS + NEGATIVE_KEYWORDS)
    for kw in all_keywords:
        if kw in text:
            found.append(kw)
    return found
