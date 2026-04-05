# File: app/services/scan_runner.py

import json
from app.config import OUTPUT_PATH

from app.collectors.news_collector import collect_news_triggers
from app.collectors.sec_filings import collect_filings
from app.collectors.market_data import collect_market_data

from app.parsers.news_parser import parse_news
from app.parsers.filing_parser import parse_filings

from app.engines.trigger_engine import classify_triggers
from app.engines.theme_mapper import map_triggers_to_opportunities
from app.engines.trigger_stack_builder import enrich_opportunities_with_trigger_stack

from app.scoring.catalyst_score import calculate_catalyst_score
from app.scoring.narrative_score import calculate_narrative_score
from app.scoring.market_score import calculate_market_score
from app.scoring.risk_score import calculate_risk_score


def run_scan():
    # 1) triggers
    raw_news = collect_news_triggers()
    classified_triggers = classify_triggers(raw_news)

    # 2) filings
    filings = collect_filings()
    parsed_filings = parse_filings(filings)

    # 3) opportunities
    mapped_opportunities = map_triggers_to_opportunities(classified_triggers)
    enriched_opportunities = enrich_opportunities_with_trigger_stack(mapped_opportunities)

    # 4) tickers
    tickers = list(set([opp.ticker for opp in enriched_opportunities]))
    if not tickers:
        tickers = ["SPY"]

    # 5) market data
    market_data = collect_market_data(tickers)

    # 6) parsed news
    parsed_news_input = []
    for opp in enriched_opportunities:
        for trig in classified_triggers:
            if trig.theme_hint == opp.theme:
                parsed_news_input.append({
                    "ticker": opp.ticker,
                    "title": trig.headline,
                    "summary": trig.headline,
                    "source": "news_trigger",
                    "link": ""
                })

    parsed_news = parse_news(parsed_news_input)

    # 7) scoring
    final_opportunities = []

    for opp in enriched_opportunities:
        ticker = opp.ticker
        ticker_news = parsed_news.get(ticker, [])

        direct_triggers = 0
        theme_triggers = 0

        for item in ticker_news:
            if ticker in item.get("title", "").upper():
                direct_triggers += 1
            else:
                theme_triggers += 1

        catalyst_score = calculate_catalyst_score(
            ticker=ticker,
            parsed_filings=parsed_filings,
            parsed_news=parsed_news,
            market_data=market_data
        )

        narrative_score = calculate_narrative_score(
            ticker=ticker,
            parsed_news=parsed_news
        )

        market_score = calculate_market_score(
            ticker=ticker,
            market_data=market_data
        )

        risk_score = calculate_risk_score(
            ticker=ticker,
            parsed_filings=parsed_filings,
            parsed_news=parsed_news
        )

        final_score = round(
            (catalyst_score * 0.4) +
            (narrative_score * 0.25) +
            (market_score * 0.2) +
            ((100 - risk_score) * 0.15),
            1
        )

        signal = determine_signal(final_score, risk_score, direct_triggers)

        final_opportunities.append({
            "ticker": ticker,
            "company": opp.company_name,
            "theme": opp.theme,
            "signal_origin": "direct" if direct_triggers else "theme",
            "direct_triggers": direct_triggers,
            "theme_triggers": theme_triggers,
            "score": final_score,
            "signal": signal,
            "catalyst_score": catalyst_score,
            "narrative_score": narrative_score,
            "market_score": market_score,
            "risk_score": risk_score,
            "why_now": opp.why_now,
            "trigger_stack": opp.trigger_stack,
            "market_data": market_data.get(ticker, {})
        })

    # 8) sort
    final_opportunities = sorted(
        final_opportunities,
        key=lambda x: x["score"],
        reverse=True
    )

    # 9) output
    result = {
        "summary": {
            "total_opportunities": len(final_opportunities),
            "scan_status": "ok"
        },
        "opportunities": final_opportunities
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


def determine_signal(score, risk_score, direct_triggers):
    if direct_triggers >= 1 and score >= 75 and risk_score < 50:
        return "BUY"

    if score >= 60:
        return "WATCH"

    return "PASS"
