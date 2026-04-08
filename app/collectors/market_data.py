# File: app/collectors/market_data.py
#
# Market data via Polygon grouped daily endpoint.
# UN SINGUR REQUEST pentru toată piața US în loc de N requests per ticker.
#
# Endpoint: GET /v2/aggs/grouped/locale/us/market/stocks/{date}
# Returnează OHLCV pentru toate tickerele active din ziua respectivă.
# ~12,000 tickers per request, fără rate limit issues.

import requests
import time
from datetime import datetime, timezone, timedelta
from app.config import POLYGON_API_KEY
from app.utils.logger import log_info, log_warn, log_error

# Cache în memorie — evităm re-descărcarea în același scan
_grouped_cache: dict = {}
_grouped_cache_date: str = ""


def collect_market_data(tickers: list[str] | None = None) -> dict:
    """
    Returnează market data pentru tickerele cerute.

    Folosește Polygon grouped daily — descarcă toată piața o dată
    și extrage doar tickerele relevante.

    Returnează:
    {
        "NVDA": {
            "ticker": "NVDA",
            "price": 177.64,
            "previous_close": ...,
            "open": ..., "high": ..., "low": ..., "close": ...,
            "volume": ...,
            "avg_volume_5d": ...,  # same as volume (prev day)
            "vwap": ...,           # volume weighted average price
            "transactions": ...,   # număr tranzacții
            "source": "polygon_grouped",
            "status": "ok"
        },
        ...
    }
    """
    if not tickers:
        return {}

    if not POLYGON_API_KEY:
        return {t: _empty_result(t, error="Missing POLYGON_API_KEY") for t in tickers}

    # Descarcă grouped data (cu cache)
    grouped = _get_grouped_daily()

    results = {}
    for ticker in tickers:
        ticker_upper = ticker.upper()
        bar = grouped.get(ticker_upper)

        if bar:
            results[ticker_upper] = {
                "ticker": ticker_upper,
                "price": bar.get("c"),           # close
                "previous_close": bar.get("c"),  # same day close ca referință
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar.get("c"),
                "volume": int(bar.get("v", 0)),
                "avg_volume_5d": int(bar.get("v", 0)),  # aproximare cu ziua curentă
                "vwap": bar.get("vw"),
                "transactions": bar.get("n"),
                "source": "polygon_grouped",
                "status": "ok"
            }
        else:
            results[ticker_upper] = _empty_result(
                ticker_upper,
                status="no_data",
                error=f"No data for {ticker_upper} in grouped daily"
            )

    return results


def _get_grouped_daily() -> dict:
    """
    Descarcă sau returnează din cache grouped daily data.
    Cache valid pentru întreaga zi curentă.
    """
    global _grouped_cache, _grouped_cache_date

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Returnează din cache dacă e aceeași zi
    if _grouped_cache_date == today and _grouped_cache:
        log_info(f"[Market] Using cached grouped daily ({len(_grouped_cache)} tickers)")
        return _grouped_cache

    # Determină data pentru care cerem date
    # Polygon grouped daily returnează date pentru ziua de tranzacționare anterioară
    date_str = _get_last_trading_day()

    log_info(f"[Market] Fetching Polygon grouped daily for {date_str}...")

    url = f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date_str}"
    params = {
        "apiKey": POLYGON_API_KEY,
        "adjusted": "true",
        "include_otc": "false",  # excludem OTC
    }

    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                wait = 10 * (attempt + 1)
                log_warn(f"[Market] Polygon grouped 429 — waiting {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue

            if not response.ok:
                log_error(f"[Market] Polygon grouped error: {response.status_code}")
                return {}

            data = response.json()
            results = data.get("results", [])

            if not results:
                log_warn(f"[Market] No results for {date_str} — trying previous day")
                date_str = _get_last_trading_day(skip_days=2)
                continue

            # Construiește index ticker → bar
            grouped = {bar["T"]: bar for bar in results if "T" in bar}

            log_info(f"[Market] Grouped daily loaded: {len(grouped)} tickers for {date_str}")

            # Salvează în cache
            _grouped_cache = grouped
            _grouped_cache_date = today

            return grouped

        except Exception as e:
            log_error(f"[Market] Grouped daily error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(3)
            continue

    log_error("[Market] All attempts failed for grouped daily")
    return {}


def _get_last_trading_day(skip_days: int = 1) -> str:
    """
    Returnează ultima zi de tranzacționare (exclude weekend).
    skip_days=1 → ieri, skip_days=2 → alaltăieri etc.
    """
    now = datetime.now(timezone.utc)
    candidate = now - timedelta(days=skip_days)

    # Skip weekend
    attempts = 0
    while candidate.weekday() >= 5 and attempts < 5:  # 5=Sat, 6=Sun
        candidate -= timedelta(days=1)
        attempts += 1

    return candidate.strftime("%Y-%m-%d")


def preload_market_data() -> int:
    """
    Pre-încarcă grouped daily data la startup.
    Apelat din scan_runner înainte de pipeline.
    Returnează numărul de tickers disponibili.
    """
    grouped = _get_grouped_daily()
    return len(grouped)


def _empty_result(ticker: str, status: str = "error", error: str = "") -> dict:
    result = {
        "ticker": ticker,
        "price": None,
        "previous_close": None,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "volume": None,
        "avg_volume_5d": None,
        "vwap": None,
        "transactions": None,
        "source": "polygon_grouped",
        "status": status,
    }
    if error:
        result["error"] = error
    return result
