# File: app/engines/theme_mapper.py
#
# REWRITE COMPLET — fara lista predefinita de companii.
#
# Filozofie corecta (din arhitectura):
# TRIGGER → TEMA → COMPANIE (descoperita din trigger)
#
# Tickerele vin exclusiv din:
# 1. Triggere news cu ticker explicit mentionat
# 2. Insider triggers Form 4 (ticker din XML)
# 3. Earnings triggers 8-K (ticker din filing)
# 4. (viitor) Volume spikes Polygon
#
# theme_registry e folosit DOAR pentru a clasifica tema unui trigger,
# nu pentru a genera companii.

import re
from app.models import Trigger, Opportunity
from app.engines.theme_detector import detect_theme_from_text

# Regex pentru ticker din text (2-5 litere majuscule)
# Filtreaza cuvinte comune care arata ca tickers
COMMON_WORDS = {
    "A", "I", "IT", "AI", "US", "UK", "EU", "UN", "AT", "BE", "BY",
    "DO", "GO", "IF", "IN", "IS", "NO", "OF", "ON", "OR", "SO", "TO",
    "UP", "VS", "WE", "AND", "ARE", "BUT", "FOR", "HAS", "NOT", "THE",
    "CEO", "CFO", "CTO", "COO", "IPO", "ETF", "GDP", "CPI", "FED",
    "SEC", "FDA", "NATO", "OPEC", "SPAC", "REIT", "ESG", "API", "SaaS",
    "LLC", "INC", "LTD", "PLC", "CORP", "NYSE", "NMS", "OTC", "ETH",
    "BTC", "USD", "EUR", "GBP", "JPY", "Q1", "Q2", "Q3", "Q4", "YOY",
    "QOQ", "EPS", "PE", "PB", "DCF", "EBIT", "EBITDA", "FCF",
}

TICKER_PATTERN = re.compile(r'\b([A-Z]{1,5})\b')


def extract_tickers_from_text(text: str) -> list[str]:
    """
    Extrage tickers potentiale din text.
    Filtreaza cuvinte comune si pastreaza doar ce arata a ticker real.
    """
    matches = TICKER_PATTERN.findall(text)
    tickers = []
    seen = set()

    for match in matches:
        if match in COMMON_WORDS:
            continue
        if len(match) < 2:
            continue
        if match not in seen:
            seen.add(match)
            tickers.append(match)

    return tickers


def map_triggers_to_opportunities(
    triggers: list[Trigger],
    insider_triggers: list[dict] | None = None,
    earnings_triggers: dict | None = None,
) -> list[Opportunity]:
    """
    Construieste oportunități EXCLUSIV din triggere reale.

    Surse de tickere (in ordine de prioritate):
    1. insider_triggers — ticker din Form 4 XML (Tier 1 Direct)
    2. earnings_triggers — ticker din 8-K filing (Tier 1 Direct)
    3. news triggers — ticker mentionat explicit in headline (Tier 2 Theme)

    Nu mai foloseste lista predefinita din theme_registry.
    """
    opportunities = []
    seen = set()  # (ticker, theme) — evita duplicate

    # ── Tier 1: Insider Buy triggers ─────────────────────────────
    if insider_triggers:
        for t in insider_triggers:
            ticker = t.get("ticker", "").upper()
            if not ticker:
                continue

            company_name = t.get("company_name", ticker)
            theme_hint, subthemes, confidence = detect_theme_from_text(
                f"{company_name} {ticker}"
            )

            key = (ticker, theme_hint)
            if key in seen:
                continue
            seen.add(key)

            opp = Opportunity(
                ticker=ticker,
                company_name=company_name,
                theme=theme_hint,
                subtheme=subthemes[0] if subthemes else None,
                role="Direct Signal",
                positioning="Insider Buy",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level="High",
                horizon="Swing",
                thesis="",
                why_now="",
                why_this_name="",
                ai_verdict="",
                status="ACTIVE WATCH"
            )
            opportunities.append(opp)

    # ── Tier 1: Earnings triggers (8-K Item 2.02) ────────────────
    if earnings_triggers:
        for ticker, data in earnings_triggers.items():
            ticker = ticker.upper()
            if not ticker:
                continue

            company_name = data.get("company_name", ticker)
            theme_hint, subthemes, confidence = detect_theme_from_text(
                f"{company_name} {ticker}"
            )

            key = (ticker, theme_hint)
            if key in seen:
                continue
            seen.add(key)

            trigger_type = data.get("trigger_type", "earnings_reported")
            role = "Earnings Reporter" if trigger_type == "earnings_reported" else "Earnings Upcoming"

            opp = Opportunity(
                ticker=ticker,
                company_name=company_name,
                theme=theme_hint,
                subtheme=subthemes[0] if subthemes else None,
                role=role,
                positioning="Earnings Catalyst",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level="Medium",
                horizon="Swing",
                thesis="",
                why_now="",
                why_this_name="",
                ai_verdict="",
                status="ACTIVE WATCH"
            )
            opportunities.append(opp)

    # ── Tier 2: News triggers cu ticker explicit ──────────────────
    for trigger in triggers:
        if trigger.trigger_type != "news":
            continue

        # Extrage tickers din headline
        headline = trigger.headline
        tickers_in_news = extract_tickers_from_text(headline.upper())

        # Filtreaza doar tickers care apar in headline (nu din tema generica)
        metadata_tickers = trigger.metadata.get("tickers", []) if hasattr(trigger, 'metadata') else []
        all_tickers = list(set(tickers_in_news + metadata_tickers))

        if not all_tickers:
            continue

        theme_hint = trigger.theme_hint
        subthemes = trigger.subthemes

        for ticker in all_tickers[:3]:  # max 3 tickers per stire
            if ticker in COMMON_WORDS:
                continue

            key = (ticker, theme_hint)
            if key in seen:
                continue
            seen.add(key)

            opp = Opportunity(
                ticker=ticker,
                company_name=ticker,  # numele va fi imbogatit ulterior
                theme=theme_hint,
                subtheme=subthemes[0] if subthemes else None,
                role="Theme Mention",
                positioning="News Trigger",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level="Low",
                horizon="Watch",
                thesis="",
                why_now="",
                why_this_name="",
                ai_verdict="",
                status="WATCH"
            )
            opportunities.append(opp)

    return opportunities
