# File: app/scoring/catalyst_score.py

def calculate_catalyst_score(ticker, parsed_filings, parsed_news, market_data):
    """
    Scor bazat pe:
    - știri bullish / bearish
    - filing-uri relevante pentru ticker
    - volum / price action de bază
    """

    score = 50

    # NEWS
    ticker_news = parsed_news.get(ticker, [])
    for item in ticker_news:
        sentiment = item.get("sentiment", "neutral")
        keywords = item.get("keywords", [])

        if sentiment == "bullish":
            score += 8
        elif sentiment == "bearish":
            score -= 8

        if "contract" in keywords:
            score += 6
        if "approval" in keywords:
            score += 8
        if "offering" in keywords:
            score -= 12
        if "dilution" in keywords:
            score -= 15
        if "breakout" in keywords:
            score += 5

    # FILINGS — aplică doar dacă tickerul apare în filing
    ticker_lower = ticker.lower()
    for filing in parsed_filings:
        filing_text = f"{filing.get('title', '')} {filing.get('summary', '')}".lower()

        if ticker_lower not in filing_text:
            continue

        sentiment = filing.get("sentiment", "neutral")
        risk_flags = filing.get("risk_flags", [])
        filing_type = filing.get("filing_type", "OTHER")

        if filing_type == "8-K" and sentiment == "bullish":
            score += 10
        if filing_type == "S-3":
            score -= 18
        if filing_type == "424B":
            score -= 14

        if "dilution_risk" in risk_flags:
            score -= 15
        if "financial_distress" in risk_flags:
            score -= 20

    # MARKET
    md = market_data.get(ticker, {})
    price = md.get("price")
    previous_close = md.get("previous_close")
    volume = md.get("volume")
    avg_volume = md.get("avg_volume_5d")

    if price and previous_close:
        if price > previous_close:
            score += 5
        elif price < previous_close:
            score -= 5

    if volume and avg_volume:
        if avg_volume > 0 and volume > avg_volume * 1.5:
            score += 8
        elif avg_volume > 0 and volume < avg_volume * 0.7:
            score -= 4

    return max(0, min(100, score))
