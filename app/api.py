import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.services.scan_runner import run_scan
from app.config import OUTPUT_PATH

app = FastAPI(title="Scanner MVP API", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "scanner-mvp"}


@app.get("/api/scanner/results")
def get_results():
    if not Path(OUTPUT_PATH).exists():
        return JSONResponse(
            status_code=404,
            content={"error": "No scan results found yet."}
        )

    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@app.post("/api/scanner/run")
def run_scanner_now():
    result = run_scan()
    return {
        "status": "success",
        "message": "Scanner run completed successfully.",
        "summary": result.get("summary", {}),
        "opportunity_count": len(result.get("opportunities", [])),
        "theme_count": len(result.get("themes", []))
    }


@app.get("/")
def root():
    return {
        "service": "Scanner MVP API",
        "endpoints": [
            "/health",
            "/api/scanner/results",
            "/api/scanner/run"
        ]
    }
