# File: app/collectors/news_collector.py

import re
from app.models import Trigger
from app.collectors.rss_collector import fetch_rss_headlines
from app.engines.theme_detector import detect_theme_from_text
from app.utils.logger import log_info

# ── Pattern $TICKER explicit ──────────────────────────────────────
DOLLAR_TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b')

# ── Dicționar companie → ticker ───────────────────────────────────
# REGULI:
# - aliasuri de 2-3 litere: ELIMINATE (ge, de, sq, ms, gs etc.)
# - aliasuri ambigue: doar varianta completă a numelui
# - entity_confidence: $TICKER=10, nume_complet=8, alias_scurt=6
COMPANY_TO_TICKER = {
    # AI / Semiconductori
    "nvidia":               ("NVDA", 8),
    "advanced micro devices": ("AMD", 8),
    "intel corporation":    ("INTC", 8),
    "broadcom":             ("AVGO", 8),
    "qualcomm":             ("QCOM", 8),
    "micron technology":    ("MU", 8),
    "taiwan semiconductor": ("TSM", 8),
    "tsmc":                 ("TSM", 8),
    "asml":                 ("ASML", 8),
    "applied materials":    ("AMAT", 8),
    "lam research":         ("LRCX", 8),
    "kla corporation":      ("KLAC", 8),
    "marvell technology":   ("MRVL", 8),
    "arista networks":      ("ANET", 8),
    "super micro computer": ("SMCI", 8),
    "supermicro":           ("SMCI", 7),
    "credo technology":     ("CRDO", 8),
    "astera labs":          ("ALAB", 8),
    "arm holdings":         ("ARM", 8),
    "globalfoundries":      ("GFS", 8),

    # Cloud / Software
    "microsoft":            ("MSFT", 8),
    "alphabet":             ("GOOGL", 8),
    "amazon":               ("AMZN", 8),
    "meta platforms":       ("META", 8),
    "salesforce":           ("CRM", 8),
    "servicenow":           ("NOW", 8),
    "snowflake":            ("SNOW", 8),
    "datadog":              ("DDOG", 8),
    "palantir":             ("PLTR", 8),
    "crowdstrike":          ("CRWD", 8),
    "palo alto networks":   ("PANW", 8),
    "zscaler":              ("ZS", 8),
    "okta":                 ("OKTA", 8),
    "mongodb":              ("MDB", 8),
    "cloudflare":           ("NET", 8),
    "workday":              ("WDAY", 8),
    "adobe":                ("ADBE", 8),

    # Energie
    "exxonmobil":           ("XOM", 8),
    "chevron":              ("CVX", 8),
    "conocophillips":       ("COP", 8),
    "cameco":               ("CCJ", 8),
    "constellation energy": ("CEG", 8),
    "vistra":               ("VST", 8),
    "eaton corporation":    ("ETN", 8),
    "vertiv":               ("VRT", 8),
    "first solar":          ("FSLR", 8),
    "enphase energy":       ("ENPH", 8),
    "nextera energy":       ("NEE", 8),

    # Defense
    "lockheed martin":      ("LMT", 8),
    "raytheon":             ("RTX", 8),
    "northrop grumman":     ("NOC", 8),
    "general dynamics":     ("GD", 8),
    "boeing":               ("BA", 8),
    "l3harris":             ("LHX", 8),
    "kratos defense":       ("KTOS", 8),
    "bae systems":          ("BAESY", 7),

    # Fintech / Crypto
    "coinbase":             ("COIN", 8),
    "robinhood":            ("HOOD", 8),
    "paypal":               ("PYPL", 8),
    "microstrategy":        ("MSTR", 8),
    "sofi technologies":    ("SOFI", 8),
    "affirm":               ("AFRM", 8),
    "nubank":               ("NU", 8),

    # Biotech
    "vertex pharmaceuticals": ("VRTX", 8),
    "moderna":              ("MRNA", 8),
    "biontech":             ("BNTX", 8),
    "regeneron":            ("REGN", 8),
    "gilead sciences":      ("GILD", 8),
    "illumina":             ("ILMN", 8),
    "exact sciences":       ("EXAS", 8),
    "natera":               ("NTRA", 8),
    "crispr therapeutics":  ("CRSP", 8),
    "beam therapeutics":    ("BEAM", 8),
    "rxrx":                 ("RXRX", 7),

    # Auto / EV
    "tesla":                ("TSLA", 8),
    "rivian":               ("RIVN", 8),
    "lucid motors":         ("LCID", 8),

    # Consumer / Retail
    "apple":                ("AAPL", 8),
    "netflix":              ("NFLX", 8),
    "disney":               ("DIS", 8),
    "walmart":              ("WMT", 8),
    "costco":               ("COST", 8),
    "amazon":               ("AMZN", 8),

    # Finance
    "jpmorgan":             ("JPM", 8),
    "jp morgan":            ("JPM", 8),
    "goldman sachs":        ("GS", 8),
    "morgan stanley":       ("MS", 8),
    "bank of america":      ("BAC", 8),
    "wells fargo":          ("WFC", 8),
    "blackstone":           ("BX", 8),
    "blackrock":            ("BLK", 8),
    "berkshire hathaway":   ("BRK", 8),

    # Industrial
    "caterpillar":          ("CAT", 8),
    "john deere":           ("DE", 8),
    "general electric":     ("GE", 8),
    "honeywell":            ("HON", 8),
    "uber":                 ("UBER", 8),
    "airbnb":               ("ABNB", 8),
    "shopify":              ("SHOP", 8),
    "mercadolibre":         ("MELI", 8),
    "spotify":              ("SPOT", 8),
}

