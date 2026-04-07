# File: app/engines/trigger_stack_builder.py
#
# Îmbogățește oportunitățile cu trigger stack real:
# - Insider buying real din SEC EDGAR Form 4
# - Earnings calendar real din Yahoo Finance
# - Market signals din Polygon

from app.models import Opportunity
from app.collectors.insider_collector import collect_insider_triggers
from app.collectors.earnings_collector import get_earnings_calendar
from app.collectors.market_signal_collector import get_mock_market_signals
from app.utils.logger import log_info


def enrich_opportunities_with_trigger_stack(
    opportunities: list[Opportunity],
    insider_triggers: list[dict] | None = None
) -> list[Opportunity]:
    """
    insider_triggers: lista returnată de collect_insider_triggers()
    Dacă nu e pasată, o colectăm intern (fallback).
    """

    # Dacă nu s-au pasat extern, colectăm acum
    # (de obicei se pasează din scan_runner pentru a evita duplicate calls)
    if insider_triggers is None:
        log_info("[TriggerStack] Collecting insider triggers internally...")
        insider_triggers = collect_insider_triggers(days_back=2)

    # Index rapid: ticker → trigger data
    insider_index = {}
    for t in insider_triggers:
        ticker = t.get("ticker", "").upper()
        if ticker not in insider_index:
            insider_index[ticker] = t
        else:
            # Păstrează cel mai mare buy
            if t.get("total_value", 0) > insider_index[ticker].get("total_value", 0):
                insider_index[ticker] = t

    # Earnings calendar real
    earnings_calendar = get_earnings_calendar()

    # Market signals (Polygon — rămâne mock până implementăm volume spike real)
    market_signals = get_mock_market_signals()

    enriched = []

    for opp in opportunities:
        ticker = opp.ticker.upper()
        trigger_stack = ["Theme Trigger"]
        market_confirmation = []
        next_confirmations = []
        failure_modes = []

        # ── Insider Buy (Tier 1 Direct) ───────────────────────────────────
        insider = insider_index.get(ticker)
        if insider and insider.get("transaction_type") == "P":
            value = insider.get("total_value", 0)
            name = insider.get("insider_name", "Insider")
            role = insider.get("insider_role", "")
            label = f"Insider Buy — {role}: ${value:,.0f}" if role else f"Insider Buy — ${value:,.0f}"
            trigger_stack.append(label)
            next_confirmations.append(
                f"Monitor follow-through after {name}'s purchase — insider conviction signal"
            )

        # ── Earnings Calendar (Tier 1 Catalyst) ──────────────────────────
        earnings = earnings_calendar.get(ticker)
        if earnings:
            days = earnings.get("days_to_earnings", 999)
            if days is not None and days <= 14:
                trigger_stack.append(f"Earnings in {days}d")
                next_confirmations.append(
                    "Earnings must reinforce theme narrative — beat + raised guidance ideal"
                )
            elif days is not None and days <= 30:
                next_confirmations.append(
                    f"Earnings in {days} days — monitor for pre-earnings setup"
                )

        # ── Market Signals (Tier 3 Confirmation) ─────────────────────────
        market = market_signals.get(ticker)
        if market:
            vol_conf = market.get("volume_confirmation", False)
            rs = market.get("relative_strength", "Neutral")
            structure = market.get("price_structure", "Unknown")

            if vol_conf:
                trigger_stack.append("Volume Confirmation")
                market_confirmation.append("Volume: YES")
            else:
                market_confirmation.append("Volume: NO")

            market_confirmation.append(f"RS: {rs}")
            market_confirmation.append(f"Structure: {structure}")

            if rs in ("Strong", "Improving"):
                next_confirmations.append(
                    "Relative strength should hold or expand vs S&P500"
                )

        # ── Failure Modes ─────────────────────────────────────────────────
        failure_modes = [
            "Theme may narrow back into obvious leaders only",
            "Narrative loses urgency if follow-through headlines fade",
            "Market confirmation fails to broaden across sector peers",
        ]

        if insider:
            failure_modes.append("Insider buy may be isolated — watch for peer confirmation")

        if any("Earnings" in t for t in trigger_stack):
            failure_modes.append("Earnings fail to confirm or guide lower")

        # ── Generic confirmations ─────────────────────────────────────────
        next_confirmations.append(
            "Theme breadth should continue expanding across related names"
        )
        next_confirmations.append(
            "Follow-through price action should remain constructive"
        )

        opp.trigger_stack = trigger_stack
        opp.trigger_count = len(trigger_stack)
        opp.market_confirmation = market_confirmation
        opp.next_confirmations = list(dict.fromkeys(next_confirmations))  # dedup
        opp.failure_modes = failure_modes

        enriched.append(opp)

    return enriched
