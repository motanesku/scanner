# File: app/scoring/market_score.py

def calculate_market_score(ticker, market_data):
    """
    Market score:
    - 50 = neutru / fără date
    - >50 = confirmare pozitivă
    - <50 = confirmare slabă
    """

    md = market_data.get(ticker, {})
    if not md:
        return 50

    if md.get("status") != "ok":
        return 50

    score = 50

    price = md.get("price")
    previous_close = md.get("previous_close")
    open_price = md.get("open")
    high_price = md.get("high")
    low_price = md.get("low")
    volume = md.get("volume")
    avg_volume = md.get("avg_volume_5d")

    # dacă prețul există
    if price is not None and previous_close is not None:
        pct_change = 0
        if previous_close not in (0, None):
            pct_change = ((price - previous_close) / previous_close) * 100

        if pct_change > 3:
            score += 12
        elif pct_change > 1:
            score += 8
        elif pct_change > 0:
            score += 4
        elif pct_change < -3:
            score -= 12
        elif pct_change < -1:
            score -= 8
        elif pct_change < 0:
            score -= 4

    # intraday strength
    if price is not None and open_price is not None:
        if price > open_price:
            score += 4
        elif price < open_price:
            score -= 4

    # range position
    if all(v is not None for v in [price, high_price, low_price]) and high_price != low_price:
        range_pos = (price - low_price) / (high_price - low_price)

        if range_pos >= 0.8:
            score += 6
        elif range_pos <= 0.2:
            score -= 6

    # volume confirmation
    if volume is not None and avg_volume is not None and avg_volume > 0:
        rel_vol = volume / avg_volume

        if rel_vol > 1.8:
            score += 12
        elif rel_vol > 1.2:
            score += 8
        elif rel_vol < 0.7:
            score -= 6

    return max(0, min(100, round(score, 1)))
