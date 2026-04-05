# File: app/collectors/news_collector.py

import re
from app.models import Trigger
from app.collectors.rss_collector import fetch_rss_headlines
from app.engines.theme_detector import detect_theme_from_text


# Detect ticker simple (ex: NVDA, AMD etc.)
TICKER_REGEX = r"\b[A-Z]{2,5}\b"


def extract_tickers(text: str):
    matches = re.findall(TICKER_REGEX, text)
    return list(set(matches))


def is_relevant_news(text: str):
    """
    Filtru simplu: elimină macro noise slab
    """
    keywords = [
        "earnings", "guidance", "forecast", "deal", "contract",
        "ai", "chip", "data center", "cloud", "security",
        "oil", "gas", "uranium", "energy",
        "fda", "trial", "approval"
    ]

    return any(k in text for k in keywords)


def collect_news_triggers() -> list[Trigger]:
    raw_headlines = fetch_rss_headlines()

    triggers = []
    seen_titles = set()

    for item in raw_headlines:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()

        if not title or title.lower() in seen_titles:
            continue

        seen_titles.add(title.lower())

        combined_text = f"{title} {summary}".lower()

        # 🔥 FILTRU IMPORTANT
        if not is_relevant_news(combined_text):
            continue

        theme_name, subthemes, confidence = detect_theme_from_text(combined_text)

        # fallback deja vine din theme_detector
        urgency = "high" if confidence >= 7.5 else "medium"

        tickers = extract_tickers(title)

        triggers.append(
            Trigger(
                trigger_type="news",
                headline=title,
                theme_hint=theme_name,
                subthemes=subthemes,
                urgency=urgency,
                freshness="new",
                confidence=confidence,
                metadata={
                    "tickers": tickers,
                    "source": item.get("source"),
                    "link": item.get("link")
                }
            )
        )

    return triggers
