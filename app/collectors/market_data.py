# File: app/collectors/market_data.py

import requests

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"


def collect_market_data(tickers=None):
    """
    Colectează market data pentru toate tickerele într-un singur request.
    Evită 429 mult mai bine decât request per ticker.
    """

    if tickers is None:
        tickers = ["NVDA", "AMD", "CRDO", "SMCI", "PLTR"]

    if not tickers:
        return {}

    symbols = ",".join(sorted(set(tickers)))

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    results = {}

    try:
        response = requests.get(
            YAHOO_QUOTE_URL,
            params={"symbols": symbols},
            headers=headers,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        quote_results = data.get("quoteResponse", {}).get("result", [])

        for item in quote_results:
            ticker = item.get("symbol")
            if not ticker:
                continue

            results[ticker] = {
                "ticker": ticker,
                "price": item.get("regularMarketPrice"),
                "previous_close": item.get("regularMarketPreviousClose"),
                "open": item.get("regularMarketOpen"),
                "high": item.get("regularMarketDayHigh"),
                "low": item.get("regularMarketDayLow"),
                "close": item.get("regularMarketPrice"),
                "volume": item.get("regularMarketVolume"),
                "avg_volume_5d": item.get("averageDailyVolume3Month"),
                "source": "Yahoo Finance"
            }

        # fallback pentru tickere lipsă
        for ticker in tickers:
            if ticker not in results:
                results[ticker] = {
                    "ticker": ticker,
                    "error": "No market data returned",
                    "source": "Yahoo Finance"
                }

    except Exception as e:
        for ticker in tickers:
            results[ticker] = {
                "ticker": ticker,
                "error": str(e),
                "source": "Yahoo Finance"
            }

    return results
