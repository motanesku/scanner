import json
from pathlib import Path
from app.config import OUTPUT_PATH

def run_scan():
    # --- MOCK DATA ---
    result = {
        "summary": {"total_opportunities": 2},
        "opportunities": [
            {
                "ticker": "NVDA",
                "score": 87,
                "catalyst": "Earnings beat",
                "narrative": "AI growth strong",
                "entry": 425,
                "target": 480
            },
            {
                "ticker": "AMD",
                "score": 81,
                "catalyst": "New GPU release",
                "narrative": "Demand high",
                "entry": 110,
                "target": 135
            }
        ],
        "themes": ["AI", "Semiconductors"]
    }

    # Scrie JSON-ul în OUTPUT_PATH
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result