# ── Keywords eveniment direct ─────────────────────────────────────
# BUY side
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
]

# SELL side
SELL_KEYWORDS = [
    "misses", "miss", "below estimates", "disappoints",
    "cuts guidance", "lowers guidance", "cuts outlook",
    "warning", "profit warning",
    "offering", "secondary offering", "dilution",
    "investigation", "probe", "subpoena",
    "lawsuit", "sued", "legal action", "settlement",
    "layoffs", "job cuts", "restructuring",
    "downgrade", "price target cut", "underperform",
    "recall", "product recall",
    "ceo resigns", "cfo leaves", "executive departure",
    "fda rejects", "rejected", "clinical failure",
]

# NEUTRAL/THEME (no ticker needed)
THEME_KEYWORDS = [
    "artificial intelligence", "ai infrastructure", "data center",
    "semiconductor", "chipmaker", "gpu demand",
    "oil prices", "crude oil", "opec", "lng",
    "defense spending", "military budget", "pentagon",
    "cybersecurity", "ransomware attack", "data breach",
    "interest rates", "federal reserve", "inflation data",
    "tariff", "trade war", "sanctions",
    "nuclear energy", "uranium demand",
    "cloud spending", "capex",
]


def extract_tickers_from_headline(headline: str) -> list[tuple[str, int]]:
    """
    Returnează lista de (ticker, entity_confidence).
    Max 3 tickers per headline.

    entity_confidence:
    - 10: $TICKER explicit
    - 8: nume complet din dicționar cu word boundary
    - 6: alias scurt cu word boundary
    """
    results = []
    seen = set()
    headline_lower = headline.lower()

    # 1. $TICKER — cel mai precis, confidence 10
    dollar_matches = DOLLAR_TICKER_PATTERN.findall(headline)
    for ticker in dollar_matches:
        if ticker not in seen:
            seen.add(ticker)
            results.append((ticker.upper(), 10))

    # 2. Dicționar cu word boundaries
    for company_name, (ticker, conf) in COMPANY_TO_TICKER.items():
        if ticker in seen:
            continue
        pattern = rf"\b{re.escape(company_name)}\b"
        if re.search(pattern, headline_lower):
            seen.add(ticker)
            results.append((ticker, conf))

    return results[:3]  # max 3 tickers per headline


