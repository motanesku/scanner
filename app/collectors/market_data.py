# File: app/collectors/market_data.py

import yfinance as yf


def collect_market_data(tickers=None):
    """
    Market data cu yfinance, ticker cu ticker.
    Mai stabil decât batch download în Railway.
    """

    if tickers is None:
        tickers = ["NVDA", "AMD", "SMCI", "ANET", "XOM", "CCJ"]

    results = {}

    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker)
            df = tk.history(period="5d", interval="1d", auto_adjust=False)

            if df is None or df.empty:
                results[ticker] = {
                    "ticker": ticker,
                    "error": "No data returned",
                    "source": "yfinance"
                }
                continue

            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else last

            volume_series = df["Volume"].dropna()

            results[ticker] = {
                "ticker": ticker,
                "price": float(last["Close"]) if last["Close"] is not None else None,
                "previous_close": float(prev["Close"]) if prev["Close"] is not None else None,
                "open": float(last["Open"]) if last["Open"] is not None else None,
                "high": float(last["High"]) if last["High"] is not None else None,
                "low": float(last["Low"]) if last["Low"] is not None else None,
                "close": float(last["Close"]) if last["Close"] is not None else None,
                "volume": int(last["Volume"]) if last["Volume"] is not None else None,
                "avg_volume_5d": float(volume_series.mean()) if not volume_series.empty else None,
                "source": "yfinance"
            }

        except Exception as e:
            results[ticker] = {
                "ticker": ticker,
                "error": str(e),
                "source": "yfinance"
            }

    return results
