# File: app/collectors/sec_enricher.py
#
# Enrichment SIC din SEC EDGAR — gratuit, oficial.
#
# Workflow:
# 1. CIK map — descărcat O DATĂ/ZI, cacheat în D1 via Worker (TTL 24h)
# 2. Fetch data.sec.gov/submissions/CIK{cik}.json per ticker
# 3. Extrage sic + sicDescription
# 4. Cache în memorie per proces (SIC nu se schimbă în aceeași zi)

import os
import json
import time
import requests
from app.utils.logger import log_info, log_warn, log_error

HEADERS = {"User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com"}
WORKER_URL = os.environ.get("WORKER_URL", "https://portfolio-api.danut-fagadau.workers.dev")

EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_TICKERS_URL     = "https://www.sec.gov/files/company_tickers.json"

# Cache în memorie per proces
_sic_cache: dict[str, tuple[int, str]] = {}
_cik_map:   dict[str, str] = {}   # ticker → cik (zero-padded 10 digits)


# ── CIK Map — cacheat în D1 via Worker (TTL 24h) ─────────────────────────────

def _load_cik_map_from_d1() -> dict[str, str]:
    """
    Încearcă să citească CIK map din D1 cache via Worker.
    Returnează dict sau {} dacă cache-ul nu există / e expirat.
    """
    try:
        r = requests.get(
            f"{WORKER_URL}/api/sec-cik-cache",
            timeout=10
        )
        if r.ok:
            data = r.json()
            if data.get("ok") and data.get("data"):
                log_info(f"[SEC] CIK map loaded from D1 cache ({data.get('age_h', '?')}h old)")
                return data["data"]
    except Exception as e:
        log_warn(f"[SEC] D1 cache read failed: {e}")
    return {}


def _save_cik_map_to_d1(cik_map: dict[str, str]) -> None:
    """Salvează CIK map în D1 via Worker."""
    try:
        r = requests.post(
            f"{WORKER_URL}/api/sec-cik-cache",
            json={"data": cik_map},
            timeout=30
        )
        if r.ok:
            log_info(f"[SEC] CIK map saved to D1 ({len(cik_map)} tickers)")
        else:
            log_warn(f"[SEC] D1 cache save failed: {r.status_code}")
    except Exception as e:
        log_warn(f"[SEC] D1 cache save error: {e}")


def _load_cik_map() -> dict[str, str]:
    """
    Returnează CIK map cu strategie cache:
    1. Cache în memorie (același proces)
    2. Cache D1 via Worker (24h TTL)
    3. Fetch direct din SEC EDGAR (fallback)
    """
    global _cik_map

    if _cik_map:
        return _cik_map

    # Încearcă D1 cache
    cached = _load_cik_map_from_d1()
    if cached:
        _cik_map = cached
        return _cik_map

    # Fetch din SEC EDGAR
    log_info("[SEC] Fetching CIK map from EDGAR (not in cache)...")
    try:
        r = requests.get(EDGAR_TICKERS_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()

        # Format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        cik_map = {}
        for _, item in data.items():
            ticker = item.get("ticker", "").upper()
            cik = str(item.get("cik_str", "")).zfill(10)
            if ticker:
                cik_map[ticker] = cik

        log_info(f"[SEC] CIK map fetched: {len(cik_map)} tickers")

        # Salvează în D1 pentru data viitoare
        _save_cik_map_to_d1(cik_map)

        _cik_map = cik_map
        return _cik_map

    except Exception as e:
        log_error(f"[SEC] CIK map load error: {e}")
        return {}


def _get_cik(ticker: str) -> str | None:
    cik_map = _load_cik_map()
    return cik_map.get(ticker.upper())


# ── SIC fetch per ticker ──────────────────────────────────────────────────────

def _fetch_sic_from_edgar(ticker: str) -> tuple[int, str] | None:
    """
    Fetch SIC code și descriere din SEC EDGAR submissions.
    Returnează (sic_code, sic_description) sau None.
    """
    cik = _get_cik(ticker)
    if not cik:
        log_warn(f"[SEC] No CIK found for {ticker}")
        return None

    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 404:
            log_warn(f"[SEC] No submissions for {ticker} (CIK: {cik})")
            return None

        if r.status_code == 429:
            log_warn(f"[SEC] Rate limit for {ticker} — waiting 10s")
            time.sleep(10)
            r = requests.get(url, headers=HEADERS, timeout=15)

        r.raise_for_status()
        data = r.json()

        sic = data.get("sic")
        sic_desc = data.get("sicDescription", "")

        if sic:
            return (int(sic), sic_desc)

        log_warn(f"[SEC] {ticker}: no SIC found")
        return None

    except Exception as e:
        log_error(f"[SEC] Submissions fetch error for {ticker}: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def enrich_with_sic(tickers: list[str]) -> dict[str, tuple[int, str]]:
    """
    Returnează SIC code și descriere pentru lista de tickers.

    Returnează:
    {
        "APP":  (7372, "Services-Prepackaged Software"),
        "NRIX": (2836, "Pharmaceutical Preparations"),
        ...
    }

    Tickers fără SIC → nu apar în rezultat.
    Cache în memorie — request SEC doar o dată per ticker per proces.
    """
    result = {}

    for ticker in tickers:
        ticker = ticker.upper()

        # Din cache memorie
        if ticker in _sic_cache:
            result[ticker] = _sic_cache[ticker]
            continue

        # Fetch din SEC
        sic_data = _fetch_sic_from_edgar(ticker)

        if sic_data:
            _sic_cache[ticker] = sic_data
            result[ticker] = sic_data
            log_info(f"[SEC] {ticker}: SIC {sic_data[0]} — {sic_data[1]}")

        # Rate limit respectuos față de SEC
        time.sleep(0.2)

    return result


def get_sic(ticker: str) -> tuple[int, str] | None:
    """Returnează SIC pentru un singur ticker."""
    result = enrich_with_sic([ticker])
    return result.get(ticker.upper())
