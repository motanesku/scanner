# File: app/collectors/volume_history.py
#
# Acumulează volume history din Polygon grouped daily.
# Salvează zilnic în data/volume_history.json.
# După 20 zile avem media robustă per ticker — zero requests extra.

import json
import time
from pathlib import Path
from datetime import datetime, timezone
from app.utils.logger import log_info, log_warn, log_error

HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "volume_history.json"
HISTORY_PATH.parent.mkdir(exist_ok=True)

# Câte zile păstrăm în history
MAX_HISTORY_DAYS = 30
# Minim zile pentru a calcula media
MIN_DAYS_FOR_AVG = 5


def load_history() -> dict:
    """
    Încarcă history din fișier local.

    Format:
    {
        "NVDA": [
            {"date": "2026-04-07", "volume": 45123456},
            {"date": "2026-04-08", "volume": 38901234},
            ...
        ],
        ...
    }
    """
    if not HISTORY_PATH.exists():
        return {}
    try:
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        log_warn(f"[VolumeHistory] Load error: {e}")
        return {}


def save_history(history: dict) -> None:
    """Salvează history în fișier local."""
    try:
        with open(HISTORY_PATH, "w") as f:
            json.dump(history, f, separators=(",", ":"))
    except Exception as e:
        log_error(f"[VolumeHistory] Save error: {e}")


def update_history(grouped_data: dict, date_str: str) -> dict:
    """
    Adaugă datele din ziua curentă în history.
    grouped_data = {ticker: bar_dict} din Polygon grouped daily.
    Returnează history-ul actualizat.
    """
    history = load_history()
    added = 0

    for ticker, bar in grouped_data.items():
        volume = bar.get("v")
        if not volume or volume <= 0:
            continue

        if ticker not in history:
            history[ticker] = []

        # Verifică dacă ziua asta e deja în history
        existing_dates = {entry["date"] for entry in history[ticker]}
        if date_str in existing_dates:
            continue

        history[ticker].append({
            "date": date_str,
            "volume": int(volume),
            "close": bar.get("c"),
            "vwap": bar.get("vw"),
        })

        # Păstrează doar ultimele MAX_HISTORY_DAYS zile
        if len(history[ticker]) > MAX_HISTORY_DAYS:
            history[ticker] = sorted(
                history[ticker],
                key=lambda x: x["date"],
                reverse=True
            )[:MAX_HISTORY_DAYS]

        added += 1

    log_info(f"[VolumeHistory] Updated {added} tickers for {date_str}")
    save_history(history)
    return history


def get_avg_volume(ticker: str, history: dict | None = None) -> float | None:
    """
    Returnează media volumului pe ultimele N zile pentru un ticker.
    None dacă nu avem suficiente date.
    """
    if history is None:
        history = load_history()

    entries = history.get(ticker.upper(), [])
    if len(entries) < MIN_DAYS_FOR_AVG:
        return None

    volumes = [e["volume"] for e in entries if e.get("volume")]
    if not volumes:
        return None

    return sum(volumes) / len(volumes)


def get_volume_spike_ratio(ticker: str, current_volume: int, history: dict | None = None) -> float | None:
    """
    Returnează ratio = current_volume / avg_volume.
    2.0 = volum dublu față de medie = spike semnificativ.
    None dacă nu avem suficiente date.
    """
    avg = get_avg_volume(ticker, history)
    if avg is None or avg <= 0:
        return None
    return current_volume / avg


def get_history_stats() -> dict:
    """Status history pentru debug."""
    history = load_history()
    tickers_with_data = {t: len(v) for t, v in history.items() if v}
    return {
        "total_tickers": len(tickers_with_data),
        "tickers_with_20d": sum(1 for v in tickers_with_data.values() if v >= 20),
        "tickers_with_5d": sum(1 for v in tickers_with_data.values() if v >= 5),
        "sample": dict(list(tickers_with_data.items())[:5])
    }
