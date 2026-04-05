# File: app/collectors/rss_collector.py

import feedparser

RSS_FEEDS = [
    # General market
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
    "https://www.marketwatch.com/rss/topstories",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",

    # Stocks & earnings
    "https://www.investing.com/rss/news_25.rss",
    "https://www.investing.com/rss/news_1.rss",

    # Tech / AI
    "https://feeds.feedburner.com/TechCrunch/",
]


def fetch_rss_headlines(limit_per_feed: int = 15) -> list[dict]:
    headlines = []
    seen = set()

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:limit_per_feed]:
                title = getattr(entry, "title", "").strip()

                if not title or title.lower() in seen:
                    continue

                seen.add(title.lower())

                headlines.append({
                    "title": title,
                    "summary": getattr(entry, "summary", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", ""),
                    "source": url
                })

        except Exception:
            continue

    return headlines
