# File: app/collectors/insider_collector.py
#
# Colectează Form 4 (insider transactions) din SEC EDGAR.
# Fără API key, fără rate limit semnificativ.
# Endpoint oficial: https://efts.sec.gov/LATEST/search-index
#
# Ce returnează:
# - tickere cu insider buying recent (ultimele 1-3 zile)
# - suma tranzacției
# - numele insider-ului
# - tipul tranzacției (P = purchase, S = sale)
#
# Folosit de trigger_engine ca Tier 1 Direct Trigger.

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from app.utils.logger import log_info, log_warn, log_error

# SEC cere User-Agent cu email real
SEC_HEADERS = {
    "User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

# Threshold minim pentru a considera un insider buy relevant
MIN_BUY_AMOUNT_USD = 50_000  # $50K minim


def collect_insider_triggers(days_back: int = 2) -> list[dict]:
    """
    Colectează Form 4 recente din SEC EDGAR.
    Returnează lista de triggere cu insider buying semnificativ.

    Fiecare trigger:
    {
        "ticker": "CRDO",
        "company_name": "Credo Technology Group",
        "insider_name": "John Smith",
        "insider_role": "Director",
        "transaction_type": "P",       # P=Purchase, S=Sale
        "shares": 10000,
        "price_per_share": 38.5,
        "total_value": 385000,
        "transaction_date": "2026-04-06",
        "filing_url": "https://...",
        "signal": "insider_buy",
        "tier": 1,
        "confidence": 8.5
    }
    """
    log_info(f"[Form4] Collecting insider transactions (last {days_back} days)...")

    # Pas 1: obține lista de Form 4 recente din EDGAR full-text search
    filings = _fetch_recent_form4_filings(days_back)
    if not filings:
        log_warn("[Form4] No recent Form 4 filings found.")
        return []

    log_info(f"[Form4] Found {len(filings)} Form 4 filings to process.")

    # Pas 2: pentru fiecare filing, parsează XML-ul și extrage tranzacția
    triggers = []
    processed = 0

    for filing in filings[:50]:  # max 50 filings per rulare
        try:
            trigger = _parse_form4_filing(filing)
            if trigger:
                triggers.append(trigger)
                processed += 1
        except Exception as e:
            log_warn(f"[Form4] Error parsing filing {filing.get('accession', '')}: {e}")
            continue

    # Pas 3: filtrează doar insider buys semnificative
    buy_triggers = [
        t for t in triggers
        if t["transaction_type"] == "P"
        and t["total_value"] >= MIN_BUY_AMOUNT_USD
    ]

    log_info(f"[Form4] Processed {processed} filings → {len(buy_triggers)} significant insider buys.")
    return buy_triggers


def _fetch_recent_form4_filings(days_back: int) -> list[dict]:
    """
    Folosește EDGAR EFTS (full-text search) pentru Form 4 recente.
    """
    today = datetime.now(timezone.utc)
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "forms": "4",
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": end_date,
        "hits.hits._source": "period_of_report,entity_name,file_date,accession_no",
        "hits.hits.total": 100,
    }

    try:
        response = requests.get(
            url,
            headers=SEC_HEADERS,
            params=params,
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", {}).get("hits", [])
        filings = []

        for hit in hits:
            source = hit.get("_source", {})
            accession = source.get("accession_no", "").replace("-", "")
            entity = source.get("entity_name", "")
            file_date = source.get("file_date", "")

            if accession:
                filings.append({
                    "accession": accession,
                    "entity_name": entity,
                    "file_date": file_date,
                })

        return filings

    except Exception as e:
        log_error(f"[Form4] EFTS fetch error: {e}")
        # Fallback: încearcă RSS feed EDGAR
        return _fetch_form4_via_rss(days_back)


def _fetch_form4_via_rss(days_back: int) -> list[dict]:
    """
    Fallback: RSS feed EDGAR pentru Form 4.
    Mai simplu dar mai puțin precis.
    """
    url = "https://www.sec.gov/cgi-bin/browse-edgar"
    params = {
        "action": "getcurrent",
        "type": "4",
        "dateb": "",
        "owner": "include",
        "count": "40",
        "search_text": "",
        "output": "atom"
    }

    try:
        response = requests.get(
            url,
            headers=SEC_HEADERS,
            params=params,
            timeout=20
        )
        response.raise_for_status()

        # Parsează Atom XML
        filings = []
        root = ET.fromstring(response.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns)
            link_elem = entry.find("atom:link", ns)
            link = link_elem.get("href", "") if link_elem is not None else ""
            updated = entry.findtext("atom:updated", "", ns)

            # Extrage accession number din link
            accession = ""
            if "/Archives/edgar/data/" in link:
                parts = link.split("/")
                for part in parts:
                    if len(part) == 18 and part.replace("-", "").isdigit():
                        accession = part.replace("-", "")
                        break

            if accession:
                filings.append({
                    "accession": accession,
                    "entity_name": title,
                    "file_date": updated[:10] if updated else "",
                    "filing_url": link
                })

        log_info(f"[Form4] RSS fallback: found {len(filings)} filings.")
        return filings

    except Exception as e:
        log_error(f"[Form4] RSS fallback error: {e}")
        return []


def _parse_form4_filing(filing: dict) -> dict | None:
    """
    Descarcă și parsează XML-ul unui Form 4 de pe EDGAR.

    Form 4 XML structure:
    - issuerTradingSymbol → ticker
    - reportingOwnerRelationship → rol insider
    - nonDerivativeTransaction → tranzacție acțiuni obișnuite
      - transactionCode → P (purchase) sau S (sale)
      - transactionShares → număr acțiuni
      - transactionPricePerShare → preț
    """
    accession = filing.get("accession", "")
    if not accession or len(accession) < 18:
        return None

    # Construiește URL-ul pentru XML-ul Form 4
    # Format accession: 0001234567-26-000001 → 0001234567/26/000001
    acc_formatted = f"{accession[:10]}-{accession[10:12]}-{accession[12:]}"
    acc_path = acc_formatted.replace("-", "")

    # Index al filing-ului
    index_url = f"https://www.sec.gov/Archives/edgar/data/{_extract_cik(acc_formatted)}/{acc_path}/{acc_formatted}-index.htm"

    # Alternativ: caută XML direct
    xml_url = f"https://www.sec.gov/Archives/edgar/data/{_extract_cik(acc_formatted)}/{acc_path}/{acc_formatted}.xml"

    try:
        response = requests.get(xml_url, headers=SEC_HEADERS, timeout=15)
        if response.status_code != 200:
            # Încearcă să găsești XML-ul din index
            return _parse_form4_from_index(acc_formatted)

        return _extract_form4_data(response.text, filing, acc_formatted)

    except Exception:
        return None


def _parse_form4_from_index(accession_formatted: str) -> dict | None:
    """
    Găsește URL-ul XML din pagina de index a filing-ului.
    """
    cik = _extract_cik(accession_formatted)
    acc_path = accession_formatted.replace("-", "")
    index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4&dateb=&owner=include&count=1&search_text="

    try:
        # Caută în EDGAR submissions API — mai fiabil
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
        response = requests.get(submissions_url, headers=SEC_HEADERS, timeout=15)
        if not response.ok:
            return None

        data = response.json()
        filings = data.get("filings", {}).get("recent", {})

        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form == "4" and i < len(accessions):
                if accessions[i].replace("-", "") == acc_path:
                    doc = primary_docs[i] if i < len(primary_docs) else ""
                    if doc.endswith(".xml"):
                        xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_path}/{doc}"
                        resp = requests.get(xml_url, headers=SEC_HEADERS, timeout=15)
                        if resp.ok:
                            return _extract_form4_data(resp.text, {"accession": acc_path, "entity_name": data.get("name", "")}, accessions[i])

        return None
    except Exception:
        return None


