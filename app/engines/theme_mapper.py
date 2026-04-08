# File: app/engines/theme_mapper.py

from app.models import Trigger, Opportunity
from app.engines.theme_detector import detect_theme_from_text
from app.utils.logger import log_info


def map_triggers_to_opportunities(
    triggers: list[Trigger],
    insider_triggers: list[dict] | None = None,
    earnings_triggers: dict | None = None,
) -> list[Opportunity]:

    opportunities = []
    seen = set()  # (ticker, theme)

    # ── Tier 1: Insider Buy (Form 4) ─────────────────────────────
    if insider_triggers:
        for t in insider_triggers:
            ticker = t.get("ticker", "").upper()
            if not ticker:
                continue

            company_name = t.get("company_name", ticker)
            theme_hint, subthemes, _ = detect_theme_from_text(
                f"{company_name} {ticker}"
            )

            key = (ticker, theme_hint)
            if key in seen:
                continue
            seen.add(key)

            opportunities.append(Opportunity(
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
                thesis="", why_now="", why_this_name="", ai_verdict="",
                status="ACTIVE WATCH"
            ))

    # ── Tier 1: Earnings 8-K ─────────────────────────────────────
    if earnings_triggers:
        for ticker, data in earnings_triggers.items():
            ticker = ticker.upper()
            if not ticker:
                continue

            company_name = data.get("company_name", ticker)
            theme_hint, subthemes, _ = detect_theme_from_text(
                f"{company_name} {ticker}"
            )

            key = (ticker, theme_hint)
            if key in seen:
                continue
            seen.add(key)

            trigger_type = data.get("trigger_type", "earnings_reported")
            role = "Earnings Reporter" if trigger_type == "earnings_reported" else "Earnings Upcoming"

            opportunities.append(Opportunity(
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
                thesis="", why_now="", why_this_name="", ai_verdict="",
                status="ACTIVE WATCH"
            ))

    # ── Tier 2: News triggers cu ticker real ─────────────────────
    for trigger in triggers:
        if trigger.trigger_type != "news":
            continue

        metadata = trigger.metadata or {}
        primary_ticker = metadata.get("primary_ticker")
        tickers_with_conf = metadata.get("tickers", [])

        if not primary_ticker:
            continue

        signal_side = metadata.get("signal_side", "neutral")
        trigger_category = metadata.get("trigger_category", "theme")
        entity_confidence = metadata.get("entity_confidence", 0)
        has_direct_event = metadata.get("has_direct_event", False)

        # Skip știri sell fără eveniment direct clar
        # (prea mult risc de fals pozitiv)
        if signal_side == "sell" and not has_direct_event:
            continue

        theme_hint = trigger.theme_hint
        subthemes = trigger.subthemes

        # Procesează toate tickerele din headline (max 3)
        for ticker, conf in tickers_with_conf:
            ticker = ticker.upper()
            key = (ticker, theme_hint)
            if key in seen:
                continue
            seen.add(key)

            # Priority în funcție de calitatea semnalului
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
                theme=theme_hint,
                subtheme=subthemes[0] if subthemes else None,
                role=role,
                positioning=f"News: {trigger_category} ({signal_side})",
                market_cap_bucket="Unknown",
                conviction_score=0.0,
                priority_level=priority,
                horizon="Watch",
                thesis="", why_now="", why_this_name="", ai_verdict="",
                status="WATCH"
            ))

    log_info(f"[Mapper] {len(opportunities)} opportunities generated")
    return opportunities
