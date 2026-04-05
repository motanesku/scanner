from collections import defaultdict
from app.models import Opportunity, ThemeCard


def build_theme_cards(opportunities: list[Opportunity]) -> list[ThemeCard]:
    grouped = defaultdict(list)

    for opp in opportunities:
        grouped[opp.theme].append(opp)

    themes = []

    for theme_name, items in grouped.items():
        top_beneficiaries = [x.ticker for x in sorted(items, key=lambda o: o.conviction_score, reverse=True)[:5]]

        avg_score = sum(x.conviction_score for x in items) / len(items)

        themes.append(
            ThemeCard(
                theme_key=theme_name.lower().replace(" ", "_"),
                theme_name=theme_name,
                subthemes=list(set([x.subtheme for x in items if x.subtheme])),
                theme_strength=round(avg_score, 2),
                narrative_strength=round(avg_score - 0.3, 2),
                market_confirmation="YES",
                priority_level="High" if avg_score >= 8 else "Medium",
                status="ACTIVE",
                why_now=f"{theme_name} is surfacing through multiple related triggers and relevant beneficiaries.",
                ai_verdict=f"{theme_name} currently looks actionable and worth active monitoring.",
                top_beneficiaries=top_beneficiaries
            )
        )

    return themes
