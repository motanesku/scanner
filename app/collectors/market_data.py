# File: app/collectors/market_data.py

import yfinance as yf


def collect_market_data(tickers=None):
    """
    Market data cu yfinance.
    Dacă apare rate limit / lipsă date, întoarce scor neutru prin lipsa datelor,
    nu strică restul scannerului.
    """

    if tickers is None:
        tickers = ["SPY"]

    results = {}

    for ticker in tickers:
        try:
            tk = yf.Ticker(ticker)
            df = tk.history(period="5d", interval="1d", auto_adjust=False)

            if df is None or df.empty:
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
                    "source": "yfinance",
                    "status": "no_data"
                }
                continue

            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else last
            volume_series = df["Volume"].dropna()

            results[ticker] = {
                "ticker": ticker,
                "price": _safe_float(last.get("Close")),
                "previous_close": _safe_float(prev.get("Close")),
                "open": _safe_float(last.get("Open")),
                "high": _safe_float(last.get("High")),
                "low": _safe_float(last.get("Low")),
                "close": _safe_float(last.get("Close")),
                "volume": _safe_int(last.get("Volume")),
                "avg_volume_5d": _safe_float(volume_series.mean()) if not volume_series.empty else None,
                "source": "yfinance",
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
                "source": "yfinance",
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
