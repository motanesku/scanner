from app.models import Trigger, Opportunity


THEME_MAP = {
    "Copper Demand Expansion": [
        {
            "ticker": "FCX",
            "company_name": "Freeport-McMoRan",
            "role": "Direct Winner",
            "positioning": "Tier 1 Liquid Leader",
            "horizon": "Swing / Position",
            "market_cap_bucket": "Large Cap"
        },
        {
            "ticker": "SCCO",
            "company_name": "Southern Copper",
            "role": "Direct Winner",
            "positioning": "High Purity Producer",
            "horizon": "Position",
            "market_cap_bucket": "Large Cap"
        },
        {
            "ticker": "ETN",
            "company_name": "Eaton",
            "role": "Second-Order Winner",
            "positioning": "Grid / Electrical Infrastructure",
            "horizon": "Swing / Position",
            "market_cap_bucket": "Large Cap"
        },
    ],
    "Cybersecurity Resilience": [
        {
            "ticker": "PANW",
            "company_name": "Palo Alto Networks",
            "role": "Direct Winner",
            "positioning": "Large Cap Security Leader",
            "horizon": "Swing / Position",
            "market_cap_bucket": "Large Cap"
        },
        {
            "ticker": "CRWD",
            "company_name": "CrowdStrike",
            "role": "Direct Winner",
            "positioning": "Cloud Security Leader",
            "horizon": "Swing / Position",
            "market_cap_bucket": "Large Cap"
        },
        {
            "ticker": "ZS",
            "company_name": "Zscaler",
            "role": "Second-Order Winner",
            "positioning": "Zero Trust Exposure",
            "horizon": "Swing",
            "market_cap_bucket": "Large Cap"
        },
    ]
}


def map_triggers_to_opportunities(triggers: list[Trigger]) -> list[Opportunity]:
    opportunities = []

    for trigger in triggers:
        mapped = THEME_MAP.get(trigger.theme_hint, [])

        for item in mapped:
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
