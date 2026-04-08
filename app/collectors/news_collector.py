# File: app/collectors/news_collector.py

import re
from app.models import Trigger
from app.collectors.rss_collector import fetch_rss_headlines
from app.engines.theme_detector import detect_theme_from_text
from app.data.company_aliases import COMPANY_ALIASES


# Patternuri precise
DOLLAR_TICKER_RE = re.compile(r'(?<!\w)\$([A-Z]{1,5})(?!\w)')
EXCHANGE_TICKER_RE = re.compile(r'\b(?:NASDAQ|NYSE|AMEX)[:\s]+([A-Z]{1,5})\b', re.IGNORECASE)
PAREN_TICKER_RE = re.compile(r'\(([A-Z]{1,5})\)')

# blacklist minim de cuvinte care au apărut false în output
STOPWORDS = {
    "A", "AI", "AM", "AN", "AND", "ARE", "AS", "AT", "BE", "BUT", "BY",
    "CEO", "CFO", "COO", "CTO", "DAY", "DEAL", "DO", "EPS", "ETF", "FDA",
    "FED", "FOR", "FROM", "GET", "GO", "HAS", "HIGH", "HOW", "IN", "IS",
    "IT", "ITS", "LOW", "MAKE", "MOST", "NEW", "NO", "NOT", "NOW", "OIL",
    "ON", "ONE", "OR", "OUR", "OUT", "Q1", "Q2", "Q3", "Q4", "RATES",
    "SEC", "SO", "STOCK", "THAT", "THE", "THIS", "TIME", "TO", "TOP",
    "UP", "USA", "USE", "WAR", "WEEK", "WHAT", "WHICH", "WITH", "YOU",
    "YOUR", "AFTER", "ABOUT", "FIRST", "FILES", "JOBS", "SHIFT", "BANK",
    "SAFE"  # companie reală la tine, dar prea ambiguă în headlines globale; o lăsăm doar prin alias match
}

HIGH_VALUE_KEYWORDS = [
    "earnings", "guidance", "beat", "miss", "contract", "deal", "partnership",
    "approval", "approved", "acquisition", "acquire", "merger", "buyout",
    "offering", "dilution", "lawsuit", "investigation", "fda", "pentagon",
    "opec", "saudi aramco", "data center", "datacenter", "gpu", "semiconductor",
    "chip", "cloud", "cyber", "cybersecurity", "uranium", "oil", "gas",
    "defense", "military", "rare disease"
]

NOISE_PATTERNS = [
    "stocks mixed",
    "market opens",
    "market closes",
    "futures edge",
    "wall street",
    "stocks to watch",
    "premarket movers",
    "top stocks",
    "market roundup",
]


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

        explicit_tickers = extract_precise_tickers(title)
        alias_matches = detect_company_aliases(combined_lower)

        has_direct_entity = bool(explicit_tickers or alias_matches)
        has_high_value_signal = is_high_value_news(combined_lower)

        # dacă nu avem nici companie, nici trigger tematic util, o ignorăm
        if not has_direct_entity and not has_high_value_signal:
            continue

        theme_name, subthemes, confidence = detect_theme_from_text(combined_text)

        if not theme_name:
            continue

        signal_origin = "direct" if has_direct_entity else "theme"
        urgency = determine_urgency(
            text=combined_lower,
            has_direct_entity=has_direct_entity,
            confidence=confidence
        )

        # tickerul final: întâi ticker explicit, apoi alias map
        final_tickers = []
        for t in explicit_tickers:
            if t not in final_tickers:
                final_tickers.append(t)

        for t in alias_matches:
            if t not in final_tickers:
                final_tickers.append(t)

        triggers.append(
            Trigger(
                trigger_type="news",
                headline=title,
                theme_hint=theme_name,
                subthemes=subthemes or [],
                urgency=urgency,
                freshness="new",
                confidence=float(confidence),
                metadata={
                    "tickers": final_tickers,
                    "signal_origin": signal_origin,
                    "source": item.get("source", ""),
                    "link": item.get("link", ""),
                    "published": item.get("published", ""),
                    "company_alias_matches": alias_matches,
                }
            )
        )

    return triggers


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_noise(text: str) -> bool:
    return any(pattern in text for pattern in NOISE_PATTERNS)


def is_high_value_news(text: str) -> bool:
    return any(keyword in text for keyword in HIGH_VALUE_KEYWORDS)


def extract_precise_tickers(text: str) -> list[str]:
    """
    Extragem doar tickere foarte probabile:
    1. $TICKER
    2. NASDAQ:NVDA / NYSE:XOM
    3. Company (TICKER)
    """
    candidates = []

    for match in DOLLAR_TICKER_RE.findall(text):
        add_valid_ticker(candidates, match)

    for match in EXCHANGE_TICKER_RE.findall(text):
        add_valid_ticker(candidates, match)

    for match in PAREN_TICKER_RE.findall(text):
        add_valid_ticker(candidates, match)

    return candidates


def add_valid_ticker(bucket: list[str], ticker: str):
    ticker = ticker.upper().strip()

    if not ticker:
        return
    if ticker in STOPWORDS:
        return
    if len(ticker) < 1 or len(ticker) > 5:
        return
    if not ticker.isalpha():
        return
    if ticker not in COMPANY_ALIASES and ticker not in {"NVDA", "AMD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "LMT", "VRTX", "XOM", "CVX", "CCJ", "SMCI", "ANET", "PANW", "CRWD", "TSM", "INTC"}:
        return

    if ticker not in bucket:
        bucket.append(ticker)


def detect_company_aliases(text_lower: str) -> list[str]:
    matched = []

    for ticker, aliases in COMPANY_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias.lower())}\b", text_lower):
                if ticker not in matched:
                    matched.append(ticker)
                break

    return matched


def determine_urgency(text: str, has_direct_entity: bool, confidence: float) -> str:
    if has_direct_entity and any(
        k in text for k in [
            "earnings", "guidance", "contract", "deal", "approval", "approved",
            "acquisition", "merger", "offering", "dilution", "lawsuit", "investigation"
        ]
    ):
        return "high"

    if has_direct_entity:
        return "high"

    if confidence >= 7.5:
        return "high"

    return "medium"
