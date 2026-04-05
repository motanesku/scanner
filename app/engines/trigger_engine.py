from app.models import Trigger


def collect_news_triggers() -> list[Trigger]:
    """
    MVP mock collector.
    Mai târziu îl înlocuim cu surse reale.
    """
    return [
        Trigger(
            trigger_type="news",
            headline="Copper demand expected to surge from AI power infrastructure",
            theme_hint="Copper Demand Expansion",
            subthemes=["AI Infrastructure", "Grid Modernization", "Power Demand"],
            urgency="high",
            freshness="new",
            confidence=8.4
        ),
        Trigger(
            trigger_type="news",
            headline="Cybersecurity spending remains resilient across enterprise budgets",
            theme_hint="Cybersecurity Resilience",
            subthemes=["Enterprise Security", "Cloud Security"],
            urgency="medium",
            freshness="new",
            confidence=7.6
        )
    ]