from app.models import Trigger
from app.collectors.rss_collector import fetch_rss_headlines
from app.engines.theme_detector import detect_theme_from_text


def collect_news_triggers() -> list[Trigger]:
    raw_headlines = fetch_rss_headlines()
    triggers = []
    seen_titles = set()

    for item in raw_headlines:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        combined_text = f"{title} {summary}"

        if not title or title.lower() in seen_titles:
            continue

        seen_titles.add(title.lower())

        theme_name, subthemes, confidence = detect_theme_from_text(combined_text)

        if not theme_name:
            continue

        urgency = "high" if confidence >= 7.5 else "medium"

        triggers.append(
            Trigger(
                trigger_type="news",
                headline=title,
                theme_hint=theme_name,
                subthemes=subthemes,
                urgency=urgency,
                freshness="new",
                confidence=confidence
            )
        )

    return triggers
