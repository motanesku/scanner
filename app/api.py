import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.services.scan_runner import run_scan
from app.config import OUTPUT_PATH

app = FastAPI(title="Scanner MVP API", version="1.0.0")


# ── Health check ──────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "scanner-mvp"}


# ── Root ──────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "Scanner MVP API",
        "endpoints": [
            "/health",
            "/api/scanner/results",
            "/api/scanner/run",
            "/api/scanner/run-now",
            "/api/debug/insider-raw",
            "/api/debug/earnings-raw",
            "/api/debug/polygon",
        ]
    }


# ── Scanner endpoints ─────────────────────────────────────────────
@app.get("/api/scanner/results")
def get_results():
    try:
        if not Path(OUTPUT_PATH).exists():
            return JSONResponse(
                status_code=200,
                content={"status": "pending", "message": "No scan results yet. Run /api/scanner/run-now first."}
            )
        
        # Verifică dacă fișierul e valid și nevid
        if Path(OUTPUT_PATH).stat().st_size == 0:
            return JSONResponse(
                status_code=200,
                content={"status": "pending", "message": "Scan in progress..."}
            )

        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except json.JSONDecodeError:
        return JSONResponse(
            status_code=200,
            content={"status": "pending", "message": "Scan in progress or file corrupted."}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/scanner/run")
def run_scanner_now_post():
    result = run_scan()
    return {
        "status": "success",
        "message": "Scanner run completed successfully.",
        "summary": result.get("summary", {}),
        "opportunity_count": len(result.get("opportunities", [])),
        "theme_count": len(result.get("themes", []))
    }


import threading
import traceback

# Variabilă globală pentru status scan
scan_status = {"running": False, "last_error": None, "last_run": None}

@app.get("/api/scanner/run-now")
def run_scanner_now_get():
    def run_in_background():
        global scan_status
        scan_status["running"] = True
        scan_status["last_error"] = None
        try:
            run_scan()
            scan_status["last_run"] = "success"
        except Exception as e:
            scan_status["last_error"] = traceback.format_exc()
            scan_status["last_run"] = "error"
        finally:
            scan_status["running"] = False
    
    thread = threading.Thread(target=run_in_background, daemon=True)
    thread.start()
    
    return {"status": "started", "message": "Check /api/scanner/status for progress."}


@app.get("/api/scanner/status")
def scanner_status():
    return {
        "running": scan_status["running"],
        "last_run": scan_status["last_run"],
        "last_error": scan_status["last_error"],
    }
    
# ── Debug endpoints (permanente) ──────────────────────────────────

@app.get("/api/debug/polygon")
def debug_polygon():
    """Market data via Polygon — confirmat funcțional"""
    from app.collectors.market_data import collect_market_data
    data = collect_market_data(["NVDA", "AMD", "TSLA"])
    return data


@app.get("/api/debug/insider-raw")
def debug_insider_raw():
    """Testează EFTS fetch + XML parsing Form 4"""
    from app.collectors.insider_collector import _fetch_recent_form4_filings, _parse_form4_filing

    filings = _fetch_recent_form4_filings(days_back=2)

    if not filings:
        return {"error": "No filings found", "count": 0}

    results = []
    for filing in filings[:5]:
        parsed = _parse_form4_filing(filing)
        results.append({
            "filing": filing,
            "parsed": parsed,
            "xml_url": (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{filing.get('company_cik')}/"
                f"{filing.get('accession_clean')}/"
                f"{filing.get('xml_filename')}"
            )
        })

    return {
        "total_filings_found": len(filings),
        "sample_parsed": results
    }


@app.get("/api/debug/earnings-raw")
def debug_earnings_raw():
    """Testează SEC EDGAR 8-K earnings collector"""
    from app.collectors.earnings_collector import get_earnings_calendar
    results = get_earnings_calendar()
    return {
        "count": len(results),
        "sample": dict(list(results.items())[:10])
    }


@app.get("/api/debug/insider")
def debug_insider():
    """Rulează insider collector complet și returnează triggere"""
    from app.collectors.insider_collector import collect_insider_triggers
    triggers = collect_insider_triggers(days_back=3)
    return {
        "count": len(triggers),
        "sample": triggers[:5]
    }

@app.get("/api/debug/insider-xml")
def debug_insider_xml():
    import requests, re
    import xml.etree.ElementTree as ET
    
    headers = {"User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com"}
    
    test_urls = [
        ("crdo", "https://www.sec.gov/Archives/edgar/data/1807794/000162828026023885/wk-form4_1775505331.xml"),
        ("ryde", "https://www.sec.gov/Archives/edgar/data/1971115/000149315226015387/ownership.xml"),
        ("howmet", "https://www.sec.gov/Archives/edgar/data/4281/000110465926040184/tm2611291-1_4seq1.xml"),
    ]
    
    results = {}
    for name, url in test_urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.ok:
                # Arată primii 500 chars din XML brut
                raw = r.text[:500]
                # Încearcă namespace cleanup
                xml_clean = re.sub(r'\sxmlns[^"]*"[^"]*"', '', r.text)
                xml_clean = re.sub(r'<[^>]+:', '<', xml_clean)
                xml_clean = re.sub(r'</[^>]+:', '</', xml_clean)
                # Încearcă să parseze
                try:
                    root = ET.fromstring(xml_clean)
                    ticker_elem = root.find(".//issuerTradingSymbol")
                    txn_count = len(root.findall(".//nonDerivativeTransaction"))
                    results[name] = {
                        "status": r.status_code,
                        "raw_start": raw,
                        "parse": "OK",
                        "ticker_found": ticker_elem.text if ticker_elem is not None else "NOT FOUND",
                        "txn_count": txn_count,
                        "root_tag": root.tag,
                        "children": [c.tag for c in list(root)[:5]]
                    }
                except Exception as e:
                    results[name] = {
                        "status": r.status_code,
                        "raw_start": raw,
                        "parse": f"ERROR: {e}"
                    }
            else:
                results[name] = {"status": r.status_code}
        except Exception as e:
            results[name] = {"error": str(e)}
    
    return results

@app.get("/api/debug/insider-txn")
def debug_insider_txn():
    import requests, re
    import xml.etree.ElementTree as ET
    
    headers = {"User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com"}
    url = "https://www.sec.gov/Archives/edgar/data/1807794/000162828026023885/wk-form4_1775505331.xml"
    
    r = requests.get(url, headers=headers, timeout=10)
    xml_clean = re.sub(r'\sxmlns[^"]*"[^"]*"', '', r.text)
    xml_clean = re.sub(r'<[^>]+:', '<', xml_clean)
    xml_clean = re.sub(r'</[^>]+:', '</', xml_clean)
    
    root = ET.fromstring(xml_clean)
    
    # Dump toate tranzacțiile cu toate câmpurile
    txns = []
    for txn in root.findall(".//nonDerivativeTransaction"):
        txn_data = {}
        for child in txn.iter():
            if child.text and child.text.strip():
                txn_data[child.tag] = child.text.strip()
        txns.append(txn_data)
    
    deriv_txns = []
    for txn in root.findall(".//derivativeTransaction"):
        txn_data = {}
        for child in txn.iter():
            if child.text and child.text.strip():
                txn_data[child.tag] = child.text.strip()
        deriv_txns.append(txn_data)
    
    return {
        "non_derivative": txns,
        "derivative": deriv_txns
    }

@app.get("/api/debug/universe")
def debug_universe():
    """Statusul ticker universe curent"""
    from app.engines.entity_resolver import get_universe
    u = get_universe()
    return {
        "count": u.get("count", 0),
        "alias_count": u.get("alias_count", 0),
        "built_at": u.get("built_at"),
        "sample_tickers": list(u.get("tickers", {}).keys())[:10],
        "sample_aliases": list(u.get("alias_index", {}).items())[:10],
    }
 
@app.get("/api/admin/refresh-universe")
def refresh_universe_endpoint():
    """Forțează re-descărcarea ticker universe din Polygon"""
    from app.engines.entity_resolver import refresh_universe
    u = refresh_universe()
    return {
        "status": "ok",
        "count": u.get("count", 0),
        "alias_count": u.get("alias_count", 0),
        "built_at": u.get("built_at"),
    }

@app.get("/api/debug/polygon-grouped")
def debug_polygon_grouped():
    import requests
    from datetime import datetime, timezone, timedelta
    
    # Data de ieri (markets closed)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    r = requests.get(
        f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{yesterday}",
        params={"apiKey": "l1oXhYe6KwprlwpIs8DUakKIj7w9SUmx", "adjusted": "true"},
        timeout=30
    )
    
    return {
        "status": r.status_code,
        "date": yesterday,
        "count": r.json().get("resultsCount", 0) if r.ok else 0,
        "sample": r.json().get("results", [])[:3] if r.ok else r.text[:200]
    }

@app.get("/api/debug/universe")
def debug_universe():
    from app.engines.entity_resolver import get_universe
    u = get_universe()
    tickers = u.get("tickers", {})
    
    # Verifică dacă SIC e prezent
    sample_with_sic = []
    for ticker, info in list(tickers.items())[:5]:
        sample_with_sic.append({
            "ticker": ticker,
            "name": info.get("name"),
            "sic_code": info.get("sic_code"),
            "sic_description": info.get("sic_description"),
        })
    
    return {
        "count": u.get("count", 0),
        "alias_count": u.get("alias_count", 0),
        "built_at": u.get("built_at"),
        "has_sic": any(
            info.get("sic_code") 
            for info in list(tickers.values())[:100]
        ),
        "sample_with_sic": sample_with_sic,
    }
