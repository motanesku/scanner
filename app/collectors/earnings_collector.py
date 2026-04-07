# File: app/collectors/earnings_collector.py
#
# Sursa: Nasdaq.com public earnings calendar API
# Nu necesită API key, returnează earnings pentru orice zi
# URL: https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD

import requests
import time
from datetime import datetime, timezone, timedelta
from app.utils.logger import log_info, log_warn, log_error

NASDAQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/market-activity/earnings",
}


def get_earnings_calendar(
    extra_tickers: list[str] | None = None,
    window_days: int = 14
) -> dict:
    """
    Returnează dict: { "TICKER": { "days_to_earnings": N, "earnings_date": "YYYY-MM-DD" } }
    Scanează zilele următoare și colectează toate earnings.
    window_days: câte zile în viitor să scaneze
    """
    log_info(f"[Earnings] Scanning Nasdaq earnings calendar ({window_days} days)...")

    all_earnings = {}
    now = datetime.now(timezone.utc)

    for day_offset in range(0, window_days + 1):
        target_date = now + timedelta(days=day_offset)

        # Skip weekend
        if target_date.weekday() >= 5:
            continue

        date_str = target_date.strftime("%Y-%m-%d")
        daily = _fetch_nasdaq_earnings_for_date(date_str)

        for ticker, data in daily.items():
            if ticker not in all_earnings:
                all_earnings[ticker] = data

        if day_offset < window_days:
            time.sleep(0.3)

    log_info(f"[Earnings] Found {len(all_earnings)} tickers with upcoming earnings.")
    return all_earnings


def _fetch_nasdaq_earnings_for_date(date_str: str) -> dict:
    """
    Fetch earnings pentru o zi specifică din Nasdaq calendar.
    """
    url = "https://api.nasdaq.com/api/calendar/earnings"
    params = {"date": date_str}

    try:
        response = requests.get(
            url,
            headers=NASDAQ_HEADERS,
            params=params,
            timeout=15
        )

        if response.status_code == 429:
            log_warn(f"[Earnings] Nasdaq rate limit for {date_str} — waiting 3s...")
            time.sleep(3)
            response = requests.get(url, headers=NASDAQ_HEADERS, params=params, timeout=15)

        if not response.ok:
            log_warn(f"[Earnings] Nasdaq returned {response.status_code} for {date_str}")
            return {}

        data = response.json()
        rows = data.get("data", {}).get("rows", [])

        if not rows:
            return {}

        now = datetime.now(timezone.utc)
        results = {}

        for row in rows:
            ticker = (row.get("symbol") or "").strip().upper()
            if not ticker:
                continue

            try:
                earnings_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_to_earnings = max(0, (earnings_dt - now).days)
            except Exception:
                continue

            results[ticker] = {
                "days_to_earnings": days_to_earnings,
                "earnings_date": date_str,
                "company_name": row.get("name", ticker),
                "eps_estimate": row.get("epsForecast", ""),
                "time": row.get("time", ""),
                "source": "nasdaq_calendar"
            }

        return results

    except Exception as e:
        log_warn(f"[Earnings] Nasdaq fetch error for {date_str}: {e}")
        return {}


def get_earnings_for_ticker(ticker: str) -> dict | None:
    """
    Helper: returnează earnings info pentru un singur ticker.
    """
    results = get_earnings_calendar(window_days=21)
    return results.get(ticker.upper())
