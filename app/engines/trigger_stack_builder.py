from app.models import Opportunity
from app.collectors.insider_collector import get_mock_insider_activity
from app.collectors.earnings_collector import get_mock_earnings_schedule
from app.collectors.market_signal_collector import get_mock_market_signals


def enrich_opportunities_with_trigger_stack(opportunities: list[Opportunity]) -> list[Opportunity]:
    insider_data = get_mock_insider_activity()
    earnings_data = get_mock_earnings_schedule()
    market_data = get_mock_market_signals()

    enriched = []

    for opp in opportunities:
        trigger_stack = ["Theme Trigger", "News Trigger"]
        market_confirmation = []
        next_confirmations = []
        failure_modes = []

        # Insider
        insider = insider_data.get(opp.ticker)
        if insider and insider.get("has_insider_buy"):
            trigger_stack.append("Insider Trigger")

        # Earnings
        earnings = earnings_data.get(opp.ticker)
        if earnings:
            days = earnings.get("days_to_earnings", 999)
            if days <= 14:
                trigger_stack.append(f"Earnings Trigger ({days}d)")
                next_confirmations.append("Earnings must reinforce the active theme narrative")
            else:
                next_confirmations.append("Monitor future earnings commentary for theme confirmation")

        # Market
        market = market_data.get(opp.ticker)
        if market:
            if market.get("volume_confirmation"):
                trigger_stack.append("Market Trigger")
                market_confirmation.append("Volume Confirmation: YES")
            else:
                market_confirmation.append("Volume Confirmation: NO")

            market_confirmation.append(f"Relative Strength: {market.get('relative_strength', 'Unknown')}")
            market_confirmation.append(f"Price Structure: {market.get('price_structure', 'Unknown')}")

        # Generic next confirmations
        next_confirmations.append("Theme breadth should continue expanding across related names")
        next_confirmations.append("Follow-through price action should remain constructive")

        # Generic failure modes
        failure_modes.append("Theme may narrow back into only obvious leaders")
        failure_modes.append("Narrative may lose urgency if follow-through headlines fade")
        failure_modes.append("Market confirmation may fail to broaden")

        opp.trigger_stack = trigger_stack
        opp.trigger_count = len(trigger_stack)
        opp.market_confirmation = market_confirmation
        opp.next_confirmations = list(dict.fromkeys(next_confirmations))
        opp.failure_modes = failure_modes

        enriched.append(opp)

    return enriched
