# File: app/scoring/risk_score.py

def calculate_risk_score(ticker, parsed_filings, parsed_news):
    """
    Risk score:
    0 = risc foarte mic
    100 = risc foarte mare
    """

    risk = 20

    # FILINGS
    for filing in parsed_filings:
        risk_flags = filing.get("risk_flags", [])
        filing_type = filing.get("filing_type", "OTHER")

        if "dilution_risk" in risk_flags:
            risk += 25
        if "financial_distress" in risk_flags:
            risk += 35
        if "legal_risk" in risk_flags:
            risk += 15

        if filing_type == "S-3":
            risk += 20
        if filing_type == "424B":
            risk += 15

    # NEWS
    ticker_news = parsed_news.get(ticker, [])
    for item in ticker_news:
        sentiment = item.get("sentiment", "neutral")
        keywords = item.get("keywords", [])

        if sentiment == "bearish":
            risk += 10

        if "offering" in keywords:
            risk += 20
        if "dilution" in keywords:
            risk += 25
        if "lawsuit" in keywords:
            risk += 15
        if "delay" in keywords:
            risk += 10

    return max(0, min(100, risk))
