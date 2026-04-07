# File: app/collectors/earnings_collector.py
#
# Colectează earnings calendar real din Yahoo Finance.
# Fără API key — folosește endpoint-ul public v7/finance/quote
# care returnează earningsTimestamp per ticker.
#
# Strategie:
# 1. Avem o listă de ~150 tickere relevante (universe)
# 2. Facem batch requests la Yahoo Finance (max 10 tickere per request)
# 3. Extragem earningsTimestamp și calculăm days_to_earnings
# 4. Returnăm doar tickerele cu earnings în fereastra 3-21 zile
#
# Earnings în 3-7 zile  → Tier 1 catalyst (setup pre-earnings)
# Earnings în 8-14 zile → Tier 2 catalyst (planificare)
# Earnings în 15-21 zile → informativ

import requests
import time
from datetime import datetime, timezone
from app.utils.logger import log_info, log_warn, log_error

# Universe de tickere pentru earnings scan
# Acesta este universul de bază — Scanner-ul adaugă dinamic tickerele
# identificate din triggere (Form 4, news, etc.)
EARNINGS_UNIVERSE = [
    # AI / Semiconductors
    "NVDA", "AMD", "AVGO", "ALAB", "CRDO", "MRVL", "SMCI", "ANET",
    "MU", "INTC", "TSM", "ASML", "KLAC", "LRCX", "AMAT",
    # Cloud / Software
    "MSFT", "GOOGL", "AMZN", "META", "CRM", "NOW", "SNOW", "DDOG",
    "ZS", "CRWD", "PANW", "S", "OKTA",
    # Fintech / Crypto
    "COIN", "HOOD", "SQ", "PYPL", "NU", "SOFI", "AFRM",
    # Energy / Defense
    "CEG", "VST", "ETN", "VRT", "LMT", "RTX", "KTOS",
    # Biotech
    "RXRX", "EXAS", "NTRA", "ILMN",
    # Industrial / Copper
    "FCX", "SCCO", "X", "CLF",
    # General large cap
    "AAPL", "TSLA", "NFLX", "UBER", "LYFT",
]

# Fereastra de interes (zile)
EARNINGS_WINDOW_MIN = 3
EARNINGS_WINDOW_MAX = 21

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def get_earnings_calendar(
    extra_tickers: list[str] | None = None,
    window_days: int = EARNINGS_WINDOW_MAX
) -> dict:
    """
    Returnează dict: { "TICKER": { "days_to_earnings": N, "earnings_date": "YYYY-MM-DD" } }
    Doar pentru tickerele cu earnings în fereastra specificată.

    extra_tickers: tickere adiționale descoperite din triggere (Form 4, news)
    """
    universe = list(EARNINGS_UNIVERSE)
    if extra_tickers:
        for t in extra_tickers:
            if t.upper() not in universe:
                universe.append(t.upper())

    log_info(f"[Earnings] Scanning {len(universe)} tickers for upcoming earnings...")

    results = {}
    errors = 0

    # Batch: 10 tickere per request la Yahoo Finance
    for i in range(0, len(universe), 10):
        batch = universe[i:i + 10]
        batch_results = _fetch_earnings_batch(batch)

        for ticker, data in batch_results.items():
            if data:
                results[ticker] = data

        # Mic delay între batch-uri
        if i + 10 < len(universe):
            time.sleep(0.5)

    # Filtrează doar earnings în fereastra de interes
    filtered = {
        ticker: data
        for ticker, data in results.items()
        if EARNINGS_WINDOW_MIN <= data.get("days_to_earnings", 999) <= window_days
    }

    log_info(f"[Earnings] Found {len(filtered)} tickers with earnings in {EARNINGS_WINDOW_MIN}-{window_days} days.")
    return filtered


def _fetch_earnings_batch(tickers: list[str]) -> dict:
    """
    Fetch earnings timestamps pentru un batch de tickere.
    Yahoo Finance v7/finance/quote returnează earningsTimestamp.
    """
    symbols = ",".join(tickers)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote"
    params = {
        "symbols": symbols,
        "fields": "earningsTimestamp,earningsTimestampStart,earningsTimestampEnd,shortName,longName"
    }

    try:
        response = requests.get(
            url,
            headers=YAHOO_HEADERS,
            params=params,
            timeout=15
        )

        if response.status_code == 429:
            log_warn("[Earnings] Yahoo Finance rate limit — waiting 5s...")
            time.sleep(5)
            # Retry o dată
            response = requests.get(url, headers=YAHOO_HEADERS, params=params, timeout=15)

        if not response.ok:
            log_warn(f"[Earnings] Yahoo returned {response.status_code} for batch {tickers[:3]}...")
            return {}

        data = response.json()
        quotes = data.get("quoteResponse", {}).get("result", [])

        results = {}
        now = datetime.now(timezone.utc)

        for quote in quotes:
            ticker = quote.get("symbol", "").upper()
            if not ticker:
                continue

            # Yahoo returnează mai multe timestamp-uri — luăm cel mai relevant
            earnings_ts = _best_earnings_timestamp(quote, now)

            if earnings_ts is None:
                continue

            earnings_dt = datetime.fromtimestamp(earnings_ts, tz=timezone.utc)
            days_to_earnings = (earnings_dt - now).days

            # Ignoră earnings din trecut sau prea departe în viitor
            if days_to_earnings < -1 or days_to_earnings > 90:
                continue

            results[ticker] = {
                "days_to_earnings": max(0, days_to_earnings),
                "earnings_date": earnings_dt.strftime("%Y-%m-%d"),
                "company_name": quote.get("shortName") or quote.get("longName", ticker),
                "source": "yahoo_finance"
            }

        return results

    except Exception as e:
        log_warn(f"[Earnings] Batch fetch error: {e}")
        return {}


def _best_earnings_timestamp(quote: dict, now: datetime) -> int | None:
    """
    Yahoo returnează 3 câmpuri timestamp pentru earnings.
    Alegem cel mai apropiat în viitor.
    """
    candidates = []

    for field in ("earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd"):
        ts = quote.get(field)
        if ts and isinstance(ts, (int, float)) and ts > 0:
            candidates.append(int(ts))

    if not candidates:
        return None

    now_ts = int(now.timestamp())

    # Preferă timestamp-urile în viitor
    future = [ts for ts in candidates if ts > now_ts]
    if future:
        return min(future)  # cel mai aproape în viitor

    # Dacă toate sunt în trecut, returnează cel mai recent
    return max(candidates)


def get_earnings_for_ticker(ticker: str) -> dict | None:
    """
    Helper: returnează earnings info pentru un singur ticker.
    Folosit de trigger_stack_builder.
    """
    result = get_earnings_calendar(extra_tickers=[ticker.upper()], window_days=30)
    return result.get(ticker.upper())
