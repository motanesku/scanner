# File: app/services/scan_runner.py

import json
from app.config import OUTPUT_PATH


def run_scan():
    """
    Scanner minimal stabil pentru Railway / mobil.
    Generează output valid și menține API-ul funcțional.
    """

    result = {
        "summary": {
            "total_opportunities": 3,
            "scan_status": "ok"
        },
        "opportunities": [
            {
                "ticker": "NVDA",
                "score": 87,
                "signal": "BUY",
                "catalyst": "AI demand acceleration",
                "narrative": "AI infrastructure expansion remains strong",
                "entry": "420-430",
                "target": "480"
            },
            {
                "ticker": "AMD",
                "score": 81,
                "signal": "WATCH",
                "catalyst": "GPU product cycle",
                "narrative": "Semiconductor momentum supported by AI compute demand",
                "entry": "108-112",
                "target": "130"
            },
            {
                "ticker": "CRDO",
                "score": 84,
                "signal": "BUY",
                "catalyst": "Networking / datacenter demand",
                "narrative": "AI infra second-order beneficiary",
                "entry": "38-40",
                "target": "48"
            }
        ],
        "themes": [
            {
                "theme": "AI Infrastructure",
                "strength": 91,
                "tickers": ["NVDA", "AMD", "CRDO"]
            },
            {
                "theme": "Semiconductors",
                "strength": 84,
                "tickers": ["NVDA", "AMD"]
            }
        ],
        "daily_report": {
            "headline": "AI infrastructure remains the strongest active market narrative.",
            "focus": [
                "Watch second-order semiconductor beneficiaries",
                "Track earnings proximity and volume confirmation",
                "Monitor AI capex and hyperscaler commentary"
            ]
        }
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result
