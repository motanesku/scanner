from app.models import Trigger, Opportunity
from app.data.theme_registry import THEME_REGISTRY


def map_triggers_to_opportunities(triggers: list[Trigger]) -> list[Opportunity]:
    opportunities = []
    seen = set()

    for trigger in triggers:
        theme_data = THEME_REGISTRY.get(trigger.theme_hint, {})
        mapped = theme_data.get("companies", [])

        for item in mapped:
            unique_key = (item["ticker"], trigger.theme_hint)

            if unique_key in seen:
                continue

            seen.add(unique_key)

            opportunities.append(
                Opportunity(
                    ticker=item["ticker"],
                    company_name=item["company_name"],
                    theme=trigger.theme_hint,
                    subtheme=trigger.subthemes[0] if trigger.subthemes else None,
                    role=item["role"],
                    positioning=item["positioning"],
                    market_cap_bucket=item["market_cap_bucket"],
                    conviction_score=0.0,
                    priority_level="Medium",
                    horizon=item["horizon"],
                    thesis="",
                    why_now="",
                    why_this_name="",
                    ai_verdict="",
                    status="ACTIVE WATCH"
                )
            )

    return opportunities
