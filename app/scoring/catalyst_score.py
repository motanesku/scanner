# File: app/scoring/catalyst_score.py
#
# Catalyst score bazat pe:
# - direct triggers (ticker apare explicit în știre/filing)
# - theme triggers (ticker derivat din temă)
# - insider buy (Form 4 real din SEC EDGAR)
# - confirmation (market data)
# - risk (filings bearish)

def calculate_catalyst_score(
    ticker,
    parsed_filings,
    parsed_news,
    market_data,
    insider_triggers: list[dict] | None = None
):
    """
    insider_triggers: lista returnată de collect_insider_triggers()
    Dacă nu e pasată, insider scoring este ignorat (nu crăpăm).
    """

    score = 50

    direct_count = 0
    theme_count = 0

    ticker_news = parsed_news.get(ticker, [])

    # ── News scoring ──────────────────────────────────────────────
    for item in ticker_news:
        sentiment = item.get("sentiment", "neutral")
        keywords = item.get("keywords", [])
        title = item.get("title", "").upper()

        # Direct vs Theme
        if ticker in title:
            direct_count += 1
        else:
            theme_count += 1

        # Sentiment
        if sentiment == "bullish":
            score += 5
        elif sentiment == "bearish":
            score -= 5

        # Keyword boosts
        if "earnings" in keywords:
            score += 10
        if "guidance" in keywords:
            score += 8
        if "contract" in keywords:
            score += 8
        if "approval" in keywords:
            score += 10
        if "offering" in keywords:
            score -= 15
        if "dilution" in keywords:
            score -= 20

    # ── Direct vs Theme boost ─────────────────────────────────────
    if direct_count >= 1:
        score += 20
    elif theme_count >= 1:
        score += 5

    # ── Insider Buy boost (Tier 1 Direct Trigger) ─────────────────
    if insider_triggers:
        ticker_insider = next(
            (t for t in insider_triggers
             if t.get("ticker", "").upper() == ticker.upper()
             and t.get("transaction_type") == "P"),
            None
        )
        if ticker_insider:
            total_value = ticker_insider.get("total_value", 0)
            role = ticker_insider.get("insider_role", "")

            # Boost în funcție de valoarea tranzacției
            if total_value >= 1_000_000:
                score += 25
            elif total_value >= 500_000:
                score += 20
            elif total_value >= 200_000:
                score += 15
            elif total_value >= 100_000:
                score += 12
            elif total_value >= 50_000:
                score += 8

            # Bonus dacă e CEO / President / CFO
            if any(title in role for title in ("CEO", "President", "CFO", "CTO", "COO")):
                score += 5

    # ── Market confirmation ───────────────────────────────────────
    md = market_data.get(ticker, {})
    price = md.get("price")
    prev = md.get("previous_close")
    volume = md.get("volume")
    avg_vol = md.get("avg_volume_5d")

    if price and prev and prev > 0:
        if price > prev:
            score += 5
        else:
            score -= 3

    if volume and avg_vol and avg_vol > 0:
        if volume > avg_vol * 1.5:
            score += 10
        elif volume < avg_vol * 0.7:
            score -= 5

    return max(0, min(100, score))
