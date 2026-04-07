# File: app/collectors/insider_collector.py

import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from app.utils.logger import log_info, log_warn, log_error

SEC_HEADERS = {
    "User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

MIN_BUY_AMOUNT_USD = 50_000


def collect_insider_triggers(days_back: int = 2) -> list[dict]:
    log_info(f"[Form4] Collecting insider transactions (last {days_back} days)...")

    filings = _fetch_recent_form4_filings(days_back)
    if not filings:
        log_warn("[Form4] No recent Form 4 filings found.")
        return []

    log_info(f"[Form4] Found {len(filings)} Form 4 filings to process.")

    triggers = []
    for filing in filings[:60]:
        try:
            trigger = _parse_form4_filing(filing)
            if trigger:
                triggers.append(trigger)
        except Exception as e:
            log_warn(f"[Form4] Parse error {filing.get('accession', '')}: {e}")
            continue

    buy_triggers = [
        t for t in triggers
        if t["transaction_type"] == "P"
        and t["total_value"] >= MIN_BUY_AMOUNT_USD
    ]

    log_info(f"[Form4] {len(buy_triggers)} significant insider buys found.")
    return buy_triggers


def _fetch_recent_form4_filings(days_back: int) -> list[dict]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "forms": "4",
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": today,
        "hits.hits.total": 100,
    }

    try:
        response = requests.get(url, headers=SEC_HEADERS, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", {}).get("hits", [])
        filings = []

        for hit in hits:
            hit_id = hit.get("_id", "")
            source = hit.get("_source", {})

            if ":" not in hit_id:
                continue

            accession_raw, xml_filename = hit_id.split(":", 1)

            if not xml_filename.endswith(".xml"):
                continue

            ciks = source.get("ciks", [])
            company_cik = ciks[-1] if len(ciks) >= 2 else (ciks[0] if ciks else "")
            try:
                company_cik = str(int(company_cik)) if company_cik else ""
            except Exception:
                company_cik = ""

            display_names = source.get("display_names", [])
            company_name = display_names[-1] if len(display_names) >= 2 else (display_names[0] if display_names else "")

            accession_clean = accession_raw.replace("-", "")

            filings.append({
                "accession": accession_raw,
                "accession_clean": accession_clean,
                "xml_filename": xml_filename,
                "company_cik": company_cik,
                "company_name": company_name,
                "file_date": source.get("file_date", ""),
            })

        log_info(f"[Form4] Parsed {len(filings)} valid filings from EFTS.")
        return filings

    except Exception as e:
        log_error(f"[Form4] EFTS fetch error: {e}")
        return []


def _parse_form4_filing(filing: dict) -> dict | None:
    cik = filing.get("company_cik", "")
    accession_clean = filing.get("accession_clean", "")
    xml_filename = filing.get("xml_filename", "")

    if not cik or not accession_clean or not xml_filename:
        return None

    xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{xml_filename}"

    try:
        response = requests.get(xml_url, headers=SEC_HEADERS, timeout=15)

        if not response.ok:
            return None

        return _extract_form4_data(response.text, filing)

    except Exception:
        return None


def _extract_form4_data(xml_text: str, filing: dict) -> dict | None:
    """
    Parsează XML Form 4 — suportă multiple formate:
    - Standard SEC (fără namespace)
    - ownership.xml (cu namespace http://www.sec.gov/...)
    - rdgdoc.xml (format alternativ)
    """
    try:
        # Elimină namespace-uri pentru parsing uniform
        xml_clean = re.sub(r'\sxmlns[^"]*"[^"]*"', '', xml_text)
        xml_clean = re.sub(r'<[^>]+:', '<', xml_clean)
        xml_clean = re.sub(r'</[^>]+:', '</', xml_clean)

        root = ET.fromstring(xml_clean)
    except ET.ParseError:
        return None

    # ── Ticker ────────────────────────────────────────────────────
    ticker = ""
    company_name = _clean_display_name(filing.get("company_name", ""))

    # Încearcă multiple path-uri pentru ticker
    ticker_paths = [
        ".//issuerTradingSymbol",
        ".//issuer/issuerTradingSymbol",
        ".//tradingSymbol",
    ]
    for path in ticker_paths:
        elem = root.find(path)
        if elem is not None and elem.text and elem.text.strip():
            ticker = elem.text.strip().upper()
            break

    # Fallback: încearcă să extragă ticker din company_name
    if not ticker:
        ticker = _extract_ticker_from_name(company_name)

    if not ticker:
        return None

    # ── Company name ──────────────────────────────────────────────
    name_paths = [
        ".//issuerName",
        ".//issuer/issuerName",
        ".//companyName",
    ]
    for path in name_paths:
        elem = root.find(path)
        if elem is not None and elem.text and elem.text.strip():
            company_name = elem.text.strip()
            break

    # ── Insider info ──────────────────────────────────────────────
    insider_name = ""
    insider_role = ""

    name_paths2 = [
        ".//reportingOwnerId/rptOwnerName",
        ".//rptOwnerName",
        ".//ownerName",
    ]
    for path in name_paths2:
        elem = root.find(path)
        if elem is not None and elem.text:
            insider_name = elem.text.strip()
            break

    # Role
    is_director = root.findtext(".//isDirector", "0")
    is_officer = root.findtext(".//isOfficer", "0")
    officer_title = root.findtext(".//officerTitle", "")

    if is_director == "1":
        insider_role = "Director"
    elif is_officer == "1":
        insider_role = officer_title.strip() if officer_title else "Officer"
    else:
        insider_role = "10% Owner"

    # ── Tranzacții ────────────────────────────────────────────────
    best_purchase = None

    # Caută în nonDerivativeTransaction și derivativeTransaction
    txn_paths = [
        ".//nonDerivativeTransaction",
        ".//nonDerivativeTable/nonDerivativeTransaction",
        ".//derivativeTransaction",
    ]

    for txn_path in txn_paths:
        for txn in root.findall(txn_path):
            code = ""
            code_paths = [
                ".//transactionCoding/transactionCode",
                ".//transactionCode",
            ]
            for cp in code_paths:
                elem = txn.find(cp)
                if elem is not None and elem.text:
                    code = elem.text.strip().upper()
                    break

            if code not in ("P", "S"):
                continue

            # Shares
            shares = 0.0
            for sp in [".//transactionAmounts/transactionShares/value",
                       ".//transactionShares/value", ".//shares/value"]:
                elem = txn.find(sp)
                if elem is not None and elem.text:
                    try:
                        shares = float(elem.text.strip())
                        break
                    except ValueError:
                        pass

            # Price
            price = 0.0
            for pp in [".//transactionAmounts/transactionPricePerShare/value",
                       ".//transactionPricePerShare/value", ".//pricePerShare/value"]:
                elem = txn.find(pp)
                if elem is not None and elem.text:
                    try:
                        price = float(elem.text.strip())
                        break
                    except ValueError:
                        pass

            # Date
            date = ""
            for dp in [".//transactionDate/value", ".//transactionDate"]:
                elem = txn.find(dp)
                if elem is not None and elem.text:
                    date = elem.text.strip()
                    break

            value = shares * price

            if code == "P" and (best_purchase is None or value > best_purchase["total_value"]):
                best_purchase = {
                    "transaction_type": "P",
                    "shares": int(shares),
                    "price_per_share": round(price, 2),
                    "total_value": round(value, 2),
                    "transaction_date": date,
                }

    if not best_purchase or best_purchase["total_value"] == 0:
        return None

    # ── Confidence ────────────────────────────────────────────────
    val = best_purchase["total_value"]
    confidence = 6.0
    if val >= 1_000_000:    confidence = 9.0
    elif val >= 500_000:    confidence = 8.5
    elif val >= 200_000:    confidence = 8.0
    elif val >= 100_000:    confidence = 7.5
    elif val >= 50_000:     confidence = 7.0

    if any(t in insider_role for t in ("CEO", "President", "CFO", "CTO", "COO")):
        confidence = min(9.5, confidence + 0.5)

    filing_url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{filing.get('company_cik', '')}/"
        f"{filing.get('accession_clean', '')}/"
        f"{filing.get('xml_filename', '')}"
    )

    return {
        "ticker": ticker,
        "company_name": company_name,
        "insider_name": insider_name,
        "insider_role": insider_role,
        "transaction_type": best_purchase["transaction_type"],
        "shares": best_purchase["shares"],
        "price_per_share": best_purchase["price_per_share"],
        "total_value": best_purchase["total_value"],
        "transaction_date": best_purchase["transaction_date"],
        "filing_url": filing_url,
        "signal": "insider_buy",
        "tier": 1,
        "confidence": confidence,
    }


