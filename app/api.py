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
