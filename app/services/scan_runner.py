# File: app/services/scan_runner.py

import json
from pathlib import Path
from app.config import OUTPUT_PATH

# Import minimal pentru mobil, doar funcționalități de bază
from app.collectors.sec_filings import collect_filings
from app.collectors.news_collector import collect_news
from app.collectors.market_data import collect_market_data
from app.parsers.filing_parser import parse_filings
from app.parsers.news_parser import parse_news
from app.scoring.catalyst_score import calculate_catalyst_score
from app.scoring.narrative_score import calculate_narrative_score

def run_scan():
    """
    Scanner real minimal pentru mobil:
    - colectează date reale
    - parsează
    - calculează scoruri
    - generează JSON valid
    """

    # 1️⃣ Colectare date
    filings = collect_filings()       # SEC filings
    news = collect_news()             # headlines relevante
    market = collect_market_data()    # OHLC + volume

    # 2️⃣ Parse
    parsed_filings = parse_filings(filings)
    parsed_news = parse_news(news)

    # 3️⃣ Calcul scoruri și oportunități
    opportunities = []
    for ticker in parsed_news.keys():
        catalyst = calculate_catalyst_score(ticker, parsed_filings, parsed_news, market)
        narrative = calculate_narrative_score(ticker, parsed_news)
        score = (catalyst + narrative) / 2  # simplificat pentru MVP

        opportunities.append({
            "ticker": ticker,
            "score": score,
            "catalyst": catalyst,
            "narrative": narrative,
            "entry": None,
            "target": None
        })

    # 4️⃣ Tematici
    themes = list(set([t.get("theme", "General") for n in parsed_news.values() for t in n]))

    # 5️⃣ Summary
    summary = {
        "total_opportunities": len(opportunities),
        "total_news": sum([len(n) for n in parsed_news.values()])
    }

    # 6️⃣ Scrie JSON
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "opportunities": opportunities,
            "themes": themes
        }, f, indent=2)

    return {
        "summary": summary,
        "opportunities": opportunities,
        "themes": themes
    }