def classify_signal_side(text: str) -> str:
    """
    Clasifică direcția știrii:
    - 'buy'  → eveniment pozitiv pentru acțiune
    - 'sell' → eveniment negativ pentru acțiune
    - 'neutral' → context fără direcție clară
    """
    text_lower = text.lower()
    buy_hits = sum(1 for kw in BUY_KEYWORDS if kw in text_lower)
    sell_hits = sum(1 for kw in SELL_KEYWORDS if kw in text_lower)

    if buy_hits > sell_hits:
        return "buy"
    elif sell_hits > buy_hits:
        return "sell"
    return "neutral"


def classify_trigger_category(text: str) -> str:
    """
    Clasifică categoria evenimentului:
    earnings / guidance / contract / mna / fda / legal / macro / theme
    """
    text_lower = text.lower()

    if any(kw in text_lower for kw in ["earnings", "quarterly", "q1", "q2", "q3", "q4", "annual results", "eps"]):
        return "earnings"
    if any(kw in text_lower for kw in ["guidance", "forecast", "outlook", "raises", "cuts guidance"]):
        return "guidance"
    if any(kw in text_lower for kw in ["contract", "awarded", "wins contract", "secures"]):
        return "contract"
    if any(kw in text_lower for kw in ["acquires", "acquisition", "merger", "buyout", "takeover"]):
        return "mna"
    if any(kw in text_lower for kw in ["fda", "approval", "approved", "clinical", "trial", "drug"]):
        return "fda"
    if any(kw in text_lower for kw in ["lawsuit", "investigation", "probe", "settlement", "legal"]):
        return "legal"
    if any(kw in text_lower for kw in ["interest rate", "fed", "inflation", "gdp", "tariff", "opec"]):
        return "macro"
    return "theme"


def collect_news_triggers() -> list[Trigger]:
    """
    Colectează triggere din RSS feeds.

    Fiecare trigger are în metadata:
    - tickers: list[(ticker, confidence)]
    - primary_ticker: primul și cel mai confident ticker
    - signal_side: buy / sell / neutral
    - trigger_category: earnings / guidance / contract / mna / fda / legal / macro / theme
    - has_direct_event: bool
    - entity_confidence: 10/8/6/0
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

        # Detectează tema
        theme_name, subthemes, confidence = detect_theme_from_text(combined_lower)

        # Verifică dacă știrea are context financiar sau tematic
        has_direct_event = any(kw in combined_lower for kw in BUY_KEYWORDS + SELL_KEYWORDS)
        has_theme = any(kw in combined_lower for kw in THEME_KEYWORDS)

        # Skip dacă nu are niciun context relevant
        if not has_direct_event and not has_theme:
            stats["skipped"] += 1
            continue

        # Extrage tickere
        tickers_with_conf = extract_tickers_from_headline(title)
        if not tickers_with_conf:
            tickers_with_conf = extract_tickers_from_headline(summary[:300])

        signal_side = classify_signal_side(combined)
        trigger_category = classify_trigger_category(combined)

        urgency = "high" if confidence >= 7.5 or has_direct_event else "medium"

        if tickers_with_conf:
            # Trigger direct — are ticker identificat
            primary_ticker = tickers_with_conf[0][0]
            entity_confidence = tickers_with_conf[0][1]
            trigger_type = "news"

            # Direct trigger necesită: entity + direct event
            # Altfel confidence mai mic
            if not has_direct_event:
                confidence = min(confidence, 5.5)
                urgency = "medium"

            stats["with_ticker"] += 1
        else:
            # Trigger narativ — temă fără ticker specific
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
                    "tickers": tickers_with_conf,           # [(ticker, conf), ...]
                    "primary_ticker": primary_ticker,        # primul ticker sau None
                    "signal_side": signal_side,              # buy/sell/neutral
                    "trigger_category": trigger_category,    # earnings/contract/etc.
                    "entity_confidence": entity_confidence,  # 10/8/6/0
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
