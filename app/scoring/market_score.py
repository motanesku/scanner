# File: app/scoring/market_score.py

def calculate_market_score(ticker, market_data):
    """
    Scor simplu de market structure:
    - up/down față de previous close
    - volum relativ
    """

    md = market_data.get(ticker, {})
    if not md:
        return 50

    score = 50

    price = md.get("price")
    previous_close = md.get("previous_close")
    volume = md.get("volume")
    avg_volume = md.get("avg_volume_5d")

    if price and previous_close:
        pct_change = ((price - previous_close) / previous_close) * 100

        if pct_change > 5:
            score += 20
        elif pct_change > 2:
            score += 12
        elif pct_change > 0:
            score += 6
        elif pct_change < -5:
            score -= 20
        elif pct_change < -2:
            score -= 12
        elif pct_change < 0:
            score -= 6

    if volume and avg_volume and avg_volume > 0:
        rel_vol = volume / avg_volume

        if rel_vol > 2:
            score += 18
        elif rel_vol > 1.5:
            score += 10
        elif rel_vol < 0.7:
            score -= 6

    return max(0, min(100, score))
