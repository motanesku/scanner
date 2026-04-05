from app.collectors.news_collector import collect_news_triggers
from app.engines.trigger_engine import classify_triggers
from app.engines.theme_mapper import map_triggers_to_opportunities
from app.engines.trigger_stack_builder import enrich_opportunities_with_trigger_stack
from app.engines.opportunity_scorer import score_opportunities
from app.engines.theme_builder import build_theme_cards
from app.engines.daily_report_builder import build_daily_report
from app.engines.card_builder import (
    build_opportunity_cards,
    build_theme_cards_payload,
    build_daily_report_card
)
from app.db import save_run, save_opportunities, save_themes, save_daily_report


def run_scan() -> dict:
    triggers = collect_news_triggers()
    classified = classify_triggers(triggers)
    mapped = map_triggers_to_opportunities(classified)
    enriched = enrich_opportunities_with_trigger_stack(mapped)
    scored = score_opportunities(enriched)
    themes = build_theme_cards(scored)
    daily_report = build_daily_report(scored, themes)

    save_run("daily", f"Scan completed with {len(scored)} opportunities and {len(themes)} themes.")
    save_opportunities(scored)
    save_themes(themes)
    save_daily_report(daily_report)

    summary = {
        "run_type": "daily",
        "trigger_count": len(classified),
        "opportunity_count": len(scored),
        "theme_count": len(themes),
        "top_themes": [t.theme_name for t in themes]
    }

    return {
        "summary": summary,
        "triggers": [t.model_dump() for t in classified],
        "themes": build_theme_cards_payload(themes),
        "opportunities": build_opportunity_cards(scored),
        "daily_report": build_daily_report_card(daily_report)
    }
