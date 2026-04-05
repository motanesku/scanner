# File: app/scoring/catalyst_score.py

def calculate_catalyst_score(ticker, parsed_filings, parsed_news, market_data):
    """
    Catalyst score bazat pe:
    - direct triggers (ticker apare în știre)
    - theme triggers (ticker derivat din temă)
    - confirmation (market)
    - risk
    """

    score = 50

    direct_count = 0
    theme_count = 0

    ticker_news = parsed_news.get(ticker, [])

    # 🔴 DIRECT vs THEME
    for item in ticker_news:
        sentiment = item.get("sentiment", "neutral")
        keywords = item.get("keywords", [])
        title = item.get("title", "").upper()

        if ticker in title:
            direct_count += 1
        else:
            theme_count += 1

        if sentiment == "bullish":
            score += 5
        elif sentiment == "bearish":
            score -= 5

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

    # 🔥 DIRECT BOOST (FOARTE IMPORTANT)
    if direct_count >= 1:
        score += 20
    elif theme_count >= 1:
        score += 5

    # 🟢 CONFIRMATION (market)
    md = market_data.get(ticker, {})
    price = md.get("price")
    prev = md.get("previous_close")
    volume = md.get("volume")
    avg_vol = md.get("avg_volume_5d")

    if price and prev:
        if price > prev:
            score += 5
        else:
            score -= 3

    if volume and avg_vol:
        if avg_vol > 0 and volume > avg_vol * 1.5:
            score += 10
        elif avg_vol > 0 and volume < avg_vol * 0.7:
            score -= 5

    return max(0, min(100, score))
