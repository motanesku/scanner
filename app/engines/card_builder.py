from app.models import Opportunity


def build_card(opportunity: Opportunity) -> dict:
    return {
        "ticker": opportunity.ticker,
        "company_name": opportunity.company_name,
        "theme": opportunity.theme,
        "subtheme": opportunity.subtheme,
        "role": opportunity.role,
        "positioning": opportunity.positioning,
        "conviction_score": opportunity.conviction_score,
        "priority_level": opportunity.priority_level,
        "horizon": opportunity.horizon,
        "thesis": opportunity.thesis,
        "why_now": opportunity.why_now,
        "why_this_name": opportunity.why_this_name,
        "ai_verdict": opportunity.ai_verdict,
    }


def build_cards(opportunities: list[Opportunity]) -> list[dict]:
    return [build_card(opp) for opp in opportunities]