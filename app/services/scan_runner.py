# File: app/services/scan_runner.py

# ... (restul rămâne identic până la scoring)

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

# ...

def determine_signal(score, risk_score, direct_triggers):
    if direct_triggers >= 1 and score >= 75 and risk_score < 50:
        return "BUY"

    if score >= 60:
        return "WATCH"

    return "PASS"
