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
