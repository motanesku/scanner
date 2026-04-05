# File: app/collectors/market_data.py

import yfinance as yf


def collect_market_data(tickers=None):
    """
    Market data folosind yfinance (stabil, deja folosit în proiectul tău).
    """

    if tickers is None:
        tickers = ["NVDA", "AMD", "SMCI", "ANET", "XOM", "CCJ"]

    results = {}

    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            threads=True
        )

        for ticker in tickers:
            try:
                df = data[ticker] if len(tickers) > 1 else data

                if df.empty:
                    raise ValueError("No data returned")

                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) >= 2 else last

                volume_series = df["Volume"].dropna()

                results[ticker] = {
                    "ticker": ticker,
                    "price": float(last["Close"]),
                    "previous_close": float(prev["Close"]),
                    "open": float(last["Open"]),
                    "high": float(last["High"]),
                    "low": float(last["Low"]),
                    "close": float(last["Close"]),
                    "volume": int(last["Volume"]),
                    "avg_volume_5d": float(volume_series.mean()) if not volume_series.empty else None,
                    "source": "yfinance"
                }

            except Exception as e:
                results[ticker] = {
                    "ticker": ticker,
                    "error": str(e),
                    "source": "yfinance"
                }

    except Exception as e:
        for ticker in tickers:
            results[ticker] = {
                "ticker": ticker,
                "error": str(e),
                "source": "yfinance"
            }

    return results
