# File: app/data/ticker_universe.py
#
# Entity layer auto — ticker universe din Polygon.
# Include SIC code per ticker pentru filtrare tematică.

import re
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from app.config import POLYGON_API_KEY
from app.utils.logger import log_info, log_warn, log_error

UNIVERSE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ticker_universe.json"
UNIVERSE_PATH.parent.mkdir(exist_ok=True)

MAX_PAGES = 5
CACHE_TTL_HOURS = 24


def _generate_aliases(company_name: str) -> list[str]:
    if not company_name:
        return []

    name = company_name.lower().strip()
    aliases = set()
    aliases.add(name)

    LEGAL_SUFFIXES = [
        r"\s+inc\.?$", r"\s+corp\.?$", r"\s+corporation$",
        r"\s+ltd\.?$", r"\s+limited$", r"\s+llc\.?$",
        r"\s+plc\.?$", r"\s+holdings?$", r"\s+group$",
        r"\s+co\.?$", r"\s+company$", r"\s+technologies$",
        r"\s+technology$", r"\s+systems$", r"\s+solutions$",
        r"\s+international$", r"\s+enterprises?$", r"\s+services?$",
        r"\s+networks?$", r"\s+pharmaceuticals?$", r"\s+therapeutics$",
        r"\s+biosciences?$", r"\s+laboratories?$", r"\s+labs?$",
        r"\s+energy$", r"\s+resources?$", r"\s+industries$",
    ]

    clean = name
    for suffix in LEGAL_SUFFIXES:
        stripped = re.sub(suffix, "", clean).strip()
        if stripped and stripped != clean and len(stripped) > 2:
            aliases.add(stripped)
            clean = stripped

    no_punct = re.sub(r"[^\w\s]", "", name).strip()
    if no_punct and no_punct != name:
        aliases.add(no_punct)

    SKIP_ALIASES = {
        "inc", "corp", "ltd", "llc", "plc", "co", "group", "the",
        "holdings", "company", "international", "global", "national",
        "first", "new", "american", "united", "general",
    }

    final = []
    for alias in aliases:
        if len(alias) < 3:
            continue
        if alias in SKIP_ALIASES:
            continue
        final.append(alias)

    final.sort(key=len, reverse=True)
    return final


def _fetch_polygon_tickers(api_key: str) -> list[dict]:
    all_tickers = []
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "market": "stocks",
        "active": "true",
        "order": "asc",
        "limit": 1000,
        "sort": "ticker",
        "apiKey": api_key,
    }

    page = 0
    next_url = None

    while page < MAX_PAGES:
        try:
            if next_url:
                r = requests.get(next_url, timeout=20)
            else:
                r = requests.get(url, params=params, timeout=20)

            if r.status_code == 429:
                log_warn("[Universe] Polygon rate limit — waiting 15s...")
                time.sleep(15)
                continue

            r.raise_for_status()
            data = r.json()

            results = data.get("results", [])
            all_tickers.extend(results)
            log_info(f"[Universe] Page {page + 1}: {len(results)} tickers (total: {len(all_tickers)})")

            next_url = data.get("next_url")
            if not next_url:
                break
            if "apiKey" not in next_url:
                next_url += f"&apiKey={api_key}"

            page += 1
            time.sleep(0.5)

        except Exception as e:
            log_error(f"[Universe] Polygon fetch error page {page}: {e}")
            break

    return all_tickers


def build_universe(force: bool = False) -> dict:
    """
    Construiește sau încarcă ticker universe.

    Structură returnată:
    {
        "tickers": {
            "NVDA": {
                "name": "NVIDIA CORP",
                "exchange": "XNAS",
                "sic_code": 3674,
                "sic_description": "Semiconductors and Related Devices"
            },
            ...
        },
        "alias_index": {"nvidia": "NVDA", ...},
        "built_at": "...",
        "count": 4521,
        "alias_count": 8771
    }
    """
    if not force and UNIVERSE_PATH.exists():
        try:
            with open(UNIVERSE_PATH, "r") as f:
                cached = json.load(f)

            built_at = cached.get("built_at", "")
            if built_at:
                age_hours = (
                    datetime.now(timezone.utc) -
                    datetime.fromisoformat(built_at.replace("Z", "+00:00"))
                ).total_seconds() / 3600

                if age_hours < CACHE_TTL_HOURS:
                    log_info(f"[Universe] Using cached universe ({len(cached.get('tickers', {}))} tickers, {age_hours:.1f}h old)")
                    return cached
        except Exception as e:
            log_warn(f"[Universe] Cache read error: {e}")

    if not POLYGON_API_KEY:
        log_warn("[Universe] No POLYGON_API_KEY — using empty universe")
        return _empty_universe()

    log_info("[Universe] Building ticker universe from Polygon...")
    raw_tickers = _fetch_polygon_tickers(POLYGON_API_KEY)

    if not raw_tickers:
        log_warn("[Universe] No tickers fetched — using empty universe")
        return _empty_universe()

    tickers = {}
    alias_index = {}
    skipped = 0

    for item in raw_tickers:
        ticker = item.get("ticker", "").upper().strip()
        name = item.get("name", "").strip()
        exchange = item.get("primary_exchange", "")
        sic_code = item.get("sic_code")
        sic_description = item.get("sic_description", "")

        if not ticker or not name:
            continue

        if not re.match(r'^[A-Z]{1,5}$', ticker):
            skipped += 1
            continue

        tickers[ticker] = {
            "name": name,
            "exchange": exchange,
            "sic_code": int(sic_code) if sic_code else None,
            "sic_description": sic_description,
        }

        aliases = _generate_aliases(name)
        for alias in aliases:
            if alias not in alias_index:
                alias_index[alias] = ticker

    universe = {
        "tickers": tickers,
        "alias_index": alias_index,
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(tickers),
        "alias_count": len(alias_index),
    }

    try:
        with open(UNIVERSE_PATH, "w") as f:
            json.dump(universe, f, separators=(",", ":"))
        log_info(f"[Universe] Saved: {len(tickers)} tickers, {len(alias_index)} aliases → {UNIVERSE_PATH}")
    except Exception as e:
        log_error(f"[Universe] Save error: {e}")

    return universe


def _empty_universe() -> dict:
    return {
        "tickers": {},
        "alias_index": {},
        "built_at": datetime.now(timezone.utc).isoformat(),
        "count": 0,
        "alias_count": 0,
    }


def is_valid_ticker(ticker: str, universe: dict) -> bool:
    return ticker.upper() in universe.get("tickers", {})


def get_ticker_name(ticker: str, universe: dict) -> str | None:
    info = universe.get("tickers", {}).get(ticker.upper())
    return info.get("name") if info else None


def get_ticker_sic(ticker: str, universe: dict) -> tuple[int | None, str]:
    """Returnează (sic_code, sic_description) pentru un ticker."""
    info = universe.get("tickers", {}).get(ticker.upper(), {})
    return info.get("sic_code"), info.get("sic_description", "")
