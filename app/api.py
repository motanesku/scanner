import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.services.scan_runner import run_scan
from app.config import OUTPUT_PATH

app = FastAPI(title="Scanner MVP API", version="1.0.0")


# --- Health check ---
@app.get("/health")
def health():
    return {"status": "ok", "service": "scanner-mvp"}


# --- Get results from latest scan ---
@app.get("/api/scanner/results")
def get_results():
    try:
        if not Path(OUTPUT_PATH).exists():
            return JSONResponse(
                status_code=404,
                content={"error": f"No scan results found yet at {OUTPUT_PATH}"}
            )

        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "output_path": str(OUTPUT_PATH)}
        )


# --- Original POST endpoint (Railway / API clients) ---
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


# --- Mobile-friendly GET to run scanner ---
@app.get("/api/scanner/run-now")
def run_scanner_now_get():
    """
    Endpoint temporar pentru test mobil: rulează scannerul și returnează rezultatul.
    """
    result = run_scan()
    return {
        "status": "success",
        "summary": result.get("summary", {}),
        "opportunities": result.get("opportunities", []),
        "themes": result.get("themes", [])
    }


# --- Root endpoint ---
@app.get("/")
def root():
    return {
        "service": "Scanner MVP API",
        "endpoints": [
            "/health",
            "/api/scanner/results",
            "/api/scanner/run",
            "/api/scanner/run-now"
        ]
    }

@app.get("/api/debug/insider")
def debug_insider():
    from app.collectors.insider_collector import collect_insider_triggers
    triggers = collect_insider_triggers(days_back=3)
    return {
        "count": len(triggers),
        "sample": triggers[:3]
    }

@app.get("/api/debug/earnings")
def debug_earnings():
    from app.collectors.earnings_collector import get_earnings_calendar
    results = get_earnings_calendar(window_days=14)
    return {
        "count": len(results),
        "results": results
    }

@app.get("/api/debug/polygon")
def debug_polygon():
    from app.collectors.market_data import collect_market_data
    data = collect_market_data(["NVDA", "AMD", "TSLA"])
    return data

@app.get("/api/debug/insider-raw")
def debug_insider_raw():
    import requests
    from datetime import datetime, timezone, timedelta
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    
    headers = {"User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com"}
    
    # Test 1: EFTS search
    r1 = requests.get(
        "https://efts.sec.gov/LATEST/search-index",
        headers=headers,
        params={"forms": "4", "dateRange": "custom", "startdt": yesterday, "enddt": today},
        timeout=15
    )
    
    return {
        "efts_status": r1.status_code,
        "efts_sample": r1.json() if r1.ok else r1.text[:500]
    }

@app.get("/api/debug/earnings-raw")
def debug_earnings_raw():
    import requests
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    r = requests.get(
        "https://query1.finance.yahoo.com/v7/finance/quote",
        headers=headers,
        params={"symbols": "NVDA,MSFT,AAPL", "fields": "earningsTimestamp,shortName"},
        timeout=15
    )
    
    return {
        "status": r.status_code,
        "response": r.json() if r.ok else r.text[:500]
    }
@app.get("/api/debug/earnings-polygon")
def debug_earnings_polygon():
    import requests
    from datetime import datetime, timezone, timedelta
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    future = (datetime.now(timezone.utc) + timedelta(days=21)).strftime("%Y-%m-%d")
    
    r = requests.get(
        "https://api.polygon.io/vX/reference/financials",
        params={
            "apiKey": "l1oXhYe6KwprlwpIs8DUakKIj7w9SUmx",
            "filing_date.gte": today,
            "filing_date.lte": future,
            "limit": 10
        },
        timeout=15
    )
    
    return {
        "status": r.status_code,
        "response": r.json() if r.ok else r.text[:500]
    }
