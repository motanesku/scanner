from datetime import datetime
from app.models import Opportunity, ThemeCard, DailyReport


def build_daily_report(opportunities: list[Opportunity], themes: list[ThemeCard]) -> DailyReport:
    top_themes = [t.theme_name for t in sorted(themes, key=lambda x: x.theme_strength, reverse=True)[:5]]
    top_tickers = [o.ticker for o in sorted(opportunities, key=lambda x: x.conviction_score, reverse=True)[:8]]

    laggards = [o.ticker for o in opportunities if o.role == "Second-Order Winner"][:5]

    risk_flags = [
        "Narratives may narrow into obvious leaders only",
        "Some themes may already be partially priced in",
        "Cross-theme confirmation still needs expansion"
    ]

    actionable_focus = [
        "Track strongest direct winners first",
        "Watch second-order laggards for catch-up moves",
        "Monitor whether theme confirmation broadens or fades"
    ]

    market_take = (
        "Current opportunity set favors theme-linked infrastructure, "
        "resilient enterprise spend, and second-order beneficiaries rather than only obvious crowded leaders."
    )

    return DailyReport(
        report_date=datetime.utcnow().strftime("%Y-%m-%d"),
        top_themes=top_themes,
        top_tickers=top_tickers,
        laggards=laggards,
        risk_flags=risk_flags,
        market_take=market_take,
        actionable_focus=actionable_focus
    )
