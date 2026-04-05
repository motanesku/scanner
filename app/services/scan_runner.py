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
    # 1) NEWS / TRIGGERS
    raw_news = collect_news_triggers()
    classified_triggers = classify_triggers(raw_news)

    # 2) FILINGS
    filings = collect_filings()
    parsed_filings = parse_filings(filings)

    # 3) BUILD OPPORTUNITIES
    mapped_opportunities = map_triggers_to_opportunities(classified_triggers)
    enriched_opportunities = enrich_opportunities_with_trigger_stack(mapped_opportunities)

    # 4) ticker universe
    tickers = []
    for opp in enriched_opportunities:
        if opp.ticker not in tickers:
            tickers.append(opp.ticker)

    if not tickers:
        tickers = ["SPY"]

    # 5) market data
    market_data = collect_market_data(tickers)

    # 6) parsed_news PER TICKER based on related triggers/theme
    parsed_news_input = []

    for opp in enriched_opportunities:
        related_triggers = [
            trig for trig in classified_triggers
            if trig.theme_hint == opp.theme
        ]

        if not related_triggers:
            parsed_news_input.append({
                "ticker": opp.ticker,
                "title": opp.theme,
                "summary": opp.theme,
                "source": "theme_fallback",
                "link": ""
            })
            continue

        for trig in related_triggers:
            parsed_news_input.append({
                "ticker": opp.ticker,
                "title": trig.headline,
                "summary": trig.headline,
                "source": "news_trigger",
                "link": ""
            })

    parsed_news = parse_news(parsed_news_input)

    # 7) final scoring
    final_opportunities = []

    for opp in enriched_opportunities:
        ticker = opp.ticker

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
            (catalyst_score * 0.35) +
            (narrative_score * 0.30) +
            (market_score * 0.20) +
            ((100 - risk_score) * 0.15),
            1
        )

        signal = determine_signal(final_score, risk_score)

        final_opportunities.append({
            "ticker": ticker,
            "company": opp.company_name,
            "theme": opp.theme,
            "subtheme": opp.subtheme,
            "role": opp.role,
            "positioning": opp.positioning,
            "market_cap_bucket": opp.market_cap_bucket,
            "score": final_score,
            "signal": signal,
            "catalyst_score": catalyst_score,
            "narrative_score": narrative_score,
            "market_score": market_score,
            "risk_score": risk_score,
            "why_now": opp.why_now or f"{opp.theme} is active and this name is mapped as a relevant beneficiary.",
            "why_this_name": opp.why_this_name or f"{opp.company_name} is positioned as {opp.positioning} within {opp.theme}.",
            "ai_verdict": opp.ai_verdict or f"{ticker} is a thematic candidate inside {opp.theme}.",
            "trigger_stack": opp.trigger_stack,
            "trigger_count": opp.trigger_count,
            "market_confirmation": opp.market_confirmation,
            "next_confirmations": opp.next_confirmations,
            "failure_modes": opp.failure_modes,
            "entry": None,
            "target": None,
            "market_data": market_data.get(ticker, {})
        })

    # 8) sort
    final_opportunities = sorted(
        final_opportunities,
        key=lambda x: x["score"],
        reverse=True
    )

    # 9) themes
    themes = build_theme_summary(final_opportunities)

    # 10) daily report
    daily_report = build_daily_report(final_opportunities, themes)

    # 11) final output
    final_result = {
        "summary": {
            "total_opportunities": len(final_opportunities),
            "total_themes": len(themes),
            "scan_status": "ok"
        },
        "opportunities": final_opportunities,
        "themes": themes,
        "daily_report": daily_report
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=2)

    return final_result


def determine_signal(score, risk_score):
    if score >= 80 and risk_score < 45:
        return "BUY"
    if score >= 65:
        return "WATCH"
    return "PASS"


def build_theme_summary(opportunities):
    theme_map = {}

    for opp in opportunities:
        theme = opp.get("theme", "General")
        if theme not in theme_map:
            theme_map[theme] = {
                "theme": theme,
                "strength": 0,
                "tickers": [],
                "count": 0
            }

        theme_map[theme]["tickers"].append(opp["ticker"])
        theme_map[theme]["strength"] += opp["score"]
        theme_map[theme]["count"] += 1

    result = []
    for theme, data in theme_map.items():
        avg_strength = round(data["strength"] / data["count"], 1) if data["count"] else 0
        result.append({
            "theme": theme,
            "strength": avg_strength,
            "tickers": list(set(data["tickers"]))
        })

    return sorted(result, key=lambda x: x["strength"], reverse=True)


def build_daily_report(opportunities, themes):
    top_ideas = opportunities[:3]
    top_themes = themes[:3]

    return {
        "headline": build_headline(top_themes),
        "top_ideas": [
            {
                "ticker": x["ticker"],
                "score": x["score"],
                "signal": x["signal"],
                "theme": x["theme"]
            }
            for x in top_ideas
        ],
        "focus": [
            "Watch for multi-trigger continuation setups",
            "Monitor filings for dilution or financing risk",
            "Track relative volume confirmation and thematic expansion"
        ]
    }


def build_headline(top_themes):
    if not top_themes:
        return "No dominant market narrative detected."

    strongest = top_themes[0]["theme"]
    return f"{strongest} is currently the strongest active market narrative."
