# File: app/collectors/news_collector.py

import re
from app.models import Trigger
from app.collectors.rss_collector import fetch_rss_headlines
from app.engines.entity_resolver import resolve_tickers
from app.engines.theme_detector import detect_theme_from_text
from app.utils.logger import log_info

# ── Clasificare semnal ────────────────────────────────────────────

BUY_KEYWORDS = [
    "beats", "beat", "exceeds", "surpasses", "tops estimates",
    "raises guidance", "raises forecast", "raises outlook",
    "record revenue", "record earnings", "record profit",
    "fda approves", "fda approval", "fda clears", "approved",
    "wins contract", "awarded contract", "secures contract",
    "acquires", "acquisition", "merger agreement",
    "buyback", "share repurchase",
    "upgrade", "price target raised", "outperform",
    "strong quarter", "strong results", "better than expected",
    "partnership", "strategic agreement", "joint venture",
    "dividend increase", "special dividend",
    "new contract", "major deal", "landmark deal",
]

SELL_KEYWORDS = [
    "misses", "miss", "below estimates", "disappoints",
    "cuts guidance", "lowers guidance", "cuts outlook",
    "profit warning", "revenue warning",
    "offering", "secondary offering", "dilution", "shelf registration",
    "investigation", "probe", "subpoena", "charged",
    "lawsuit", "sued", "legal action", "settlement",
    "layoffs", "job cuts", "restructuring", "downsizing",
    "downgrade", "price target cut", "underperform", "sell rating",
    "recall", "product recall", "safety issue",
    "ceo resigns", "cfo leaves", "executive departure",
    "fda rejects", "fda rejection", "clinical failure", "trial failure",
    "revenue decline", "loss widens", "margin compression",
]

THEME_KEYWORDS = [
    "artificial intelligence", "ai infrastructure", "data center",
    "semiconductor", "chipmaker", "gpu demand",
    "oil prices", "crude oil", "opec", "lng", "energy transition",
    "defense spending", "military budget", "pentagon", "nato",
    "cybersecurity", "ransomware", "data breach", "zero trust",
    "interest rates", "federal reserve", "inflation", "gdp",
    "tariff", "trade war", "sanctions", "export controls",
    "nuclear energy", "uranium", "small modular reactor",
    "cloud spending", "capex", "hyperscaler",
    "gene therapy", "clinical trial", "fda",
]

TRIGGER_CATEGORY_MAP = [
    ("earnings",  ["earnings", "quarterly", "q1", "q2", "q3", "q4", "annual results", "eps", "revenue beat", "revenue miss"]),
    ("guidance",  ["guidance", "forecast", "outlook", "raises guidance", "cuts guidance", "lowers guidance"]),
    ("contract",  ["contract", "awarded", "wins contract", "secures", "pentagon contract", "government contract"]),
    ("mna",       ["acquires", "acquisition", "merger", "buyout", "takeover", "deal valued"]),
    ("fda",       ["fda", "approval", "approved", "clinical", "trial", "drug", "pdufa", "nda", "bla"]),
    ("legal",     ["lawsuit", "investigation", "probe", "settlement", "charged", "subpoena"]),
    ("insider",   ["insider", "form 4", "13d", "13g", "beneficial ownership"]),
    ("offering",  ["offering", "dilution", "shelf", "secondary", "at-the-market"]),
    ("macro",     ["interest rate", "federal reserve", "inflation", "gdp", "tariff", "opec", "sanctions"]),
]


def classify_signal_side(text: str) -> str:
    text_lower = text.lower()
    buy_hits = sum(1 for kw in BUY_KEYWORDS if kw in text_lower)
    sell_hits = sum(1 for kw in SELL_KEYWORDS if kw in text_lower)
    if buy_hits > sell_hits:
        return "buy"
    elif sell_hits > buy_hits:
        return "sell"
    return "neutral"


def classify_trigger_category(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in TRIGGER_CATEGORY_MAP:
        if any(kw in text_lower for kw in keywords):
            return category
    return "theme"


def collect_news_triggers() -> list[Trigger]:
    """
    Colectează triggere din RSS.

    Fiecare trigger are în metadata:
    - tickers: [(ticker, entity_confidence), ...]
    - primary_ticker: primul ticker sau None
    - signal_side: buy / sell / neutral
    - trigger_category: earnings / guidance / contract / mna / fda / legal / macro / theme
    - entity_confidence: 10 ($TICKER), 8 (alias index), 0 (niciun ticker)
    - has_direct_event: bool
    - source, link
    """
    raw_headlines = fetch_rss_headlines()
    log_info(f"[News] Processing {len(raw_headlines)} headlines...")

    triggers = []
    seen_titles = set()
    stats = {"with_ticker": 0, "theme_only": 0, "skipped": 0}

    for item in raw_headlines:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()

        if not title or title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())

        combined = f"{title} {summary}"
        combined_lower = combined.lower()

        # Verifică relevanta
        has_direct_event = any(kw in combined_lower for kw in BUY_KEYWORDS + SELL_KEYWORDS)
        has_theme = any(kw in combined_lower for kw in THEME_KEYWORDS)

        if not has_direct_event and not has_theme:
            stats["skipped"] += 1
            continue

        # Detectează tema
        theme_name, subthemes, confidence = detect_theme_from_text(combined_lower)

        # Rezolvă tickere din text via entity_resolver
        tickers_with_conf = resolve_tickers(combined, max_results=3)

        signal_side = classify_signal_side(combined)
        trigger_category = classify_trigger_category(combined)

        urgency = "high" if confidence >= 7.5 or has_direct_event else "medium"

        if tickers_with_conf:
            primary_ticker = tickers_with_conf[0][0]
            entity_confidence = tickers_with_conf[0][1]
            trigger_type = "news"

            # Direct trigger: necesită entity + eveniment clar
            if not has_direct_event:
                confidence = min(confidence, 5.5)
                urgency = "medium"

            stats["with_ticker"] += 1
        else:
            primary_ticker = None
            entity_confidence = 0
            trigger_type = "theme"
            stats["theme_only"] += 1

        triggers.append(
            Trigger(
                trigger_type=trigger_type,
                headline=title,
                theme_hint=theme_name,
                subthemes=subthemes,
                urgency=urgency,
                freshness="new",
                confidence=confidence,
                metadata={
                    "tickers": tickers_with_conf,
                    "primary_ticker": primary_ticker,
                    "signal_side": signal_side,
                    "trigger_category": trigger_category,
                    "entity_confidence": entity_confidence,
                    "has_direct_event": has_direct_event,
                    "source": item.get("source"),
                    "link": item.get("link"),
                }
            )
        )

    log_info(
        f"[News] {len(triggers)} triggers — "
        f"{stats['with_ticker']} cu ticker, "
        f"{stats['theme_only']} narrative, "
        f"{stats['skipped']} skipped"
    )
    return triggers