def _extract_form4_data(xml_text: str, filing: dict, accession: str) -> dict | None:
    """
    Parsează XML-ul Form 4 și extrage datele relevante.
    """
    try:
        root = ET.fromstring(xml_text)

        # Ticker
        ticker = ""
        issuer = root.find(".//issuer")
        if issuer is not None:
            ticker_elem = issuer.find("issuerTradingSymbol")
            ticker = ticker_elem.text.strip().upper() if ticker_elem is not None and ticker_elem.text else ""
            company_name_elem = issuer.find("issuerName")
            company_name = company_name_elem.text.strip() if company_name_elem is not None and company_name_elem.text else filing.get("entity_name", "")
        else:
            company_name = filing.get("entity_name", "")

        if not ticker:
            return None

        # Insider info
        owner = root.find(".//reportingOwner")
        insider_name = ""
        insider_role = ""
        if owner is not None:
            id_elem = owner.find(".//reportingOwnerId/rptOwnerName")
            insider_name = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

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

        # Tranzacții non-derivative (acțiuni obișnuite)
        total_purchase_value = 0.0
        total_shares = 0
        transaction_type = ""
        transaction_date = ""
        price_per_share = 0.0

        for txn in root.findall(".//nonDerivativeTransaction"):
            code_elem = txn.find(".//transactionCoding/transactionCode")
            if code_elem is None or code_elem.text is None:
                continue

            code = code_elem.text.strip().upper()

            # P = Purchase open market, ne interesează
            # S = Sale, notăm dar nu e trigger bullish
            # A = Award (grant), ignorăm
            if code not in ("P", "S"):
                continue

            shares_elem = txn.find(".//transactionAmounts/transactionShares/value")
            price_elem = txn.find(".//transactionAmounts/transactionPricePerShare/value")
            date_elem = txn.find(".//transactionDate/value")

            shares = float(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
            price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
            date = date_elem.text.strip() if date_elem is not None and date_elem.text else ""

            value = shares * price

            if code == "P" and value > total_purchase_value:
                total_purchase_value = value
                total_shares = int(shares)
                transaction_type = "P"
                transaction_date = date
                price_per_share = price

        # Nu avem date suficiente
        if not transaction_type or total_shares == 0:
            return None

        # Calculează confidence în funcție de valoare
        confidence = 6.0
        if total_purchase_value >= 1_000_000:
            confidence = 9.0
        elif total_purchase_value >= 500_000:
            confidence = 8.5
        elif total_purchase_value >= 200_000:
            confidence = 8.0
        elif total_purchase_value >= 100_000:
            confidence = 7.5
        elif total_purchase_value >= 50_000:
            confidence = 7.0

        # Director/CEO buy e mai important decât 10% owner
        if "CEO" in insider_role or "President" in insider_role:
            confidence = min(9.5, confidence + 0.5)

        filing_url = f"https://www.sec.gov/Archives/edgar/data/{_extract_cik(accession)}/{accession.replace('-', '')}/{accession}-index.htm"

        return {
            "ticker": ticker,
            "company_name": company_name,
            "insider_name": insider_name,
            "insider_role": insider_role,
            "transaction_type": transaction_type,
            "shares": total_shares,
            "price_per_share": round(price_per_share, 2),
            "total_value": round(total_purchase_value, 2),
            "transaction_date": transaction_date,
            "filing_url": filing_url,
            "signal": "insider_buy" if transaction_type == "P" else "insider_sell",
            "tier": 1,
            "confidence": confidence,
        }

    except ET.ParseError:
        return None
    except Exception:
        return None


def _extract_cik(accession: str) -> str:
    """
    Extrage CIK din accession number.
    Format: XXXXXXXXXX-YY-ZZZZZZ → primele 10 cifre sunt CIK
    """
    clean = accession.replace("-", "")
    return str(int(clean[:10]))  # elimină leading zeros


def get_insider_activity_for_ticker(ticker: str, days_back: int = 7) -> dict:
    """
    Helper: returnează activitatea insider pentru un ticker specific.
    Folosit de trigger_stack_builder pentru enrichment.
    """
    triggers = collect_insider_triggers(days_back=days_back)

    ticker_triggers = [t for t in triggers if t.get("ticker") == ticker.upper()]

    if not ticker_triggers:
        return {
            "has_insider_buy": False,
            "headline": "",
            "confidence": 0.0,
            "details": []
        }

    # Cel mai mare buy
    best = max(ticker_triggers, key=lambda x: x["total_value"])

    return {
        "has_insider_buy": best["transaction_type"] == "P",
        "headline": (
            f"Insider buy: {best['insider_name']} ({best['insider_role']}) "
            f"— ${best['total_value']:,.0f} @ ${best['price_per_share']}"
        ),
        "confidence": best["confidence"],
        "details": ticker_triggers
    }
