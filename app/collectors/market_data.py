# File: app/collectors/market_data.py

import requests
import time
from app.config import POLYGON_API_KEY


def collect_market_data(tickers=None):
    """
    Market data via Polygon previous day bar.
    - nu blochează scannerul dacă un ticker dă 429
    - retry scurt
    - fallback neutru dacă nu merge
    """

    if tickers is None:
        tickers = ["SPY"]

    results = {}

    if not POLYGON_API_KEY:
        for ticker in tickers:
            results[ticker] = _empty_result(
                ticker=ticker,
                error="Missing POLYGON_API_KEY"
            )
        return results

    headers = {
        "Authorization": f"Bearer {POLYGON_API_KEY}"
    }

    for ticker in tickers:
        results[ticker] = _fetch_prev_bar_with_retry(ticker, headers)

        # mic delay ca să reducem riscul de rate limit
        time.sleep(0.25)

    return results


def _fetch_prev_bar_with_retry(ticker, headers, retries=2):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"

    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20)

            if response.status_code == 429:
                if attempt < retries:
                    time.sleep(1 + attempt)
                    continue
                return _empty_result(
                    ticker=ticker,
                    error=f"429 Too Many Requests for {ticker}"
                )

            response.raise_for_status()
            data = response.json()

            results_list = data.get("results", [])
            if not results_list:
                return _empty_result(
                    ticker=ticker,
                    status="no_data",
                    error=f"No Polygon data for {ticker}"
                )

            bar = results_list[0]

            close_price = _safe_float(bar.get("c"))
            open_price = _safe_float(bar.get("o"))
            high_price = _safe_float(bar.get("h"))
            low_price = _safe_float(bar.get("l"))
            volume = _safe_int(bar.get("v"))

            return {
                "ticker": ticker,
                "price": close_price,
                "previous_close": close_price,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "avg_volume_5d": volume,
                "source": "polygon",
                "status": "ok"
            }

        except Exception as e:
            if attempt < retries:
                time.sleep(1 + attempt)
                continue

            return _empty_result(
                ticker=ticker,
                error=str(e)
            )

    return _empty_result(
        ticker=ticker,
        error=f"Unknown Polygon error for {ticker}"
    )


def _empty_result(ticker, status="error", error=None):
    payload = {
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
        "status": status
    }

    if error:
        payload["error"] = error

    return payload


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
