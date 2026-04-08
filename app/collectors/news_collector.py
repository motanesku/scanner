# File: app/collectors/news_collector.py

import re
from app.models import Trigger
from app.collectors.rss_collector import fetch_rss_headlines
from app.engines.theme_detector import detect_theme_from_text
from app.data.theme_registry import THEME_REGISTRY


NOISE_PATTERNS = [
    "stocks mixed",
    "market opens",
    "market closes",
    "futures edge",
    "dow rises",
    "nasdaq rises",
    "s&p 500",
    "wall street",
    "stocks to watch",
    "premarket movers",
]

HIGH_VALUE_KEYWORDS = [
    "earnings",
    "guidance",
    "beat",
    "miss",
    "contract",
    "deal",
    "partnership",
    "approval",
    "acquisition",
    "merger",
    "offering",
    "dilution",
    "lawsuit",
    "investigation",
    "ai",
    "gpu",
    "data center",
    "cloud",
    "oil",
    "gas",
    "uranium",
    "copper",
    "cyber",
    "defense",
]

TICKER_REGEX = r"\b[A-Z]{2,5}\b"


def collect_news_triggers() -> list[Trigger]:
    raw_headlines = fetch_rss_headlines(limit_per_feed=15)
    triggers: list[Trigger] = []
    seen_titles = set()

    for item in raw_headlines:
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()

        if not title:
            continue

        normalized_title = normalize_text(title)
        if normalized_title in seen_titles:
            continue
        seen_titles.add(normalized_title)

        combined_text = f"{title} {summary}"
        combined_lower = combined_text.lower()

        if is_noise(combined_lower):
            continue

        if not is_relevant_news(combined_lower):
            continue

        explicit_tickers = extract_tickers(title)
        explicit_company_match = detect_company_match(combined_lower)

        theme_name, subthemes, confidence = detect_theme_from_text(combined_text)

        # fallback: dacă nu detectăm tema din text, dar detectăm companie/ticker din registry
        if (theme_name is None or theme_name == "General Market") and explicit_company_match:
            theme_name = explicit_company_match["theme"]
            subthemes = explicit_company_match["subthemes"]
            confidence = max(confidence, 7.0)

        if theme_name is None:
            continue

        urgency = determine_urgency(
            text=combined_lower,
            confidence=confidence,
            explicit_tickers=explicit_tickers,
            explicit_company_match=explicit_company_match is not None,
        )

        headline = title
        if explicit_tickers:
            headline = f"{title} [{' '.join(explicit_tickers)}]"

        triggers.append(
            Trigger(
                trigger_type="news",
                headline=headline,
                theme_hint=theme_name,
                subthemes=subthemes or [],
                urgency=urgency,
                freshness="new",
                confidence=float(confidence),
            )
        )

    return triggers


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_noise(text: str) -> bool:
    return any(pattern in text for pattern in NOISE_PATTERNS)


def is_relevant_news(text: str) -> bool:
    if any(keyword in text for keyword in HIGH_VALUE_KEYWORDS):
        return True

    # dacă menționează explicit o companie/ticker din registry, o considerăm relevantă
    if detect_company_match(text) is not None:
        return True

    return False


def extract_tickers(text: str) -> list[str]:
    matches = re.findall(TICKER_REGEX, text or "")
    filtered = []

    for m in matches:
        # filtrăm zgomotul evident
        if m in {"USA", "CEO", "FDA", "ETF", "EPS", "SEC", "IPO"}:
            continue
        filtered.append(m)

    return sorted(list(set(filtered)))


def detect_company_match(text: str):
    """
    Caută dacă o companie din registry sau tickerul ei apare explicit în text.
    Returnează tema aferentă, dacă există match.
    """

    text_upper = text.upper()

    for theme_name, theme_data in THEME_REGISTRY.items():
        for company in theme_data.get("companies", []):
            ticker = company.get("ticker", "").upper()
            company_name = company.get("company_name", "").lower()

            if ticker and re.search(rf"\b{re.escape(ticker)}\b", text_upper):
                return {
                    "theme": theme_name,
                    "subthemes": theme_data.get("subthemes", []),
                    "ticker": ticker,
                    "company_name": company.get("company_name", ""),
                }

            if company_name and company_name in text.lower():
                return {
                    "theme": theme_name,
                    "subthemes": theme_data.get("subthemes", []),
                    "ticker": ticker,
                    "company_name": company.get("company_name", ""),
                }

    return None


def determine_urgency(
    text: str,
    confidence: float,
    explicit_tickers: list[str],
    explicit_company_match: bool,
) -> str:
    if explicit_tickers or explicit_company_match:
        return "high"

    if any(k in text for k in ["earnings", "guidance", "contract", "approval", "offering", "dilution"]):
        return "high"

    if confidence >= 7.5:
        return "high"

    return "medium"