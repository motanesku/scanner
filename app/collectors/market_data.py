# File: app/collectors/market_data.py

import requests
from app.config import POLYGON_API_KEY


def collect_market_data(tickers=None):
    """
    Market data via Polygon previous day bar.
    Stabil pentru un număr mic de tickere deja identificate.
    """

    if tickers is None:
        tickers = ["SPY"]

    results = {}

    if not POLYGON_API_KEY:
        for ticker in tickers:
            results[ticker] = {
                "ticker": ticker,
                "price": None,
                "previous_close": None,
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None,
                "avg_volume_5d": None,
                "source": "polygon",
                "status": "error",
                "error": "Missing POLYGON_API_KEY"
            }
        return results

    headers = {
        "Authorization": f"Bearer {POLYGON_API_KEY}"
    }

    for ticker in tickers:
        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()

            results_list = data.get("results", [])
            if not results_list:
                results[ticker] = {
                    "ticker": ticker,
                    "price": None,
                    "previous_close": None,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume": None,
                    "avg_volume_5d": None,
                    "source": "polygon",
                    "status": "no_data"
                }
                continue

            bar = results_list[0]

            close_price = _safe_float(bar.get("c"))
            results[ticker] = {
                "ticker": ticker,
                "price": close_price,
                "previous_close": close_price,
                "open": _safe_float(bar.get("o")),
                "high": _safe_float(bar.get("h")),
                "low": _safe_float(bar.get("l")),
                "close": close_price,
                "volume": _safe_int(bar.get("v")),
                "avg_volume_5d": _safe_int(bar.get("v")),
                "source": "polygon",
                "status": "ok"
            }

        except Exception as e:
            results[ticker] = {
                "ticker": ticker,
                "price": None,
                "previous_close": None,
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": None,
                "avg_volume_5d": None,
                "source": "polygon",
                "status": "error",
                "error": str(e)
            }

    return results


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value):
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None
