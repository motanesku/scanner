# File: app/collectors/market_data.py

import requests

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def collect_market_data(tickers=None):
    """
    Colectează market data simplă pentru tickerele date.
    Returnează OHLC + volume + preț curent.
    """

    if tickers is None:
        tickers = ["NVDA", "AMD", "CRDO", "SMCI", "PLTR"]

    results = {}

    for ticker in tickers:
        try:
            url = YAHOO_CHART_URL.format(ticker=ticker)
            params = {
                "range": "5d",
                "interval": "1d"
            }

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            result = data.get("chart", {}).get("result", [])
            if not result:
                results[ticker] = {"error": "No market data"}
                continue

            quote = result[0].get("indicators", {}).get("quote", [{}])[0]
            meta = result[0].get("meta", {})

            closes = quote.get("close", [])
            volumes = quote.get("volume", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            opens = quote.get("open", [])

            results[ticker] = {
                "ticker": ticker,
                "price": meta.get("regularMarketPrice"),
                "previous_close": meta.get("chartPreviousClose"),
                "open": opens[-1] if opens else None,
                "high": highs[-1] if highs else None,
                "low": lows[-1] if lows else None,
                "close": closes[-1] if closes else None,
                "volume": volumes[-1] if volumes else None,
                "avg_volume_5d": _avg([v for v in volumes if v is not None]),
                "source": "Yahoo Finance"
            }

        except Exception as e:
            results[ticker] = {
                "ticker": ticker,
                "error": str(e),
                "source": "Yahoo Finance"
            }

    return results


def _avg(values):
    if not values:
        return None
    return sum(values) / len(values)
