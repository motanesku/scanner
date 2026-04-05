from app.models import Opportunity


def score_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    scored = []

    for opp in opportunities:
        if opp.role == "Direct Winner":
            opp.conviction_score = 8.7
            opp.priority_level = "High"
        else:
            opp.conviction_score = 7.5
            opp.priority_level = "Medium"

        opp.thesis = (
            f"{opp.company_name} appears relevant as a {opp.role.lower()} "
            f"within the {opp.theme} theme."
        )

        opp.why_now = (
            f"The {opp.theme} narrative is active and currently showing "
            f"cross-market relevance with growing investor attention."
        )

        opp.why_this_name = (
            f"{opp.company_name} has meaningful exposure to the {opp.theme} theme "
            f"through its positioning as {opp.positioning}."
        )

        opp.ai_verdict = (
            f"{opp.ticker} is currently a useful watchlist candidate inside "
            f"the {opp.theme} opportunity set, especially as a {opp.role.lower()}."
        )

        scored.append(opp)

    return scored
