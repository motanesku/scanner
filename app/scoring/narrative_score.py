# File: app/scoring/narrative_score.py

THEME_STRENGTH = {
    "AI Infrastructure Buildout": 92,
    "Semiconductors Cycle": 82,
    "Energy & Commodities": 76,
    "Cybersecurity": 80,
    "General Market": 55,
    "AI Infrastructure": 90,
    "Semiconductors": 82,
    "Cloud": 78,
    "Energy": 72,
    "Defense": 74,
    "Biotech": 68,
    "Copper": 76,
    "General": 55
}


def calculate_narrative_score(ticker, parsed_news):
    """
    Scor de narativă:
    - cât de puternică e tema în piață
    - cât de consistent apare tickerul în acea temă
    """

    ticker_news = parsed_news.get(ticker, [])
    if not ticker_news:
        return 40

    score = 50
    seen_themes = []

    for item in ticker_news:
        theme = item.get("theme", "General")
        sentiment = item.get("sentiment", "neutral")

        if theme not in seen_themes:
            seen_themes.append(theme)
            score += int(THEME_STRENGTH.get(theme, 55) * 0.2)

        if sentiment == "bullish":
            score += 5
        elif sentiment == "bearish":
            score -= 5

    if len(ticker_news) >= 3:
        score += 8
    elif len(ticker_news) == 2:
        score += 4
    elif len(ticker_news) == 1:
        score += 2

    return max(0, min(100, score))
