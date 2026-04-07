# File: app/collectors/earnings_collector.py
#
# Sursa: SEC EDGAR 8-K Item 2.02 = Results of Operations
# Item 2.02 = compania tocmai a raportat earnings
# Acesta e mai valoros decât earnings calendar viitor:
# → detectează beat/miss în timp real
# → trigger direct Tier 1
# → ticker descoperit dinamic, fără listă predefinită

import re
import requests
from datetime import datetime, timezone, timedelta
from app.utils.logger import log_info, log_warn, log_error

SEC_HEADERS = {
    "User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

# Item 2.02 = Results of Operations (earnings announcement)
# Item 2.01 = Completion of Acquisition
# Item 8.01 = Other Events (guidance updates, prelim results)
EARNINGS_ITEMS = {"2.02", "8.01"}

# Regex pentru ticker din display_names
# Format: "COMPANY NAME  (TICKER)  (CIK 0001234567)"
TICKER_REGEX = re.compile(r'\(([A-Z]{1,5})\)\s+\(CIK')


def get_earnings_calendar(
    extra_tickers: list[str] | None = None,
    window_days: int = 14
) -> dict:
    """
    Returnează dict: { "TICKER": { "days_to_earnings": 0, "earnings_date": "YYYY-MM-DD", ... } }

    Strategie duală:
    1. Earnings recente (ultimele 3 zile) — 8-K Item 2.02 deja depuse
    2. Earnings anunțate (8-K Item 7.01 cu press release) — anunțuri viitoare

    days_to_earnings = 0 înseamnă că tocmai au raportat → trigger imediat
    """
    log_info("[Earnings] Collecting earnings triggers from SEC EDGAR 8-K...")

    results = {}

    # 1. Earnings recente — Item 2.02
    recent = _fetch_8k_earnings(days_back=3, items_filter={"2.02"})
    for ticker, data in recent.items():
        results[ticker] = {**data, "trigger_type": "earnings_reported"}

    # 2. Upcoming earnings anunțate — Item 7.01 cu keywords
    upcoming = _fetch_8k_guidance(days_back=5)
    for ticker, data in upcoming.items():
        if ticker not in results:
            results[ticker] = {**data, "trigger_type": "earnings_upcoming"}

    log_info(f"[Earnings] Found {len(results)} earnings triggers from 8-K filings.")
    return results


def _fetch_8k_earnings(days_back: int, items_filter: set) -> dict:
    """
    Fetch 8-K filings cu items specifici din ultimele N zile.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "forms": "8-K",
        "dateRange": "custom",
        "startdt": start,
        "enddt": today,
        "hits.hits.total": 100,
    }

    try:
        response = requests.get(url, headers=SEC_HEADERS, params=params, timeout=20)
        response.raise_for_status()

        hits = response.json().get("hits", {}).get("hits", [])
        results = {}

        for hit in hits:
            src = hit.get("_source", {})
            items = set(src.get("items", []))

            # Verifică dacă filing-ul conține items relevante
            if not items.intersection(items_filter):
                continue

            # Extrage ticker din display_names
            display_names = src.get("display_names", [])
            ticker = _extract_ticker_from_names(display_names)
            if not ticker:
                continue

            company_name = _extract_company_name(display_names)
            file_date = src.get("file_date", "")

            # Calculează days_to_earnings
            try:
                filing_dt = datetime.strptime(file_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_ago = (datetime.now(timezone.utc) - filing_dt).days
            except Exception:
                days_ago = 0

            results[ticker] = {
                "days_to_earnings": 0,  # tocmai au raportat
                "days_ago": days_ago,
                "earnings_date": file_date,
                "company_name": company_name,
                "items": list(items),
                "filing_id": hit.get("_id", ""),
                "source": "sec_edgar_8k"
            }

        return results

    except Exception as e:
        log_warn(f"[Earnings] 8-K fetch error: {e}")
        return {}


def _fetch_8k_guidance(days_back: int) -> dict:
    """
    Fetch 8-K Item 7.01 (press release) care menționează earnings/guidance.
    Acestea sunt adesea anunțuri de earnings preliminare sau guidance updates.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "forms": "8-K",
        "dateRange": "custom",
        "startdt": start,
        "enddt": today,
        "hits.hits.total": 50,
    }

    try:
        response = requests.get(url, headers=SEC_HEADERS, params=params, timeout=20)
        response.raise_for_status()

        hits = response.json().get("hits", {}).get("hits", [])
        results = {}

        for hit in hits:
            src = hit.get("_source", {})
            items = set(src.get("items", []))

            # 7.01 = Regulation FD Disclosure (guidance, prelim results)
            if "7.01" not in items:
                continue

            display_names = src.get("display_names", [])
            ticker = _extract_ticker_from_names(display_names)
            if not ticker:
                continue

            company_name = _extract_company_name(display_names)
            file_date = src.get("file_date", "")

            results[ticker] = {
                "days_to_earnings": 1,
                "earnings_date": file_date,
                "company_name": company_name,
                "items": list(items),
                "filing_id": hit.get("_id", ""),
                "source": "sec_edgar_8k_guidance"
            }

        return results

    except Exception as e:
        log_warn(f"[Earnings] 8-K guidance fetch error: {e}")
        return {}


def _extract_ticker_from_names(display_names: list) -> str:
    """
    Extrage ticker din display_names.
    Format: "COMPANY NAME  (TICKER)  (CIK 0001234567)"
    """
    for name in display_names:
        match = TICKER_REGEX.search(name)
        if match:
            ticker = match.group(1)
            # Filtrează tichere false (ex: CIK-uri care arată ca tickers)
            if len(ticker) <= 5 and ticker.isalpha():
                return ticker.upper()
    return ""


def _extract_company_name(display_names: list) -> str:
    """
    Extrage numele companiei din primul display_name.
    """
    if not display_names:
        return ""
    # Format: "COMPANY NAME  (TICKER)  (CIK ...)"
    name = display_names[0]
    # Elimină tot ce e după primul "("
    clean = name.split("(")[0].strip()
    return clean


def get_earnings_for_ticker(ticker: str) -> dict | None:
    """
    Helper: returnează earnings info pentru un singur ticker.
    """
    results = get_earnings_calendar()
    return results.get(ticker.upper())
