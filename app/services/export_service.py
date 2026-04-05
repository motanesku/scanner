import json
from app.config import OUTPUT_PATH
from app.utils.logger import log_success


def export_to_json(payload: dict):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log_success(f"Exported scan results to {OUTPUT_PATH}")