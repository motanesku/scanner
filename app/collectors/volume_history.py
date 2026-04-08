# File: app/collectors/volume_history.py
#
# Volume history via Cloudflare D1 (prin Worker).
# Persistent cross-deploy — nu se pierde la Railway redeploy.
#
# Workflow:
# 1. După fiecare scan: trimite volumele zilei la Worker → D1
# 2. La scan următor: citește history din Worker → detectează spikes

import os
import time
import requests
from app.utils.logger import log_info, log_warn, log_error

WORKER_URL = os.environ.get(
    "WORKER_URL",
    "https://portfolio-api.danut-fagadau.workers.dev"
)

# Nu avem nevoie de auth pentru volume history — e date publice
HEADERS = {"Content-Type": "application/json"}

# Minim zile pentru a calcula media robustă
MIN_DAYS_FOR_AVG = 5


def save_volume_history(grouped_data: dict, date_str: str) -> bool:
    """
    Trimite volumele zilei la Worker → D1.

    grouped_data = {ticker: bar} din Polygon grouped daily.
    bar = {"v": volume, "c": close, "vw": vwap, ...}

    Trimite doar tickerele cu volum valid și daily turnover >= $1M
    (filtrăm garbage înainte de a trimite — nu supraîncărcăm D1).
    """
    if not grouped_data:
        return False

    # Filtrăm și compactăm — trimitem doar ce e relevant
    tickers_to_save = {}
    for ticker, bar in grouped_data.items():
        volume = bar.get("v", 0)
        close = bar.get("c", 0)
        vwap = bar.get("vw", 0)

        if not volume or not close:
            continue

        # Filtrăm micro-cap evident
        if price_x_vol := close * volume:
            if price_x_vol < 1_000_000:  # sub $1M zilnic — nu ne interesează
                continue

        tickers_to_save[ticker] = {
            "v": int(volume),
            "c": round(close, 4),
            "vw": round(vwap, 4) if vwap else None,
        }

    if not tickers_to_save:
        log_warn("[VolumeHistory] No valid tickers to save")
        return False

    log_info(f"[VolumeHistory] Saving {len(tickers_to_save)} tickers for {date_str}...")

    try:
        r = requests.post(
            f"{WORKER_URL}/api/volume-history",
            json={"date": date_str, "tickers": tickers_to_save},
            headers=HEADERS,
            timeout=30,
        )
        if r.ok:
            data = r.json()
            log_info(f"[VolumeHistory] Saved {data.get('saved', 0)} tickers to D1")
            return True
        else:
            log_error(f"[VolumeHistory] Worker error: {r.status_code} — {r.text[:100]}")
            return False
    except Exception as e:
        log_error(f"[VolumeHistory] Save failed: {e}")
        return False


def get_volume_history(tickers: list[str], days: int = 20) -> dict[str, list[dict]]:
    """
    Citește history de volum din D1 via Worker.

    Returnează:
    {
        "NVDA": [
            {"date": "2026-04-07", "volume": 45123456, "close": 177.64, "vwap": 176.5},
            ...
        ],
        ...
    }
    """
    if not tickers:
        return {}

    # Trimitem în chunks de max 50 tickers (URL length limit)
    CHUNK = 50
    result = {}

    for i in range(0, len(tickers), CHUNK):
        chunk = tickers[i:i + CHUNK]
        try:
            r = requests.get(
                f"{WORKER_URL}/api/volume-history",
                params={"tickers": ",".join(chunk), "days": days},
                headers=HEADERS,
                timeout=15,
            )
            if r.ok:
                data = r.json()
                result.update(data.get("data", {}))
            else:
                log_warn(f"[VolumeHistory] Get error: {r.status_code}")
        except Exception as e:
            log_error(f"[VolumeHistory] Get failed: {e}")

    return result


def get_avg_volume(ticker: str, history: dict) -> float | None:
    """Calculează media volumului din history pentru un ticker."""
    entries = history.get(ticker, [])
    if len(entries) < MIN_DAYS_FOR_AVG:
        return None
    volumes = [e["volume"] for e in entries if e.get("volume")]
    if not volumes:
        return None
    return sum(volumes) / len(volumes)


def get_volume_spike_ratio(ticker: str, current_volume: int, history: dict) -> float | None:
    """
    Returnează ratio = current_volume / avg_volume.
    2.0 = volum dublu față de medie = spike semnificativ.
    """
    avg = get_avg_volume(ticker, history)
    if avg is None or avg <= 0:
        return None
    return current_volume / avg
