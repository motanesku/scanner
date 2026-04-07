# File: app/collectors/insider_collector.py
#
# Colectează Form 4 (insider transactions) din SEC EDGAR.
# Fix: folosim _id din EFTS care conține direct path-ul XML
# Format _id: "0001628280-26-023885:wk-form4_1775505331.xml"
#             ──────────────────── ───────────────────────
#             accession            filename

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
    """
    Colectează Form 4 recente din SEC EDGAR.
    Returnează lista de triggere cu insider buying semnificativ.
    """
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
    """
    Fetch Form 4 recente din EDGAR EFTS.
    Extrage accession + filename XML direct din _id field.
    """
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
            # _id format: "0001628280-26-023885:wk-form4_1775505331.xml"
            hit_id = hit.get("_id", "")
            source = hit.get("_source", {})

            if ":" not in hit_id:
                continue

            accession_raw, xml_filename = hit_id.split(":", 1)

            # Sari dacă nu e XML
            if not xml_filename.endswith(".xml"):
                continue

            # CIK-ul companiei e al doilea din lista ciks
            ciks = source.get("ciks", [])
            company_cik = ciks[-1] if len(ciks) >= 2 else (ciks[0] if ciks else "")
            company_cik = str(int(company_cik)) if company_cik else ""

            display_names = source.get("display_names", [])
            company_name = display_names[-1] if len(display_names) >= 2 else (display_names[0] if display_names else "")

            # accession fără cratime pentru path
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
    """
    Descarcă și parsează XML-ul Form 4.
    URL format: https://www.sec.gov/Archives/edgar/data/{CIK}/{accession_clean}/{xml_filename}
    """
    cik = filing.get("company_cik", "")
    accession_clean = filing.get("accession_clean", "")
    xml_filename = filing.get("xml_filename", "")

    if not cik or not accession_clean or not xml_filename:
        return None

    xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{xml_filename}"

    try:
        response = requests.get(xml_url, headers=SEC_HEADERS, timeout=15)

        if response.status_code == 404:
            # Proba cu CIK padding
            cik_padded = cik.zfill(10)
            xml_url2 = f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/{accession_clean}/{xml_filename}"
            response = requests.get(xml_url2, headers=SEC_HEADERS, timeout=15)

        if not response.ok:
            return None

        return _extract_form4_data(response.text, filing)

    except Exception:
        return None


def _extract_form4_data(xml_text: str, filing: dict) -> dict | None:
    """
    Parsează XML-ul Form 4 și extrage datele relevante.
    """
    try:
        root = ET.fromstring(xml_text)

        # Ticker
        ticker = ""
        company_name = filing.get("company_name", "")

        issuer = root.find(".//issuer")
        if issuer is not None:
            ticker_elem = issuer.find("issuerTradingSymbol")
            if ticker_elem is not None and ticker_elem.text:
                ticker = ticker_elem.text.strip().upper()
            name_elem = issuer.find("issuerName")
            if name_elem is not None and name_elem.text:
                company_name = name_elem.text.strip()

        if not ticker:
            return None

        # Insider info
        insider_name = ""
        insider_role = ""
        owner = root.find(".//reportingOwner")
        if owner is not None:
            name_elem = owner.find(".//reportingOwnerId/rptOwnerName")
            if name_elem is not None and name_elem.text:
                insider_name = name_elem.text.strip()

            rel = owner.find(".//reportingOwnerRelationship")
            if rel is not None:
                is_director = rel.findtext("isDirector", "0")
                is_officer = rel.findtext("isOfficer", "0")
                officer_title = rel.findtext("officerTitle", "")
                if is_director == "1":
                    insider_role = "Director"
                elif is_officer == "1":
                    insider_role = officer_title or "Officer"
                else:
                    insider_role = "10% Owner"

        # Tranzacții non-derivative
        best_purchase = None

        for txn in root.findall(".//nonDerivativeTransaction"):
            code_elem = txn.find(".//transactionCoding/transactionCode")
            if code_elem is None or not code_elem.text:
                continue

            code = code_elem.text.strip().upper()
            if code not in ("P", "S"):
                continue

            shares_elem = txn.find(".//transactionAmounts/transactionShares/value")
            price_elem = txn.find(".//transactionAmounts/transactionPricePerShare/value")
            date_elem = txn.find(".//transactionDate/value")

            try:
                shares = float(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
                price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
                date = date_elem.text.strip() if date_elem is not None and date_elem.text else ""
            except (ValueError, AttributeError):
                continue

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

        # Confidence
        val = best_purchase["total_value"]
        confidence = 6.0
        if val >= 1_000_000:    confidence = 9.0
        elif val >= 500_000:    confidence = 8.5
        elif val >= 200_000:    confidence = 8.0
        elif val >= 100_000:    confidence = 7.5
        elif val >= 50_000:     confidence = 7.0

        if any(t in insider_role for t in ("CEO", "President", "CFO", "CTO", "COO")):
            confidence = min(9.5, confidence + 0.5)

        accession = filing.get("accession", "")
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{filing.get('company_cik', '')}/{filing.get('accession_clean', '')}/{filing.get('xml_filename', '')}"

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

    except ET.ParseError:
        return None
    except Exception:
        return None


def get_insider_activity_for_ticker(ticker: str, days_back: int = 7) -> dict:
    """
    Helper: returnează activitatea insider pentru un ticker specific.
    """
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