@app.get("/api/debug/earnings-raw2")
def debug_earnings_raw2():
    import requests
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    
    # v8/finance/chart returnează earningsTimestamp în meta
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/NVDA",
        headers=headers,
        params={"interval": "1d", "range": "5d"},
        timeout=15
    )
    
    return {
        "status": r.status_code,
        "earnings_ts": r.json().get("chart", {}).get("result", [{}])[0].get("meta", {}).get("earningsTimestamp") if r.ok else None,
        "raw": r.json() if r.ok else r.text[:300]
    }    

@app.get("/api/debug/earnings-raw3")
def debug_earnings_raw3():
    import requests
    from datetime import datetime, timezone
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    
    # Tickere cu earnings probabile în aprilie/mai
    test_tickers = ["JPM", "GS", "MS", "BAC", "NFLX", "TSLA", "ASML", "TSM"]
    results = {}
    
    for ticker in test_tickers:
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                headers=headers,
                params={"interval": "1d", "range": "5d"},
                timeout=10
            )
            if r.ok:
                meta = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
                ts = meta.get("earningsTimestamp")
                results[ticker] = {
                    "earningsTimestamp": ts,
                    "earningsDate": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else None
                }
        except Exception as e:
            results[ticker] = {"error": str(e)}
    
    return results
    
@app.get("/api/debug/earnings-polygon2")
def debug_earnings_polygon2():
    import requests
    from datetime import datetime, timezone, timedelta
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    future = (datetime.now(timezone.utc) + timedelta(days=21)).strftime("%Y-%m-%d")
    
    # Endpoint corect pentru earnings calendar
    r = requests.get(
        "https://api.polygon.io/v2/reference/earnings",
        params={
            "apiKey": "l1oXhYe6KwprlwpIs8DUakKIj7w9SUmx",
            "date.gte": today,
            "date.lte": future,
            "limit": 20
        },
        timeout=15
    )
    
    # Alternativ: earnings per ticker specific
    r2 = requests.get(
        "https://api.polygon.io/v3/reference/dividends",
        params={"apiKey": "l1oXhYe6KwprlwpIs8DUakKIj7w9SUmx", "ticker": "NVDA"},
        timeout=15
    )
    
    return {
        "earnings_status": r.status_code,
        "earnings_response": r.json() if r.ok else r.text[:300],
        "div_status": r2.status_code
    }

# Adaugă acestea la sfârșitul app/api.py

@app.get("/api/debug/insider-raw")
def debug_insider_raw():
    """Testează EFTS fetch + XML parsing Form 4"""
    from app.collectors.insider_collector import _fetch_recent_form4_filings, _parse_form4_filing
    
    filings = _fetch_recent_form4_filings(days_back=2)
    
    if not filings:
        return {"error": "No filings found", "count": 0}
    
    # Încearcă să parseze primele 5
    results = []
    for filing in filings[:5]:
        parsed = _parse_form4_filing(filing)
        results.append({
            "filing": filing,
            "parsed": parsed,
            "xml_url": f"https://www.sec.gov/Archives/edgar/data/{filing.get('company_cik')}/{filing.get('accession_clean')}/{filing.get('xml_filename')}"
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
    
@app.get("/api/debug/earnings-sec")
def debug_earnings_sec():
    """Earnings recente din SEC EDGAR 8-K Item 2.02"""
    import requests
    from datetime import datetime, timezone, timedelta
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    
    headers = {"User-Agent": "scanner-mvp/1.0 danut.fagadau@gmail.com"}
    
    # 8-K cu Item 2.02 = Results of Operations (earnings announcement)
    r = requests.get(
        "https://efts.sec.gov/LATEST/search-index",
        headers=headers,
        params={
            "forms": "8-K",
            "dateRange": "custom",
            "startdt": start,
            "enddt": today,
            "hits.hits.total": 20,
        },
        timeout=15
    )
    
    if not r.ok:
        return {"status": r.status_code, "error": r.text[:200]}
    
    hits = r.json().get("hits", {}).get("hits", [])
    results = []
    for h in hits[:10]:
        src = h.get("_source", {})
        results.append({
            "company": src.get("display_names", []),
            "items": src.get("items", []),
            "file_date": src.get("file_date"),
            "id": h.get("_id")
        })
    
    return {"count": len(hits), "sample": results}
