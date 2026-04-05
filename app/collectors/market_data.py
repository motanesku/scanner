# File: app/collectors/market_data.py

import csv
import io
import requests

STOOQ_URL = "https://stooq.com/q/d/l/"


def collect_market_data(tickers=None):
    """
    Market data din Stooq, fără API key.
    Returnează price / previous_close / volume / avg_volume_5d.
    """

    if tickers is None:
        tickers = ["NVDA", "AMD", "SMCI", "ANET", "XOM", "CCJ"]

    results = {}

    for ticker in tickers:
        try:
            stooq_symbol = f"{ticker.lower()}.us"
            response = requests.get(
                STOOQ_URL,
                params={"s": stooq_symbol, "i": "d"},
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()

            content = response.text.strip()
            if not content or "No data" in content:
                results[ticker] = {
                    "ticker": ticker,
                    "error": "No market data returned",
                    "source": "Stooq"
                }
                continue

            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)

            if len(rows) < 2:
                results[ticker] = {
                    "ticker": ticker,
                    "error": "Not enough historical rows",
                    "source": "Stooq"
                }
                continue

            last_row = rows[-1]
            prev_row = rows[-2]
            recent_rows = rows[-5:] if len(rows) >= 5 else rows

            volumes = []
            for row in recent_rows:
                try:
                    volumes.append(int(row["Volume"]))
                except Exception:
                    continue

            results[ticker] = {
                "ticker": ticker,
                "price": _to_float(last_row.get("Close")),
                "previous_close": _to_float(prev_row.get("Close")),
                "open": _to_float(last_row.get("Open")),
                "high": _to_float(last_row.get("High")),
                "low": _to_float(last_row.get("Low")),
                "close": _to_float(last_row.get("Close")),
                "volume": _to_int(last_row.get("Volume")),
                "avg_volume_5d": _avg(volumes),
                "source": "Stooq"
            }

        except Exception as e:
            results[ticker] = {
                "ticker": ticker,
                "error": str(e),
                "source": "Stooq"
            }

    return results


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _to_int(value):
    try:
        return int(value)
    except Exception:
        return None


def _avg(values):
    if not values:
        return None
    return sum(values) / len(values)