def _clean_display_name(name: str) -> str:
    """Elimină CIK și ticker din display_name."""
    # Format: "COMPANY NAME  (TICKER)  (CIK 0001234567)"
    clean = re.sub(r'\s*\(CIK[^)]+\)', '', name)
    clean = re.sub(r'\s*\([A-Z]{1,5}(?:,[A-Z]{1,5})*\)', '', clean)
    return clean.strip()


def _extract_ticker_from_name(display_name: str) -> str:
    """Extrage ticker din display_name dacă e prezent."""
    # Format: "COMPANY NAME  (TICKER)  (CIK ...)"
    match = re.search(r'\(([A-Z]{1,5})\)\s+\(CIK', display_name)
    if match:
        return match.group(1)
    return ""


def get_insider_activity_for_ticker(ticker: str, days_back: int = 7) -> dict:
    triggers = collect_insider_triggers(days_back=days_back)
    ticker_triggers = [t for t in triggers if t.get("ticker") == ticker.upper()]

    if not ticker_triggers:
        return {"has_insider_buy": False, "headline": "", "confidence": 0.0, "details": []}

    best = max(ticker_triggers, key=lambda x: x["total_value"])
    return {
        "has_insider_buy": True,
        "headline": (
            f"Insider buy: {best['insider_name']} ({best['insider_role']}) "
            f"— ${best['total_value']:,.0f} @ ${best['price_per_share']}"
        ),
        "confidence": best["confidence"],
        "details": ticker_triggers
    }
