from app.models import Opportunity


def score_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    scored = []

    for opp in opportunities:
        base_score = 6.5

        # Role
        if opp.role == "Direct Winner":
            base_score += 1.0
        elif opp.role == "Second-Order Winner":
            base_score += 0.5

        # Trigger stack
        base_score += min(1.5, opp.trigger_count * 0.35)

        # Market confirmation boost
        if any("Volume Confirmation: YES" in x for x in opp.market_confirmation):
            base_score += 0.4

        if any("Relative Strength: Strong" in x for x in opp.market_confirmation):
            base_score += 0.4
        elif any("Relative Strength: Improving" in x for x in opp.market_confirmation):
            base_score += 0.2

        opp.conviction_score = round(min(9.8, base_score), 2)

        if opp.conviction_score >= 8.5:
            opp.priority_level = "High"
        elif opp.conviction_score >= 7.5:
            opp.priority_level = "Medium"
        else:
            opp.priority_level = "Low"

        opp.thesis = (
            f"{opp.company_name} appears relevant as a {opp.role.lower()} "
            f"within the {opp.theme} theme, with {opp.trigger_count} active supporting triggers."
        )

        opp.why_now = (
            f"{opp.theme} is active, and {opp.ticker} currently shows a meaningful trigger stack "
            f"that improves the quality of the opportunity."
        )

        opp.why_this_name = (
            f"{opp.company_name} has meaningful exposure to the {opp.theme} theme "
            f"through its positioning as {opp.positioning}, making it a relevant expression of the idea."
        )

        opp.ai_verdict = (
            f"{opp.ticker} currently looks like a {opp.priority_level.lower()}-priority watchlist candidate "
            f"inside the {opp.theme} theme, especially given its current trigger stack."
        )

        scored.append(opp)

    return scored
