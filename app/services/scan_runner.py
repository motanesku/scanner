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
import json
from pathlib import Path
from app.config import OUTPUT_PATH

def run_scan():
    """
    Generare JSON mock minimal pentru test rapid pe mobil.
    """
    data = {
        "summary": {"total_opportunities": 2},
        "opportunities": [
            {"ticker": "NVDA", "score": 87, "catalyst": "Earnings beat", "narrative": "AI growth strong"},
            {"ticker": "AMD", "score": 81, "catalyst": "GPU release", "narrative": "High demand"}
        ],
        "themes": ["AI", "Semiconductors"]
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return data
