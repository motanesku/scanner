# File: app/collectors/sec_enricher.py
#
# Enrichment SIC din SEC EDGAR — gratuit, oficial, fără rate limit sever.
#
# Workflow:
# 1. Caută CIK pentru ticker din EDGAR company search
# 2. Fetch data.sec.gov/submissions/CIK{cik}.json
# 3. Extrage sic + sicDescription
# 4. Cacheaza în memorie (SIC nu se schimbă)

import re
import time
import requests
from app.utils.logger import log_info, log_warn, log_error

HEADERS = {"User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com"}

# Cache în memorie per proces — SIC nu se schimbă
_sic_cache: dict[str, tuple[int, str]] = {}

# EDGAR company search
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
EDGAR_COMPANY_URL = "https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=1&search_text=&action=getcompany&output=atom"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Cache CIK lookup — descărcat o dată
_cik_map: dict[str, str] = {}  # ticker → cik (zero-padded 10 digits)


def _load_cik_map() -> dict[str, str]:
    """
    Descarcă mapping-ul complet ticker → CIK din SEC EDGAR.
    Fișier static, actualizat zilnic de SEC.
    ~500KB, conține toate companiile publice US.
    """
    global _cik_map

    if _cik_map:
        return _cik_map

    try:
        log_info("[SEC] Loading CIK map from EDGAR...")
        r = requests.get(
            EDGAR_TICKERS_URL,
            headers=HEADERS,
            timeout=20
        )
        r.raise_for_status()
        data = r.json()

        # Format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        for _, item in data.items():
            ticker = item.get("ticker", "").upper()
            cik = str(item.get("cik_str", "")).zfill(10)
            if ticker:
                _cik_map[ticker] = cik

        log_info(f"[SEC] CIK map loaded: {len(_cik_map)} tickers")
        return _cik_map

    except Exception as e:
        log_error(f"[SEC] CIK map load error: {e}")
        return {}


def _get_cik(ticker: str) -> str | None:
    """Returnează CIK pentru un ticker."""
    cik_map = _load_cik_map()
    return cik_map.get(ticker.upper())


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
            log_warn(f"[SEC] Rate limit for {ticker} — waiting 5s")
            time.sleep(5)
            r = requests.get(url, headers=HEADERS, timeout=15)

        r.raise_for_status()
        data = r.json()

        sic = data.get("sic")
        sic_desc = data.get("sicDescription", "")

        if sic:
            return (int(sic), sic_desc)

        return None

    except Exception as e:
        log_error(f"[SEC] Submissions fetch error for {ticker}: {e}")
        return None


def enrich_with_sic(tickers: list[str]) -> dict[str, tuple[int, str]]:
    """
    Returnează SIC code și descriere pentru lista de tickers.

    Returnează:
    {
        "APP":  (7372, "Services-Prepackaged Software"),
        "NRIX": (2836, "Pharmaceutical Preparations"),
        "OGS":  (4924, "Natural Gas Distribution"),
        "AEHR": (3825, "Instruments for Measuring"),
        ...
    }

    Tickers fără SIC → nu apar în rezultat.
    Folosește cache în memorie — request SEC doar o dată per ticker per proces.
    """
    result = {}

    for ticker in tickers:
        ticker = ticker.upper()

        # Din cache
        if ticker in _sic_cache:
            result[ticker] = _sic_cache[ticker]
            continue

        # Fetch din SEC
        sic_data = _fetch_sic_from_edgar(ticker)

        if sic_data:
            _sic_cache[ticker] = sic_data
            result[ticker] = sic_data
            log_info(f"[SEC] {ticker}: SIC {sic_data[0]} — {sic_data[1]}")
        else:
            log_warn(f"[SEC] {ticker}: no SIC found")

        # Rate limit respectuos față de SEC
        time.sleep(0.15)

    return result


def get_sic(ticker: str) -> tuple[int, str] | None:
    """Returnează SIC pentru un singur ticker."""
    result = enrich_with_sic([ticker])
    return result.get(ticker.upper())
