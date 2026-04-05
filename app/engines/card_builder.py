from app.models import Opportunity, ThemeCard, DailyReport


def build_opportunity_card(opportunity: Opportunity) -> dict:
    return {
        "ticker": opportunity.ticker,
        "company_name": opportunity.company_name,
        "theme": opportunity.theme,
        "subtheme": opportunity.subtheme,
        "role": opportunity.role,
        "positioning": opportunity.positioning,
        "market_cap_bucket": opportunity.market_cap_bucket,
        "conviction_score": opportunity.conviction_score,
        "priority_level": opportunity.priority_level,
        "horizon": opportunity.horizon,
        "thesis": opportunity.thesis,
        "why_now": opportunity.why_now,
        "why_this_name": opportunity.why_this_name,
        "ai_verdict": opportunity.ai_verdict,
        "status": opportunity.status,
        "trigger_stack": opportunity.trigger_stack,
        "trigger_count": opportunity.trigger_count,
        "market_confirmation": opportunity.market_confirmation,
        "next_confirmations": opportunity.next_confirmations,
        "failure_modes": opportunity.failure_modes,
    }


def build_theme_card(theme: ThemeCard) -> dict:
    return theme.model_dump()


def build_daily_report_card(report: DailyReport) -> dict:
    return report.model_dump()


def build_opportunity_cards(opportunities: list[Opportunity]) -> list[dict]:
    return [build_opportunity_card(opp) for opp in opportunities]


def build_theme_cards_payload(themes: list[ThemeCard]) -> list[dict]:
    return [build_theme_card(theme) for theme in themes]
