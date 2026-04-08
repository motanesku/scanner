# File: app/engines/theme_mapper.py
#
# Mapează triggere → oportunități cu temă corectă.
#
# Sursa temei în ordine de prioritate:
# 1. TICKER_THEME_OVERRIDE — forțat manual
# 2. SIC code din ticker_universe
# 3. detect_theme_from_text — din RSS/company name
# 4. "General Market" — fallback (scor penalizat)

from app.models import Trigger, Opportunity
from app.engines.sic_theme_mapper import get_theme_for_ticker
from app.engines.theme_detector import detect_theme_from_text
from app.data.ticker_universe import get_ticker_sic
from app.engines.entity_resolver import get_universe
from app.utils.logger import log_info


def _resolve_theme(ticker: str, company_name: str, fallback_text: str = "") -> tuple[str, str | None]:
    """
    Rezolvă tema pentru un ticker.
    Returnează (theme_name, subtheme).
    Returnează (None, None) dacă tickerul e exclus.
    """
    universe = get_universe()
    sic_code, sic_desc = get_ticker_sic(ticker, universe)

    # 1. SIC theme mapper (include override manual și excludere)
    result = get_theme_for_ticker(ticker, sic_code)

    if result is None:
        return None, None  # exclus explicit

    if result != ("General Market", "Macro"):
        return result  # temă specifică din SIC sau override

    # 2. Fallback la RSS/text dacă SIC dă General Market
    if fallback_text:
        theme_name, subthemes, confidence = detect_theme_from_text(fallback_text.lower())
        if theme_name and theme_name != "General Market" and confidence >= 5.0:
            return theme_name, subthemes[0] if subthemes else None

    # 3. SIC description ca hint suplimentar
    if sic_desc:
        theme_name, subthemes, confidence = detect_theme_from_text(sic_desc.lower())
        if theme_name and theme_name != "General Market":
            return theme_name, subthemes[0] if subthemes else None

    return "General Market", "Macro"


def map_triggers_to_opportunities(
    triggers: list[Trigger],
    insider_triggers: list[dict] | None = None,
    earnings_triggers: dict | None = None,
) -> list[Opportunity]:

    opportunities = []
    seen = set()  # ticker — un ticker apare o singură dată

    # ── Tier 1: Insider Buy (Form 4) ─────────────────────────────
    # Insider buy NICIODATĂ nu se exclude — e cel mai valoros semnal
    if insider_triggers:
        for t in insider_triggers:
            ticker = t.get("ticker", "").upper()
            if not ticker or ticker in seen:
                continue

            company_name = t.get("company_name", ticker)
            theme, subtheme = _resolve_theme(ticker, company_name, company_name)

            # Dacă tema e None (exclus de override), fallback la General Market
            # Insider buy e prea important ca să fie pierdut
            if theme is None:
                theme, subtheme = "General Market", "Insider Signal"
                log_info(f"[Mapper] Insider {ticker} — sector excluded but keeping (insider buy)")

            seen.add(ticker)
            opportunities.append(Opportunity(
                ticker=ticker,
                company_name=company_name,
                theme=theme,
                subtheme=subtheme,
                role="Direct Signal",
                positioning="Insider Buy",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level="High",
                horizon="Swing",
                thesis="", why_now="", why_this_name="", ai_verdict="",
                status="ACTIVE WATCH"
            ))

    # ── Tier 1: Earnings 8-K ─────────────────────────────────────
    if earnings_triggers:
        for ticker, data in earnings_triggers.items():
            ticker = ticker.upper()
            if not ticker or ticker in seen:
                continue

            company_name = data.get("company_name", ticker)
            theme, subtheme = _resolve_theme(ticker, company_name, company_name)

            if theme is None:
                log_info(f"[Mapper] Earnings {ticker} ({company_name}) excluded (sector filter)")
                continue

            seen.add(ticker)

            trigger_type = data.get("trigger_type", "earnings_reported")
            role = "Earnings Reporter" if trigger_type == "earnings_reported" else "Earnings Upcoming"

            opportunities.append(Opportunity(
                ticker=ticker,
                company_name=company_name,
                theme=theme,
                subtheme=subtheme,
                role=role,
                positioning="Earnings Catalyst",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level="Medium",
                horizon="Swing",
                thesis="", why_now="", why_this_name="", ai_verdict="",
                status="ACTIVE WATCH"
            ))

    # ── Tier 2: News triggers cu ticker real ─────────────────────
    for trigger in triggers:
        if trigger.trigger_type != "news":
            continue

        metadata = trigger.metadata or {}
        tickers_with_conf = metadata.get("tickers", [])
        primary_ticker = metadata.get("primary_ticker")

        if not primary_ticker:
            continue

        signal_side = metadata.get("signal_side", "neutral")
        trigger_category = metadata.get("trigger_category", "theme")
        entity_confidence = metadata.get("entity_confidence", 0)
        has_direct_event = metadata.get("has_direct_event", False)

        if signal_side == "sell" and not has_direct_event:
            continue

        for ticker, conf in tickers_with_conf:
            ticker = ticker.upper()
            if ticker in seen:
                continue

            theme, subtheme = _resolve_theme(
                ticker, ticker,
                f"{trigger.headline} {trigger.theme_hint}"
            )

            if theme is None:
                continue

            seen.add(ticker)

            if entity_confidence == 10 and has_direct_event:
                priority = "High"
                role = "Direct News Signal"
            elif entity_confidence >= 8 and has_direct_event:
                priority = "Medium"
                role = "Company News"
            else:
                priority = "Low"
                role = "Theme Mention"

            opportunities.append(Opportunity(
                ticker=ticker,
                company_name=ticker,
                theme=theme,
                subtheme=subtheme,
                role=role,
                positioning=f"News: {trigger_category} ({signal_side})",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level=priority,
                horizon="Watch",
                thesis="", why_now="", why_this_name="", ai_verdict="",
                status="WATCH"
            ))

    log_info(f"[Mapper] {len(opportunities)} opportunities after sector filter")
    return opportunities
