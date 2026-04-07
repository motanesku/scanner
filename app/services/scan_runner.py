# File: app/services/scan_runner.py

import json
from app.config import OUTPUT_PATH

from app.collectors.news_collector import collect_news_triggers
from app.collectors.sec_filings import collect_filings
from app.collectors.market_data import collect_market_data
from app.collectors.insider_collector import collect_insider_triggers
from app.collectors.earnings_collector import get_earnings_calendar

from app.parsers.news_parser import parse_news
from app.parsers.filing_parser import parse_filings

from app.engines.trigger_engine import classify_triggers
from app.engines.theme_mapper import map_triggers_to_opportunities
from app.engines.trigger_stack_builder import enrich_opportunities_with_trigger_stack

from app.scoring.catalyst_score import calculate_catalyst_score
from app.scoring.narrative_score import calculate_narrative_score
from app.scoring.market_score import calculate_market_score
from app.scoring.risk_score import calculate_risk_score

from app.utils.logger import log_info, log_success


def run_scan():
    log_info("Starting scan pipeline...")

    # ── 1. Triggere din știri (RSS) ───────────────────────────────
    raw_news = collect_news_triggers()
    classified_triggers = classify_triggers(raw_news)
    log_info(f"[Scan] News triggers: {len(classified_triggers)}")

    # ── 2. Filing-uri SEC (8-K, etc.) ────────────────────────────
    filings = collect_filings()
    parsed_filings = parse_filings(filings)
    log_info(f"[Scan] SEC filings: {len(parsed_filings)}")

    # ── 2b. Insider triggers Form 4 ──────────────────────────────
    insider_triggers = collect_insider_triggers(days_back=2)
    log_info(f"[Scan] Insider triggers (Form 4): {len(insider_triggers)}")

    # ── 2c. Earnings triggers 8-K ────────────────────────────────
    earnings_triggers = get_earnings_calendar()
    log_info(f"[Scan] Earnings triggers (8-K): {len(earnings_triggers)}")

    # ── 3. Oportunități mapate EXCLUSIV din triggere reale ────────
    mapped_opportunities = map_triggers_to_opportunities(
        classified_triggers,
        insider_triggers=insider_triggers,
        earnings_triggers=earnings_triggers,
    )
    enriched_opportunities = enrich_opportunities_with_trigger_stack(
        mapped_opportunities,
        insider_triggers=insider_triggers
    )
    log_info(f"[Scan] Opportunities after enrichment: {len(enriched_opportunities)}")

    # ── 4. Univers tickere ────────────────────────────────────────
    tickers = list({opp.ticker for opp in enriched_opportunities})
    if not tickers:
        tickers = ["SPY"]

    # ── 5. Market data ────────────────────────────────────────────
    market_data = collect_market_data(tickers)

    # ── 6. Parsed news per ticker ────────────────────────────────
    parsed_news_input = []
    seen_news_per_ticker = set()

    for opp in enriched_opportunities:
        related_triggers = [
            trig for trig in classified_triggers
            if trig.theme_hint == opp.theme
        ]

        if not related_triggers:
            key = (opp.ticker, opp.theme, "fallback")
            if key not in seen_news_per_ticker:
                seen_news_per_ticker.add(key)
                parsed_news_input.append({
                    "ticker": opp.ticker,
                    "title": opp.theme,
                    "summary": opp.theme,
                    "source": "theme_fallback",
                    "link": ""
                })
            continue

        for trig in related_triggers:
            key = (opp.ticker, trig.headline)
            if key in seen_news_per_ticker:
                continue
            seen_news_per_ticker.add(key)
            parsed_news_input.append({
                "ticker": opp.ticker,
                "title": trig.headline,
                "summary": trig.headline,
                "source": "news_trigger",
                "link": ""
            })

    parsed_news = parse_news(parsed_news_input)

    # ── 7. Scoring final ──────────────────────────────────────────
    final_opportunities = []

    for opp in enriched_opportunities:
        ticker = opp.ticker
        ticker_news = parsed_news.get(ticker, [])

        direct_triggers = 0
        theme_triggers = 0

        for item in ticker_news:
            title_upper = item.get("title", "").upper()
            company_upper = opp.company_name.upper()
            if ticker in title_upper or company_upper in title_upper:
                direct_triggers += 1
            else:
                theme_triggers = 1

        confirmation_triggers = 0

        for stack_item in opp.trigger_stack:
            if "Earnings" in stack_item:
                confirmation_triggers += 1

        md = market_data.get(ticker, {})
        if md.get("status") == "ok":
            if md.get("volume") and md.get("avg_volume_5d"):
                if md["avg_volume_5d"] > 0 and md["volume"] > md["avg_volume_5d"] * 1.5:
                    confirmation_triggers += 1
            if md.get("price") and md.get("previous_close"):
                if md["price"] > md["previous_close"]:
                    confirmation_triggers += 1

        # Insider buy ca direct trigger
        has_insider_buy = any("Insider Buy" in s for s in opp.trigger_stack)
        if has_insider_buy:
            direct_triggers += 1

        # Scoruri cu insider_triggers pasat explicit
        catalyst_score = calculate_catalyst_score(
            ticker=ticker,
            parsed_filings=parsed_filings,
            parsed_news=parsed_news,
            market_data=market_data,
            insider_triggers=insider_triggers   # ← nou
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
            (catalyst_score * 0.40) +
            (narrative_score * 0.25) +
            (market_score * 0.20) +
            ((100 - risk_score) * 0.15),
            1
        )

        signal_origin = "direct" if direct_triggers >= 1 else "theme"
        signal = determine_signal(
            score=final_score,
            risk_score=risk_score,
            direct_triggers=direct_triggers,
            confirmation_triggers=confirmation_triggers
        )

        why_now = build_why_now(
            signal_origin=signal_origin,
            ticker=ticker,
            company=opp.company_name,
            theme=opp.theme,
            has_insider=has_insider_buy
        )

        # Insider info pentru card
        insider_detail = next(
            (t for t in insider_triggers
             if t.get("ticker", "").upper() == ticker
             and t.get("transaction_type") == "P"),
            None
        )

        final_opportunities.append({
            "ticker": ticker,
            "company": opp.company_name,
            "theme": opp.theme,
            "subtheme": opp.subtheme,
            "role": opp.role,
            "positioning": opp.positioning,
            "market_cap_bucket": opp.market_cap_bucket,

            "signal_origin": signal_origin,
            "direct_triggers": direct_triggers,
            "theme_triggers": theme_triggers,
            "confirmation_triggers": confirmation_triggers,

            "score": final_score,
            "signal": signal,

            "catalyst_score": catalyst_score,
            "narrative_score": narrative_score,
            "market_score": market_score,
            "risk_score": risk_score,

            "why_now": why_now,
            "why_this_name": (
                f"{opp.company_name} is mapped as a relevant "
                f"{opp.role.lower()} in {opp.theme}."
            ),
            "ai_verdict": "",

            "trigger_stack": opp.trigger_stack,
            "market_confirmation": opp.market_confirmation,
            "next_confirmations": opp.next_confirmations,
            "failure_modes": opp.failure_modes,

            # Insider detalii pentru card UI
            "insider": {
                "name": insider_detail.get("insider_name", ""),
                "role": insider_detail.get("insider_role", ""),
                "value": insider_detail.get("total_value", 0),
                "date": insider_detail.get("transaction_date", ""),
                "filing_url": insider_detail.get("filing_url", ""),
            } if insider_detail else None,

            "entry": None,
            "target": None,
            "market_data": md
        })

    # ── 8. Sortare ────────────────────────────────────────────────
    final_opportunities = sorted(
        final_opportunities,
        key=lambda x: x["score"],
        reverse=True
    )

    # ── 9. Theme summary ──────────────────────────────────────────
    themes = build_theme_summary(final_opportunities)

    # ── 10. Daily report ──────────────────────────────────────────
    daily_report = build_daily_report(final_opportunities, themes)

    # ── 11. Output final ──────────────────────────────────────────
    result = {
        "summary": {
            "total_opportunities": len(final_opportunities),
            "total_themes": len(themes),
            "insider_triggers_found": len(insider_triggers),
            "scan_status": "ok"
        },
        "opportunities": final_opportunities,
        "themes": themes,
        "daily_report": daily_report
    }

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    log_success(f"[Scan] Done — {len(final_opportunities)} opportunities, {len(insider_triggers)} insider triggers.")
    return result


