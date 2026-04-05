from app.collectors.news_collector import collect_news_triggers
from app.engines.trigger_engine import classify_triggers
from app.engines.theme_mapper import map_triggers_to_opportunities
from app.engines.opportunity_scorer import score_opportunities
from app.engines.card_builder import build_cards


def run_scan() -> dict:
    triggers = collect_news_triggers()
    classified = classify_triggers(triggers)
    mapped = map_triggers_to_opportunities(classified)
    scored = score_opportunities(mapped)
    cards = build_cards(scored)

    summary = {
        "run_type": "daily",
        "trigger_count": len(classified),
        "opportunity_count": len(scored),
        "top_themes": list(set([t.theme_hint for t in classified]))
    }

    return {
        "summary": summary,
        "triggers": [t.model_dump() for t in classified],
        "cards": cards
    }