def determine_signal(score, risk_score, direct_triggers, confirmation_triggers):
    if direct_triggers >= 1 and confirmation_triggers >= 1 and score >= 75 and risk_score < 50:
        return "BUY"
    if direct_triggers >= 1:
        return "WATCH"
    if score >= 60:
        return "WATCH"
    return "PASS"


def build_why_now(signal_origin, ticker, company, theme, has_insider=False):
    if has_insider and signal_origin == "direct":
        return (
            f"Direct insider buying detected for {ticker} / {company}, "
            f"combined with active {theme} theme narrative."
        )
    if signal_origin == "direct":
        return f"Direct company-specific trigger detected for {ticker} / {company}."
    return (
        f"{theme} is active in current news flow, "
        f"and {company} is mapped as a relevant beneficiary."
    )


def build_theme_summary(opportunities):
    theme_map = {}
    for opp in opportunities:
        theme = opp.get("theme", "General")
        if theme not in theme_map:
            theme_map[theme] = {"theme": theme, "strength_sum": 0, "count": 0, "tickers": []}
        theme_map[theme]["strength_sum"] += opp["score"]
        theme_map[theme]["count"] += 1
        theme_map[theme]["tickers"].append(opp["ticker"])

    result = []
    for theme, data in theme_map.items():
        avg = round(data["strength_sum"] / data["count"], 1) if data["count"] else 0
        result.append({
            "theme": theme,
            "strength": avg,
            "tickers": sorted(list(set(data["tickers"])))
        })
    return sorted(result, key=lambda x: x["strength"], reverse=True)


def build_daily_report(opportunities, themes):
    top_ideas = opportunities[:3]
    top_themes = themes[:3]
    return {
        "headline": (
            f"{top_themes[0]['theme']} is currently the strongest active market narrative."
            if top_themes else "No dominant market narrative detected."
        ),
        "top_ideas": [
            {"ticker": x["ticker"], "score": x["score"], "signal": x["signal"], "theme": x["theme"]}
            for x in top_ideas
        ],
        "focus": [
            "Watch for multi-trigger continuation setups",
            "Monitor filings for dilution or financing risk",
            "Track relative volume confirmation and thematic expansion"
        ]
    }
